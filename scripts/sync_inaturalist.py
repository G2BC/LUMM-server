"""
Sincroniza observações do iNaturalist para espécies com inaturalist_taxon_id cadastrado.

- Incremental por padrão (updated_since = last_inaturalist_sync_at)
- Full sync quando: primeiro sync, FORCE_FULL_SYNC=true ou LUMM_ID especificado
- UPSERT via INSERT ... ON CONFLICT DO UPDATE
- ThreadPoolExecutor com MAX_WORKERS threads
- Kill switch por MAX_RUNTIME_SECONDS
"""

import os
import sys
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import func

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.extensions import db
from app.models.observation import Observation
from app.models.species import Species
from app.services.cache_service import CacheService

INAT_API_URL = os.getenv("INATURALIST_API_URL", "https://api.inaturalist.org/v1")
INAT_API_KEY = os.getenv("INATURALIST_API_KEY")
PER_PAGE = 200
REQUEST_TIMEOUT = 30
MAX_WORKERS = int(4)
MAX_RUNTIME_SECONDS = int("3540")
FORCE_FULL_SYNC = os.getenv("FORCE_FULL_SYNC", "").lower() in ("1", "true", "yes")

app = create_app()


def _log(msg):
    print(msg, flush=True)


def _parse_location(location):
    if not location:
        return None, None
    try:
        lat, lng = location.split(",", 1)
        return float(lat), float(lng)
    except Exception:
        return None, None


def _fetch_page(taxon_id, updated_since, id_above):
    params = {
        "taxon_id": taxon_id,
        "has[]": "geo",
        "per_page": PER_PAGE,
        "order": "asc",
        "order_by": "id",
    }
    if updated_since:
        params["updated_since"] = updated_since.isoformat()
    if id_above:
        params["id_above"] = id_above
    if INAT_API_KEY:
        headers = {"Authorization": f"Bearer {INAT_API_KEY}"}
    else:
        headers = {}

    for attempt in range(3):
        r = requests.get(f"{INAT_API_URL}/observations", params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if r.status_code == 429:
            time.sleep(2 ** attempt * 5)
            continue
        r.raise_for_status()
        return r.json()

    raise RuntimeError("Máximo de tentativas atingido (429)")


def _upsert(species_id, rows):
    if not rows:
        return 0
    stmt = pg_insert(Observation).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_observation_source_external_id",
        set_={
            "latitude": stmt.excluded.latitude,
            "longitude": stmt.excluded.longitude,
            "location_obscured": stmt.excluded.location_obscured,
            "observed_on": stmt.excluded.observed_on,
            "quality_grade": stmt.excluded.quality_grade,
            "photo_url": stmt.excluded.photo_url,
            "url": stmt.excluded.url,
            "updated_at": func.now(),
        },
    )
    db.session.execute(stmt)
    db.session.commit()
    return len(rows)


def _sync_species(species_id, taxon_id, last_sync_at, force_full, start_time):
    with app.app_context():
        is_full = force_full or last_sync_at is None
        updated_since = None if is_full else last_sync_at

        _log(f"  [{species_id}] modo={'full' if is_full else 'incremental'} taxon={taxon_id}")

        if is_full:
            db.session.query(Observation).filter_by(species_id=species_id, source="inaturalist").delete()
            db.session.commit()

        id_above = None
        total = 0
        page = 0

        while True:
            if time.time() - start_time > MAX_RUNTIME_SECONDS:
                _log("  Kill switch atingido — abortando espécie")
                return total, False

            page += 1
            data = _fetch_page(taxon_id, updated_since, id_above)
            results = data.get("results", [])
            if not results:
                break

            rows = []
            for obs in results:
                lat, lng = _parse_location(obs.get("location"))
                if lat is None:
                    continue
                photos = obs.get("photos") or []
                raw_url = photos[0].get("url") if photos else None
                rows.append({
                    "species_id": species_id,
                    "source": "inaturalist",
                    "external_id": str(obs["id"]),
                    "latitude": lat,
                    "longitude": lng,
                    "location_obscured": bool(obs.get("obscured", False)),
                    "observed_on": obs.get("observed_on"),
                    "quality_grade": obs.get("quality_grade"),
                    "photo_url": raw_url.replace("/square.", "/medium.") if raw_url else None,
                    "url": obs.get("uri"),
                })

            total += _upsert(species_id, rows)
            _log(f"  [{species_id}] página {page}: +{len(rows)}")

            if len(results) < PER_PAGE:
                break
            id_above = results[-1]["id"]

        species = db.session.get(Species, species_id)
        if species:
            species.last_inaturalist_sync_at = datetime.now(timezone.utc)
            db.session.commit()

        prefix = app.config.get("OBSERVATIONS_CACHE_PREFIX", "observations")
        CacheService.delete(f"{prefix}:{species_id}:all")
        CacheService.delete(f"{prefix}:{species_id}:inaturalist")

        db.session.remove()
        return total, True


def main():
    start_time = time.time()

    raw_lumm_ids = os.getenv("LUMM_ID", "")
    lumm_ids = [int(v) for raw in raw_lumm_ids.split(",") if (v := raw.strip()).isdigit()]
    force_full = FORCE_FULL_SYNC or bool(lumm_ids)

    _log("=== Sync iNaturalist ===")
    _log(f"modo={'FULL' if force_full else 'incremental'} | workers={MAX_WORKERS} | limite={MAX_RUNTIME_SECONDS}s")

    with app.app_context():
        query = db.session.query(
            Species.id, Species.inaturalist_taxon_id, Species.last_inaturalist_sync_at
        ).filter(Species.inaturalist_taxon_id.isnot(None))
        if lumm_ids:
            query = query.filter(Species.id.in_(lumm_ids))
        species_rows = query.all()

    _log(f"Espécies: {len(species_rows)}")

    total = 0
    errors = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(_sync_species, row.id, row.inaturalist_taxon_id, row.last_inaturalist_sync_at, force_full, start_time): row.id
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
