
from pathlib import Path
import logging

import pandas as pd


# --------------------------------------------------
# Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

BRONZE_DIR = PROJECT_ROOT / "data" / "bronze" / "online_retail_ii"
SILVER_DIR = PROJECT_ROOT / "data" / "silver" / "online_retail_ii"
REPORT_DIR = PROJECT_ROOT / "reports" / "quality"

SILVER_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


# --------------------------------------------------
# Transformation
# --------------------------------------------------

def transform_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise les colonnes et prépare les données Silver."""

    df = df.copy()

    # Normalisation explicite des noms de colonnes source.
    # InvoiceDate doit devenir invoice_date, et non invoicedate.
    column_mapping = {
        "Invoice": "invoice",
        "StockCode": "stock_code",
        "Description": "description",
        "Quantity": "quantity",
        "InvoiceDate": "invoice_date",
        "Price": "price",
        "Customer_ID": "customer_id",
        "Country": "country",
    }

    df.columns = [str(column).strip() for column in df.columns]
    df = df.rename(columns=column_mapping)

    # Vérifier la présence des colonnes attendues
    required_columns = list(column_mapping.values())
    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Colonnes manquantes dans le fichier source : "
            f"{missing_columns}. Colonnes disponibles : "
            f"{df.columns.tolist()}"
        )

    # Uniformiser les champs textuels
    text_columns = [
        "invoice",
        "stock_code",
        "description",
        "country",
    ]

    for column in text_columns:
        df[column] = df[column].astype("string").str.strip()

    # Les descriptions vides deviennent des valeurs manquantes
    df["description"] = df["description"].replace("", pd.NA)

    # Convertir les quantités en nombres entiers nullable
    df["quantity"] = pd.to_numeric(
        df["quantity"], errors="coerce"
    ).astype("Int64")

    # Convertir les prix
    df["price"] = pd.to_numeric(
        df["price"], errors="coerce"
    )

    # Convertir les identifiants clients en entiers nullable
    customer_id = pd.to_numeric(
        df["customer_id"], errors="coerce"
    )

    invalid_customer_ids = (
        customer_id.notna() & (customer_id % 1 != 0)
    )

    if invalid_customer_ids.any():
        logger.warning(
            "%s identifiants clients non entiers détectés.",
            int(invalid_customer_ids.sum()),
        )

    df["customer_id"] = (
        customer_id.where(~invalid_customer_ids).astype("Int64")
    )

    # Convertir les dates
    df["invoice_date"] = pd.to_datetime(
        df["invoice_date"], errors="coerce"
    )

    return df


# --------------------------------------------------
# Exécution et contrôles qualité
# --------------------------------------------------

def main():
    if not BRONZE_DIR.exists():
        raise FileNotFoundError(
            f"Dossier Bronze introuvable : {BRONZE_DIR}"
        )

    files = sorted(BRONZE_DIR.glob("*.parquet"))

    if not files:
        raise FileNotFoundError(
            f"Aucun fichier Parquet dans {BRONZE_DIR}"
        )

    quality_reports = []

    for file_path in files:
        logger.info("Lecture : %s", file_path.name)

        df = pd.read_parquet(file_path)
        original_rows = len(df)

        df = transform_dataframe(df)

        # Conserver la provenance des données
        df["source_file"] = file_path.name

        # Détecter les doublons exacts sans les supprimer
        duplicate_count = int(
            df.drop(columns=["source_file"]).duplicated().sum()
        )

        # Écrire le fichier Silver
        output_file = SILVER_DIR / file_path.name
        df.to_parquet(output_file, index=False, engine="pyarrow")

        # Calcul des indicateurs de qualité
        missing_values = df.isna().sum()

        report = {
            "source_file": file_path.name,
            "rows_read": original_rows,
            "rows_written": len(df),
            "columns": len(df.columns),
            "exact_duplicate_rows": duplicate_count,
            "missing_invoice_date": int(
                df["invoice_date"].isna().sum()
            ),
            "missing_description": int(
                df["description"].isna().sum()
            ),
            "missing_customer_id": int(
                df["customer_id"].isna().sum()
            ),
            "invalid_quantity": int(
                df["quantity"].isna().sum()
            ),
            "invalid_price": int(
                df["price"].isna().sum()
            ),
            "negative_quantity": int(
                (df["quantity"] < 0).fillna(False).sum()
            ),
            "negative_price": int(
                (df["price"] < 0).fillna(False).sum()
            ),
            "zero_price": int(
                (df["price"] == 0).fillna(False).sum()
            ),
        }

        quality_reports.append(report)

        logger.info(
            "Silver écrit : %s | lignes : %s | doublons détectés : %s",
            output_file.name,
            len(df),
            duplicate_count,
        )

        logger.info(
            "Valeurs manquantes par colonne :\n%s",
            missing_values.to_string(),
        )

    # Enregistrer le rapport de qualité
    report_df = pd.DataFrame(quality_reports)

    report_file = REPORT_DIR / "online_retail_quality.csv"
    report_df.to_csv(report_file, index=False)

    logger.info("Transformation Silver terminée.")
    logger.info("Rapport qualité : %s", report_file)
    logger.info(
        "Total des lignes Silver : %s",
        report_df["rows_written"].sum(),
    )


if __name__ == "__main__":
    main()
