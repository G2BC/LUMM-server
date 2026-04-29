"""
Sincroniza observações do Mushroom Observer para espécies com scientific_name cadastrado.

- Estratégia replace: apaga todas as obs da espécie+source e re-insere tudo
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

MO_API_URL = os.getenv("MUSHROOM_OBSERVER_API_URL", "https://mushroomobserver.org/api2")
REQUEST_TIMEOUT = 30
SLEEP_BETWEEN_PAGES = float("1")
MAX_WORKERS = 4
MAX_RUNTIME_SECONDS = int("3540")

app = create_app()


def _log(msg):
    print(msg, flush=True)


def _center_of_bbox(loc):
    try:
        lat = (float(loc["latitude_north"]) + float(loc["latitude_south"])) / 2
        lng = (float(loc["longitude_east"]) + float(loc["longitude_west"])) / 2
        return round(lat, 6), round(lng, 6)
    except (KeyError, TypeError, ValueError):
        return None, None


def _parse_coords(obs):
    lat, lng = obs.get("latitude"), obs.get("longitude")
    if lat is not None and lng is not None:
        try:
            return float(lat), float(lng)
        except (TypeError, ValueError):
            pass
    loc = obs.get("location")
    if isinstance(loc, dict):
        return _center_of_bbox(loc)
    return None, None


def _photo_url(obs):
    primary = obs.get("primary_image")
    if not primary:
        return None
    url = primary.get("original_url", "")
    return url.replace("/orig/", "/640/") if url else None


def _fetch_page(name_id, scientific_name, page):
    if name_id:
        params = {"format": "json", "detail": "high", "name_id": name_id, "page": page}
    else:
        params = {"format": "json", "detail": "high", "name": scientific_name, "page": page}
    r = requests.get(f"{MO_API_URL}/observations", params=params, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _sync_species(species_id, scientific_name, mo_name_id, start_time):
    with app.app_context():
        collected = []
        discovered_name_id = None
        page = 1

        while True:
            if time.time() - start_time > MAX_RUNTIME_SECONDS:
                _log(f"  [{species_id}] Kill switch — abortando")
                return 0, False

            data = _fetch_page(mo_name_id, scientific_name, page)
            if data.get("errors"):
                raise RuntimeError(f"Erro da API MO: {data['errors']}")

            results = data.get("results") or []
            if not results:
                break

            for obs in results:
                # salva o name_id do primeiro resultado se ainda não temos
                if discovered_name_id is None and not mo_name_id:
                    discovered_name_id = (obs.get("consensus") or {}).get("id")

                lat, lng = _parse_coords(obs)
                if lat is None:
                    continue
                has_precise = obs.get("latitude") is not None
                obs_id = str(obs["id"])
                collected.append({
                    "species_id": species_id,
                    "source": "mushroom_observer",
                    "external_id": obs_id,
                    "latitude": lat,
                    "longitude": lng,
                    "location_obscured": bool(obs.get("gps_hidden", False)) or not has_precise,
                    "observed_on": obs.get("date") or None,
                    "quality_grade": None,
                    "photo_url": _photo_url(obs),
                    "url": f"https://mushroomobserver.org/observations/{obs_id}",
                })

            total_pages = data.get("number_of_pages", 1)
            _log(f"  [{species_id}] página {page}/{total_pages}: {len(results)} obs (via {'id' if mo_name_id else 'name'})")

            if page >= total_pages:
                break
            page += 1
            time.sleep(SLEEP_BETWEEN_PAGES)

        db.session.query(Observation).filter_by(species_id=species_id, source="mushroom_observer").delete()
        for row in collected:
            db.session.add(Observation(**row))

        # persiste o name_id descoberto para os próximos syncs
        if discovered_name_id:
            species = db.session.get(Species, species_id)
            if species and not species.mushroom_observer_name_id:
                species.mushroom_observer_name_id = discovered_name_id

        db.session.commit()

        prefix = app.config.get("OBSERVATIONS_CACHE_PREFIX", "observations")
        CacheService.delete(f"{prefix}:{species_id}:all")
        CacheService.delete(f"{prefix}:{species_id}:mushroom_observer")

        db.session.remove()

        return len(collected), True


def main():
    start_time = time.time()

    raw_lumm_ids = os.getenv("LUMM_ID", "")
    lumm_ids = [int(v) for raw in raw_lumm_ids.split(",") if (v := raw.strip()).isdigit()]

    _log("=== Sync Mushroom Observer ===")
    _log(f"workers={MAX_WORKERS} | limite={MAX_RUNTIME_SECONDS}s")

    with app.app_context():
        query = db.session.query(
            Species.id, Species.scientific_name, Species.mushroom_observer_name_id
        ).filter(Species.scientific_name.isnot(None))
        if lumm_ids:
            query = query.filter(Species.id.in_(lumm_ids))
        species_rows = query.all()

    _log(f"Espécies: {len(species_rows)}")

    total = 0
    errors = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(_sync_species, row.id, row.scientific_name, row.mushroom_observer_name_id, start_time): row.id
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
