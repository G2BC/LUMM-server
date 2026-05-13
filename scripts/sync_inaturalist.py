"""
Sincroniza observações do iNaturalist para espécies com inaturalist_taxon_id cadastrado.

- Full sync por padrão
- UPSERT via INSERT ... ON CONFLICT DO UPDATE
- Reconcilia observações removendo, no final, o que não veio mais da API
- Lock Redis + checkpoint por espécie (via SyncRunner)
- Agrupamento por group_name com pausa configurável entre grupos
"""

import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import requests
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import func

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models.observation import Observation  # noqa: E402
from app.models.species import Species  # noqa: E402
from app.services.cache_service import CacheService  # noqa: E402
from scripts.sync_base import SyncRunner  # noqa: E402

INAT_API_URL = os.getenv("INATURALIST_API_URL", "https://api.inaturalist.org/v1")
INAT_API_KEY = os.getenv("INATURALIST_API_KEY")
PER_PAGE = 200
REQUEST_TIMEOUT = 30


def _parse_location(location):
    if not location:
        return None, None
    try:
        lat, lng = location.split(",", 1)
        return float(lat), float(lng)
    except Exception:
        return None, None


def _fetch_page(taxon_id, id_above):
    params = {
        "taxon_id": taxon_id,
        "has[]": "geo",
        "per_page": PER_PAGE,
        "order": "asc",
        "order_by": "id",
    }
    if id_above:
        params["id_above"] = id_above
    headers = {"Authorization": f"Bearer {INAT_API_KEY}"} if INAT_API_KEY else {}

    for attempt in range(3):
        r = requests.get(
            f"{INAT_API_URL}/observations",
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        if r.status_code == 429:
            time.sleep(2**attempt * 5)
            continue
        r.raise_for_status()
        return r.json()

    raise RuntimeError("Máximo de tentativas atingido (429)")


def _upsert(rows):
    if not rows:
        return 0
    stmt = pg_insert(Observation).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_observation_source_external_id",
        set_={
            "species_id": stmt.excluded.species_id,
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


def _delete_stale_observations(species_id, seen_external_ids):
    current_ids = {
        external_id
        for (external_id,) in db.session.query(Observation.external_id).filter_by(
            species_id=species_id,
            source="inaturalist",
        )
    }
    stale_ids = current_ids - seen_external_ids
    if not stale_ids:
        return 0

    deleted = 0
    stale_ids = list(stale_ids)
    for i in range(0, len(stale_ids), 1000):
        chunk = stale_ids[i : i + 1000]
        deleted += (
            db.session.query(Observation)
            .filter(
                Observation.species_id == species_id,
                Observation.source == "inaturalist",
                Observation.external_id.in_(chunk),
            )
            .delete(synchronize_session=False)
        )
    db.session.commit()
    return deleted


class InatSync(SyncRunner):
    source_name = "inaturalist"
    env_prefix = "INAT"

    def get_species_rows(self, session, lumm_ids):
        query = session.query(
            Species.id, Species.inaturalist_taxon_id, Species.group_name
        ).filter(Species.inaturalist_taxon_id.isnot(None))
        if lumm_ids:
            query = query.filter(Species.id.in_(lumm_ids))
        return query.all()

    def sync_species(self, row, start_time):
        self._log(f"  [{row.id}] modo=full taxon={row.inaturalist_taxon_id}")

        seen_external_ids = set()
        id_above = None
        total = 0
        page = 0

        while True:
            if time.time() - start_time > self.max_runtime:
                self._log("  Kill switch atingido — abortando espécie")
                return total, 0, False

            page += 1
            data = _fetch_page(row.inaturalist_taxon_id, id_above)
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
                rows.append(
                    {
                        "species_id": row.id,
                        "source": "inaturalist",
                        "external_id": str(obs["id"]),
                        "latitude": lat,
                        "longitude": lng,
                        "location_obscured": bool(obs.get("obscured", False)),
                        "observed_on": obs.get("observed_on"),
                        "quality_grade": obs.get("quality_grade"),
                        "photo_url": raw_url.replace("/square.", "/medium.") if raw_url else None,
                        "url": obs.get("uri"),
                    }
                )
                seen_external_ids.add(str(obs["id"]))

            total += _upsert(rows)
            self._log(f"  [{row.id}] página {page}: +{len(rows)}")

            if len(results) < PER_PAGE:
                break
            id_above = results[-1]["id"]

        deleted = _delete_stale_observations(row.id, seen_external_ids)

        species = db.session.get(Species, row.id)
        if species:
            species.last_inaturalist_sync_at = datetime.now(UTC)
            db.session.commit()

        prefix = self.app.config.get("OBSERVATIONS_CACHE_PREFIX", "observations")
        CacheService.delete(f"{prefix}:{row.id}:all")
        CacheService.delete(f"{prefix}:{row.id}:inaturalist")

        return total, deleted, True


if __name__ == "__main__":
    InatSync(create_app()).run()
