
from pathlib import Path
import logging

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SOURCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "source"
    / "online_retail_ii"
    / "online_retail_II.xlsx"
)

BRONZE_DIR = PROJECT_ROOT / "data" / "bronze" / "online_retail_ii"
BRONZE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    if not SOURCE_FILE.is_file():
        raise FileNotFoundError(f"Fichier introuvable : {SOURCE_FILE}")

    logger.info("Lecture du fichier Excel : %s", SOURCE_FILE.name)

    # Online Retail II peut contenir plusieurs feuilles Excel.
    sheets = pd.read_excel(
        SOURCE_FILE,
        sheet_name=None,
        engine="openpyxl",
    )

    total_rows = 0

    for sheet_name, df in sheets.items():
        if df.empty:
            logger.warning("Feuille vide ignorée : %s", sheet_name)
            continue

        # Normaliser les noms des colonnes
        df.columns = [
            str(column).strip().replace(" ", "_")
            for column in df.columns
        ]

        # Uniformiser la colonne Invoice :
        # certaines factures ont un préfixe, par exemple C489449.
        if "Invoice" in df.columns:
            df["Invoice"] = df["Invoice"].astype("string")

        # Éviter les conflits de types dans les autres colonnes
        # qui pourraient contenir des valeurs mixtes.
        for column in df.select_dtypes(include=["object"]).columns:
            df[column] = df[column].astype("string")

        output_file = BRONZE_DIR / f"{sheet_name}.parquet"

        df.to_parquet(
            output_file,
            index=False,
            engine="pyarrow"
        )

        total_rows += len(df)

        logger.info(
            "Feuille %s : %s lignes, %s colonnes -> %s",
            sheet_name,
            len(df),
            len(df.columns),
            output_file.name,
        )

    logger.info("Ingestion terminée : %s lignes au total.", total_rows)


if __name__ == "__main__":
    main()
