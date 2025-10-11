import math
import os

import pandas as pd
from app import create_app
from app.extensions import db
from app.models.species import Species
from app.models.taxon import Taxon

EXCEL_PATH = os.getenv("EXCEL_PATH", "MBList.xlsx")
SHEET = os.getenv("SHEET", "Sheet1")

app = create_app()

_txt = (
    lambda v: (s := str(v).strip()) and s
    if v not in (None, "") and not (isinstance(v, float) and math.isnan(v))
    else None
)


def _i(v):
    if v in (None, "") or (isinstance(v, float) and math.isnan(v)):
        return None
    try:
        return int(float(str(v).strip()))
    except:
        return None


def main():
    print(">> Carregando chaves do banco…")
    with app.app_context():
        species_rows = (
            db.session.query(
                Species.id,
                Species.mycobank_index_fungorum_id,
            )
            .filter(Species.mycobank_index_fungorum_id.isnot(None))
            .all()
        )

    mb_ids = {r.mycobank_index_fungorum_id for r in species_rows}
    print(f">> Espécies com MycoBank ID no banco: {len(mb_ids)}")

    usecols = [
        "MycoBank #",
        "Classification",
        "Synonymy",
        "Authors",
        "Year of effective publication",
    ]
    print(">> Lendo XLSX (somente colunas necessárias)…")

    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET, usecols=usecols, engine="openpyxl")

    before = len(df)
    df = df[df["MycoBank #"].isin(mb_ids)]
    print(f">> Filtrado XLSX: {len(df)}/{before} linhas correspondentes")

    df.rename(
        columns={
            "MycoBank #": "mb_id",
            "Classification": "classification",
            "Synonymy": "synonyms",
            "Authors": "authors",
            "Year of effective publication": "year",
        },
        inplace=True,
    )

    inserted = updated = linked = 0

    with app.app_context():
        species_by_mb = {r.mycobank_index_fungorum_id: r for r in species_rows}

        for idx, row in enumerate(df.to_dict(orient="records"), start=1):
            mb_id = _i(row.get("mb_id"))
            if not mb_id:
                continue

            srow = species_by_mb.get(mb_id)
            if not srow:
                continue

            taxon = Taxon.query.filter_by(species_id=srow.id).one_or_none()
            if not taxon:
                taxon = Taxon(species_id=srow.id)
                db.session.add(taxon)
                inserted += 1
            else:
                updated += 1

            if val := _txt(row.get("classification")):
                taxon.classification = val
            if val := _txt(row.get("synonyms")):
                taxon.synonyms = val
            if val := _txt(row.get("authors")):
                taxon.authors = val
            if val := _txt(row.get("year")):
                taxon.years_of_effective_publication = val

            linked += 1
            if idx <= 5:
                print(f"-- Vinculado species_id={srow.id} MycoBank={mb_id}")

        db.session.commit()

    print("== RESUMO ==")
    print(f"Inseridos: {inserted} | Atualizados: {updated} | Vinculados: {linked}")
    print(">> IMPORTAÇÃO FINALIZADA")


if __name__ == "__main__":
    main()
