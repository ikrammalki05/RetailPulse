
from pathlib import Path
import logging

import pandas as pd

# Racine du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = PROJECT_ROOT / "data" / "source" / "olist"
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze" / "olist"

BRONZE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def ingest_csv(file_path: Path) -> None:
    """Lit un CSV source et le copie dans Bronze au format Parquet."""
    logger.info("Lecture de %s", file_path.name)

    df = pd.read_csv(file_path)

    output_path = BRONZE_DIR / f"{file_path.stem}.parquet"
    df.to_parquet(output_path, index=False)

    logger.info(
        "Ingestion terminée : %s lignes, %s colonnes -> %s",
        len(df),
        len(df.columns),
        output_path.name,
    )


def main() -> None:
    if not SOURCE_DIR.is_dir():
        raise FileNotFoundError(
            f"Dossier source introuvable : {SOURCE_DIR}"
        )

    files = sorted(SOURCE_DIR.glob("*.csv"))

    if not files:
        raise FileNotFoundError(
            f"Aucun fichier CSV trouvé dans {SOURCE_DIR}"
        )

    logger.info("%s fichiers CSV détectés.", len(files))

    for file_path in files:
        try:
            ingest_csv(file_path)
        except Exception:
            logger.exception("Échec de l'ingestion de %s", file_path.name)
            raise

    logger.info("Pipeline Bronze terminé.")


if __name__ == "__main__":
    main()
