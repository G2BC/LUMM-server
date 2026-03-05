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


def main():
    print("Starting IUCN Red List status import")

    with app.app_context():
        species = Species.query.all()
        for species in species:
            print(f"Searching - {species.scientific_name}")

            genus_name, species_name = species.scientific_name.split(" ")

            print(f"Genus: {genus_name} - Species: {species_name}")

            response = requests.get(
                f"https://api.iucnredlist.org/api/v4/taxa/scientific_name",
                headers={
                    "authorization": os.getenv('IUCN_API_KEY'),
                    "accept": "application/json"
                },
                params={
                    "genus_name": genus_name,
                    "species_name": species_name
                }
            )
            
            if response.status_code == 200:
                data = response.json()

                if not isinstance(data, dict):
                    print(f"Error: {species.scientific_name} - Invalid response format")
                    continue

                assessments = data.get("assessments")
                if not isinstance(assessments, list):
                    print(f"Error: {species.scientific_name} - Invalid assessments format")
                    continue

                for assessment in assessments:
                    if assessment.get("latest", False):
                        conservation_status = assessment.get("red_list_category_code")
                        assessment_id = assetment.get("assessment_id")

                        Species.query.filter_by(id=species.id).update(
                            {"iucn_redlist": assessment_id},
                            synchronize_session=False,
                        )
                        SpeciesCharacteristics.query.filter_by(species_id=species.id).update(
                            {"conservation_status": conservation_status},
                            synchronize_session=False,
                        )

                        db.session.commit()
                    else:
                        print(f"Error: {species.scientific_name} - No assessment")
            else:
                print(f"Error: {response.status_code} - {response.text}")
            
            time.sleep(1)

if __name__ == "__main__":
    main()
