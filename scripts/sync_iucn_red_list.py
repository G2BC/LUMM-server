"""
Popula a coluna conservation_status da species_characteristics com os dados da API IUCN.

- Lock Redis + checkpoint por espécie (via SyncRunner)
- Agrupamento por group_name com pausa configurável entre grupos
"""

import os
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models.species import Species  # noqa: E402
from app.models.species_characteristics import SpeciesCharacteristics  # noqa: E402
from scripts.sync_base import SyncRunner  # noqa: E402

IUCN_REQUEST_TIMEOUT = 30


def _i(value):
    if value in (None, ""):
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


class IucnSync(SyncRunner):
    source_name = "iucn_red_list"
    env_prefix = "IUCN"

    def get_species_rows(self, session, lumm_ids):
        query = session.query(Species.id, Species.scientific_name, Species.group_name)
        if lumm_ids:
            query = query.filter(Species.id.in_(lumm_ids))
        return query.all()

    def sync_species(self, row, start_time):
        name_parts = (row.scientific_name or "").split()
        if len(name_parts) < 2:
            self._log(f"  [{row.id}] nome científico inválido: {row.scientific_name!r}")
            return 0, 0, True

        genus_name = name_parts[0]
        species_name = " ".join(name_parts[1:])

        response = requests.get(
            "https://api.iucnredlist.org/api/v4/taxa/scientific_name",
            headers={
                "authorization": os.getenv("IUCN_API_KEY"),
                "accept": "application/json",
            },
            params={"genus_name": genus_name, "species_name": species_name},
            timeout=IUCN_REQUEST_TIMEOUT,
        )

        if response.status_code != 200:
            time.sleep(1)
            raise RuntimeError(
                f"IUCN API HTTP {response.status_code} para {row.scientific_name!r}"
            )

        data = response.json()

        if not isinstance(data, dict):
            time.sleep(1)
            self._log(f"  [{row.id}] resposta inválida da API IUCN")
            return 0, 0, True

        assessments = data.get("assessments")
        if not isinstance(assessments, list):
            time.sleep(1)
            self._log(f"  [{row.id}] campo assessments inválido")
            return 0, 0, True

        latest_assessment = next(
            (a for a in assessments if a.get("latest", False)),
            None,
        )

        if not latest_assessment:
            time.sleep(1)
            self._log(f"  [{row.id}] sem assessment latest")
            return 0, 0, True

        conservation_status = latest_assessment.get("red_list_category_code")
        assessment_id = latest_assessment.get("assessment_id")
        iucn_assessment_year = latest_assessment.get("year_published")
        url = latest_assessment.get("url")

        db.session.query(Species).filter_by(id=row.id).update(
            {"iucn_redlist": assessment_id},
            synchronize_session=False,
        )
        db.session.query(SpeciesCharacteristics).filter_by(species_id=row.id).update(
            {
                "conservation_status": conservation_status,
                "iucn_assessment_year": iucn_assessment_year,
                "iucn_assessment_url": url,
            },
            synchronize_session=False,
        )
        db.session.commit()

        self._log(
            f"  [{row.id}] {row.scientific_name} → {conservation_status}"
        )

        time.sleep(1)
        return 1, 0, True


if __name__ == "__main__":
    IucnSync(create_app()).run()
