from pathlib import Path
import pandas as pd

# Chemin vers la couche Bronze
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze" / "online_retail_ii"


def main():
    if not BRONZE_DIR.exists():
        raise FileNotFoundError(
            f"Dossier Bronze introuvable : {BRONZE_DIR}"
        )

    parquet_files = sorted(BRONZE_DIR.glob("*.parquet"))

    if not parquet_files:
        print("Aucun fichier Parquet trouvé dans la couche Bronze.")
        return

    for file_path in parquet_files:
        print("\n" + "=" * 60)
        print(f"Fichier : {file_path.name}")

        df = pd.read_parquet(file_path)

        print(f"\nDimensions : {df.shape}")

        print("\nTypes des colonnes :")
        print(df.dtypes)

        print("\nAperçu des 3 premières lignes :")
        print(df.head(3).to_string(index=False))

        print("\nValeurs manquantes par colonne :")
        print(df.isna().sum())

        print(f"\nNombre de lignes dupliquées : {df.duplicated().sum()}")


if __name__ == "__main__":
    main()
