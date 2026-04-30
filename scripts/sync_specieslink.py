"""
Sincroniza ocorrências do speciesLink para espécies com scientific_name cadastrado.

- Estratégia replace: apaga todas as obs da espécie+source e re-insere tudo
- Paginação via offset/limit
- ThreadPoolExecutor com MAX_WORKERS threads
- Kill switch por MAX_RUNTIME_SECONDS
"""

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.extensions import db
from app.models.observation import Observation
from app.models.species import Species
from app.services.cache_service import CacheService

SPECIESLINK_API_URL = os.getenv("SPECIESLINK_API_URL", "https://specieslink.net/ws/1.0/search")
SPECIESLINK_API_KEY = os.getenv("SPECIESLINK_API_KEY", "")
PAGE_SIZE = 500
REQUEST_TIMEOUT = 30
SLEEP_BETWEEN_PAGES = float("3")
MAX_WORKERS = 2
MAX_RUNTIME_SECONDS = int("3540")
MAX_RETRIES = 3
HEADERS = {"User-Agent": "LUMM-server/1.0 (lumm.uneb.br; contact: lumm.g2bc@gmail.com)"}

app = create_app()


def _log(msg):
    print(msg, flush=True)


def _build_date(props):
    year = props.get("yearcollected")
    month = props.get("monthcollected")
    day = props.get("daycollected")
    if not year:
        return None
    parts = [year.zfill(4)]
    if month:
        parts.append(month.zfill(2))
        if day:
            parts.append(day.zfill(2))
    return "-".join(parts) if len(parts) == 3 else None


def _fetch_page(scientific_name, offset):
    params = {
        "apikey": SPECIESLINK_API_KEY,
        "scientificName": scientific_name,
        "offset": offset,
        "limit": PAGE_SIZE,
    }
    for attempt in range(MAX_RETRIES):
        r = requests.get(SPECIESLINK_API_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if r.status_code == 429:
            wait = 2 ** attempt * 10
            _log(f"  429 recebido — aguardando {wait}s (tentativa {attempt + 1}/{MAX_RETRIES})")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()

    raise RuntimeError("Máximo de tentativas atingido (429)")


def _sync_species(species_id, scientific_name, start_time):
    with app.app_context():
        collected = []
        offset = 0
        page = 0

        while True:
            if time.time() - start_time > MAX_RUNTIME_SECONDS:
                _log(f"  [{species_id}] Kill switch — abortando")
                return 0, False

            data = _fetch_page(scientific_name, offset)
            features = data.get("features") or []
            number_matched = data.get("numberMatched", 0)

            for feature in features:
                geom = feature.get("geometry") or {}
                coords = geom.get("coordinates")
                if not coords or len(coords) < 2:
                    continue

                lng, lat = coords[0], coords[1]
                props = feature.get("properties") or {}
                barcode = props.get("barcode") or props.get("catalognumber")
                if not barcode:
                    continue

                collection_id = props.get("collectionid")
                catalog_number = props.get("catalognumber")
                if collection_id and catalog_number:
                    url = f"https://specieslink.net/search/records/collectioncode/{collection_id}/catalognumber/{catalog_number}"
                else:
                    url = None

                collected.append({
                    "species_id": species_id,
                    "source": "specieslink",
                    "external_id": barcode,
                    "latitude": float(lat),
                    "longitude": float(lng),
                    "location_obscured": False,
                    "observed_on": _build_date(props),
                    "quality_grade": props.get("basisofrecord"),
                    "photo_url": None,
                    "url": url,
                })

            page += 1
            _log(f"  [{species_id}] página {page}: {len(features)} features (total matched: {number_matched})")

            offset += PAGE_SIZE
            if offset >= number_matched or not features:
                break

            time.sleep(SLEEP_BETWEEN_PAGES)

        db.session.query(Observation).filter_by(species_id=species_id, source="specieslink").delete()
        for row in collected:
            db.session.add(Observation(**row))
        db.session.commit()

        prefix = app.config.get("OBSERVATIONS_CACHE_PREFIX", "observations")
        CacheService.delete(f"{prefix}:{species_id}:all")
        CacheService.delete(f"{prefix}:{species_id}:specieslink")

        db.session.remove()
        return len(collected), True


def main():
    start_time = time.time()

    raw_lumm_ids = os.getenv("LUMM_ID", "")
    lumm_ids = [int(v) for raw in raw_lumm_ids.split(",") if (v := raw.strip()).isdigit()]

    _log("=== Sync speciesLink ===")
    _log(f"workers={MAX_WORKERS} | limite={MAX_RUNTIME_SECONDS}s")

    with app.app_context():
        query = db.session.query(Species.id, Species.scientific_name).filter(
            Species.scientific_name.isnot(None)
        )
        if lumm_ids:
            query = query.filter(Species.id.in_(lumm_ids))
        species_rows = query.all()

    _log(f"Espécies: {len(species_rows)}")

    total = 0
    errors = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(_sync_species, row.id, row.scientific_name, start_time): row.id
            for row in species_rows
        }
        for future in as_completed(futures):
            species_id = futures[future]
            try:
                inserted, completed = future.result()
                total += inserted
                _log(f"[OK] species={species_id} +{inserted}")
                if not completed:
                    pool.shutdown(wait=False, cancel_futures=True)
                    break
            except Exception as e:
                errors += 1
                _log(f"[ERRO] species={species_id}: {e}")

    _log(f"Total: {total} | Erros: {errors} | Tempo: {int(time.time() - start_time)}s")


if __name__ == "__main__":
    main()
