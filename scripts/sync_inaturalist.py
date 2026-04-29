"""
Sincroniza observações do iNaturalist para espécies com inaturalist_taxon_id cadastrado.
Estratégia replace: apaga todas as obs da espécie+source e re-insere tudo.
Garante que mudanças de taxon_id ou remoções no iNat sejam refletidas corretamente.
Paginação via id_above para superar o limite de 10k resultados da API.
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

INAT_API_URL = os.getenv("INATURALIST_API_URL", "https://api.inaturalist.org/v1")
INAT_API_KEY = os.getenv("INATURALIST_API_KEY")
PER_PAGE = 200
SLEEP_BETWEEN_SPECIES = float(os.getenv("INATURALIST_SLEEP_BETWEEN_SPECIES", "1"))
SLEEP_BETWEEN_PAGES = float(os.getenv("INATURALIST_SLEEP_BETWEEN_PAGES", "0.5"))
REQUEST_TIMEOUT = int(os.getenv("INATURALIST_REQUEST_TIMEOUT_SECONDS", "30"))

app = create_app()


def _log(message: str, level: str = "INFO") -> None:
    print(f"[{level}] {message}")


def _int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _build_headers() -> dict:
    headers = {"Accept": "application/json"}
    if INAT_API_KEY:
        headers["Authorization"] = f"Bearer {INAT_API_KEY}"
    return headers


def _parse_location(location: str | None) -> tuple[float | None, float | None]:
    if not location:
        return None, None
    try:
        lat_str, lng_str = location.split(",", 1)
        return float(lat_str.strip()), float(lng_str.strip())
    except (ValueError, AttributeError):
        return None, None


def _fetch_page(taxon_id: int, id_above: int | None) -> dict:
    params = {
        "taxon_id": taxon_id,
        "has[]": "geo",
        "per_page": PER_PAGE,
        "order": "asc",
        "order_by": "id",
    }
    if id_above is not None:
        params["id_above"] = id_above

    response = requests.get(
        f"{INAT_API_URL}/observations",
        headers=_build_headers(),
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def _collect_species(taxon_id: int) -> list[dict]:
    """Coleta todas as observações do iNat para o taxon. Levanta exceção se falhar."""
    collected = []
    id_above = None
    page_num = 0

    while True:
        page_num += 1
        data = _fetch_page(taxon_id, id_above)
        results = data.get("results", [])
        if not results:
            break

        for obs in results:
            obs_id = str(obs.get("id"))
            lat, lng = _parse_location(obs.get("location"))
            if lat is None or lng is None:
                continue

            photos = obs.get("photos") or []
            raw_photo_url = photos[0].get("url") if photos else None
            photo_url = raw_photo_url.replace("/square.", "/medium.") if raw_photo_url else None

            collected.append({
                "source": "inaturalist",
                "external_id": obs_id,
                "latitude": lat,
                "longitude": lng,
                "location_obscured": bool(obs.get("obscured", False)),
                "observed_on": obs.get("observed_on") or None,
                "quality_grade": obs.get("quality_grade") or None,
                "photo_url": photo_url,
                "url": obs.get("uri") or None,
            })

        _log(f"  página {page_num}: {len(results)} obs coletadas (total={len(collected)})")

        if len(results) < PER_PAGE:
            break

        id_above = results[-1].get("id")
        time.sleep(SLEEP_BETWEEN_PAGES)

    return collected


def _sync_species(species: Species) -> tuple[int, int]:
    """Retorna (apagadas, inseridas) para a espécie."""
    taxon_id = species.inaturalist_taxon_id

    collected = _collect_species(taxon_id)

    deleted = Observation.query.filter_by(
        species_id=species.id, source="inaturalist"
    ).delete()

    for row in collected:
        db.session.add(Observation(species_id=species.id, **row))

    db.session.commit()
    return deleted, len(collected)


def main():
    raw_lumm_ids = os.environ.get("LUMM_ID", "")
    lumm_ids = [v for raw in raw_lumm_ids.split(",") if (v := _int(raw.strip()))]

    _log("=== Sync iNaturalist: inicio ===")
    if INAT_API_KEY:
        _log("Usando API key", "OK")
    else:
        _log("Sem API key — rate limit reduzido", "AVISO")

    with app.app_context():
        query = db.session.query(Species).filter(
            Species.inaturalist_taxon_id.isnot(None)
        )
        if lumm_ids:
            _log(f"Modo individual: LUMM_IDs={lumm_ids}")
            query = query.filter(Species.id.in_(lumm_ids))

        species_list = query.all()
        total_species = len(species_list)
        _log(f"Espécies com inaturalist_taxon_id: {total_species}", "OK")

        total_deleted = 0
        total_inserted = 0
        errors = 0

        for idx, species in enumerate(species_list, start=1):
            _log(
                f"[{idx}/{total_species}] {species.scientific_name} "
                f"(taxon_id={species.inaturalist_taxon_id})"
            )
            try:
                deleted, inserted = _sync_species(species)
                total_deleted += deleted
                total_inserted += inserted
                _log(f"  apagadas={deleted} inseridas={inserted}", "OK")
            except Exception as e:
                errors += 1
                _log(f"  Erro inesperado: {e}", "ERRO")
                db.session.rollback()

            time.sleep(SLEEP_BETWEEN_SPECIES)

    _log(
        f"Apagadas: {total_deleted} | Inseridas: {total_inserted} | Erros: {errors}",
        "RESUMO",
    )
    _log("Sincronização finalizada", "OK")


if __name__ == "__main__":
    main()
