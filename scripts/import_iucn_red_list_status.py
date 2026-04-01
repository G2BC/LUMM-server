"""
Popula a coluna conservation_status da species_characteristics com os dados da API IUCN
"""

from pathlib import Path
import sys
import requests
import time
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.extensions import db
from app.models.species import Species
from app.models.species_characteristics import SpeciesCharacteristics


app = create_app()


def _log(message: str, level: str = "INFO") -> None:
    print(f"[{level}] {message}")


def main():
    _log("=== Import IUCN Red List: inicio ===")

    with app.app_context():
        species_list = Species.query.all()
        total = len(species_list)

        updated = 0
        invalid_name = 0
        api_errors = 0
        invalid_response = 0
        no_latest_assessment = 0

        _log(f"Especies carregadas: {total}", "OK")

        for idx, species in enumerate(species_list, start=1):
            _log(f"[{idx}/{total}] Buscando: {species.scientific_name}")

            name_parts = (species.scientific_name or "").split()
            if len(name_parts) < 2:
                invalid_name += 1
                _log(
                    f"[{idx}/{total}] {species.scientific_name} - nome cientifico invalido",
                    "ERRO",
                )
                continue

            genus_name = name_parts[0]
            species_name = " ".join(name_parts[1:])

            response = requests.get(
                f"https://api.iucnredlist.org/api/v4/taxa/scientific_name",
                headers={
                    "authorization": os.getenv("IUCN_API_KEY"),
                    "accept": "application/json",
                },
                params={
                    "genus_name": genus_name,
                    "species_name": species_name,
                },
                timeout=30,
            )

            if response.status_code != 200:
                api_errors += 1
                _log(
                    f"[{idx}/{total}] {species.scientific_name} - HTTP {response.status_code}",
                    "ERRO",
                )
                time.sleep(1)
                continue

            data = response.json()

            if not isinstance(data, dict):
                invalid_response += 1
                _log(
                    f"[{idx}/{total}] {species.scientific_name} - resposta invalida",
                    "ERRO",
                )
                time.sleep(1)
                continue

            assessments = data.get("assessments")
            if not isinstance(assessments, list):
                invalid_response += 1
                _log(
                    f"[{idx}/{total}] {species.scientific_name} - assessments invalido",
                    "ERRO",
                )
                time.sleep(1)
                continue

            latest_assessment = next(
                (assessment for assessment in assessments if assessment.get("latest", False)),
                None,
            )

            if not latest_assessment:
                no_latest_assessment += 1
                _log(
                    f"[{idx}/{total}] {species.scientific_name} - sem assessment latest",
                    "ERRO",
                )
            else:
                conservation_status = latest_assessment.get("red_list_category_code")
                assessment_id = latest_assessment.get("assessment_id")

                Species.query.filter_by(id=species.id).update(
                    {"iucn_redlist": assessment_id},
                    synchronize_session=False,
                )
                SpeciesCharacteristics.query.filter_by(species_id=species.id).update(
                    {"conservation_status": conservation_status},
                    synchronize_session=False,
                )

                db.session.commit()
                updated += 1
                _log(
                    f"[{idx}/{total}] Atualizado: {species.scientific_name} -> {conservation_status}",
                    "OK",
                )

            time.sleep(1)

    _log(
        "Atualizadas: "
        f"{updated} | Nome invalido: {invalid_name} | Erros API: {api_errors} | "
        f"Resposta invalida: {invalid_response} | Sem latest: {no_latest_assessment}",
        "RESUMO",
    )
    _log("Importacao finalizada", "OK")


if __name__ == "__main__":
    main()
