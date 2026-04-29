"""
Sincroniza observações do Mushroom Observer para espécies com scientific_name cadastrado.
Usa upsert por (source, external_id). Coordenadas precisas quando disponíveis,
caso contrário calcula o centro do bounding box da localidade.
"""

import os
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.extensions import db
from app.models.observation import Observation
from app.models.species import Species

MO_API_URL = os.getenv("MUSHROOM_OBSERVER_API_URL", "https://mushroomobserver.org/api2")
SLEEP_BETWEEN_SPECIES = float(os.getenv("MUSHROOM_OBSERVER_SLEEP_BETWEEN_SPECIES", "2"))
SLEEP_BETWEEN_PAGES = float(os.getenv("MUSHROOM_OBSERVER_SLEEP_BETWEEN_PAGES", "1"))
REQUEST_TIMEOUT = int(os.getenv("MUSHROOM_OBSERVER_REQUEST_TIMEOUT_SECONDS", "30"))

app = create_app()


def _log(message: str, level: str = "INFO") -> None:
    print(f"[{level}] {message}")


def _int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _center_of_bbox(loc: dict) -> tuple[float | None, float | None]:
    try:
        lat = (float(loc["latitude_north"]) + float(loc["latitude_south"])) / 2
        lng = (float(loc["longitude_east"]) + float(loc["longitude_west"])) / 2
        return round(lat, 6), round(lng, 6)
    except (KeyError, TypeError, ValueError):
        return None, None


def _parse_coords(obs: dict) -> tuple[float | None, float | None]:
    """Coordenada precisa quando disponível, senão centro do bbox da localidade."""
    lat = obs.get("latitude")
    lng = obs.get("longitude")
    if lat is not None and lng is not None:
        try:
            return float(lat), float(lng)
        except (TypeError, ValueError):
            pass

    loc = obs.get("location")
    if isinstance(loc, dict):
        return _center_of_bbox(loc)

    return None, None


def _photo_url(obs: dict) -> str | None:
    primary = obs.get("primary_image")
    if not primary:
        return None
    url = primary.get("original_url", "")
    # troca /orig/ por /640/ — menor e suficiente para marcadores de mapa
    return url.replace("/orig/", "/640/") if url else None


def _obs_url(obs_id: int | str) -> str:
    return f"https://mushroomobserver.org/observations/{obs_id}"


def _fetch_page(scientific_name: str, page: int) -> dict:
    response = requests.get(
        f"{MO_API_URL}/observations",
        params={
            "format": "json",
            "detail": "high",
            "name": scientific_name,
            "page": page,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def _sync_species(species: Species) -> tuple[int, int]:
    """Retorna (inseridas, atualizadas) para a espécie."""
    name = species.scientific_name
    inserted = 0
    updated = 0
    page = 1

    while True:
        try:
            data = _fetch_page(name, page)
        except requests.HTTPError as e:
            _log(f"  HTTP {e.response.status_code} na página {page}: {e}", "ERRO")
            break
        except requests.RequestException as e:
            _log(f"  Erro de rede na página {page}: {e}", "ERRO")
            break

        errors = data.get("errors")
        if errors:
            _log(f"  Erro da API MO: {errors}", "ERRO")
            break

        results = data.get("results") or []
        if not results:
            break

        for obs in results:
            obs_id = str(obs.get("id"))
            lat, lng = _parse_coords(obs)

            if lat is None or lng is None:
                continue

            location_obscured = bool(obs.get("gps_hidden", False))
            has_precise_coords = obs.get("latitude") is not None

            values = {
                "species_id": species.id,
                "source": "mushroom_observer",
                "external_id": obs_id,
                "latitude": lat,
                "longitude": lng,
                "location_obscured": location_obscured or not has_precise_coords,
                "observed_on": obs.get("date") or None,
                "quality_grade": None,  # MO usa confidence (float), sem equivalente direto
                "photo_url": _photo_url(obs),
                "url": _obs_url(obs_id),
            }

            existing = Observation.query.filter_by(
                source="mushroom_observer", external_id=obs_id
            ).one_or_none()

            if existing:
                for k, v in values.items():
                    setattr(existing, k, v)
                updated += 1
            else:
                db.session.add(Observation(**values))
                inserted += 1

        db.session.commit()

        total_pages = data.get("number_of_pages", 1)
        _log(
            f"  página {page}/{total_pages}: {len(results)} obs | "
            f"inseridas={inserted} atualizadas={updated}"
        )

        if page >= total_pages:
            break

        page += 1
        time.sleep(SLEEP_BETWEEN_PAGES)

    return inserted, updated


def main():
    raw_lumm_ids = os.environ.get("LUMM_ID", "")
    lumm_ids = [v for raw in raw_lumm_ids.split(",") if (v := _int(raw.strip()))]

    _log("=== Sync Mushroom Observer: inicio ===")

    with app.app_context():
        query = db.session.query(Species).filter(Species.scientific_name.isnot(None))
        if lumm_ids:
            _log(f"Modo individual: LUMM_IDs={lumm_ids}")
            query = query.filter(Species.id.in_(lumm_ids))

        species_list = query.all()
        total_species = len(species_list)
        _log(f"Espécies para sincronizar: {total_species}", "OK")

        total_inserted = 0
        total_updated = 0
        errors = 0

        for idx, species in enumerate(species_list, start=1):
            _log(f"[{idx}/{total_species}] {species.scientific_name}")
            try:
                ins, upd = _sync_species(species)
                total_inserted += ins
                total_updated += upd
            except Exception as e:
                errors += 1
                _log(f"  Erro inesperado: {e}", "ERRO")
                db.session.rollback()

            time.sleep(SLEEP_BETWEEN_SPECIES)

    _log(
        f"Inseridas: {total_inserted} | Atualizadas: {total_updated} | Erros: {errors}",
        "RESUMO",
    )
    _log("Sincronização finalizada", "OK")


if __name__ == "__main__":
    main()
