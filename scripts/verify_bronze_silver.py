from pathlib import Path
import pandas as pd

bronze_dir = Path("data/bronze/online_retail_ii")
silver_dir = Path("data/silver/online_retail_ii")

if not bronze_dir.exists():
    raise FileNotFoundError(f"Dossier Bronze introuvable : {bronze_dir}")

if not silver_dir.exists():
    raise FileNotFoundError(f"Dossier Silver introuvable : {silver_dir}")

bronze_files = sorted(bronze_dir.glob("*.parquet"))

if not bronze_files:
    raise FileNotFoundError("Aucun fichier Parquet trouvé dans Bronze.")

print("\n=== Vérification Bronze / Silver ===\n")

for bronze_file in bronze_files:
    silver_file = silver_dir / bronze_file.name

    if not silver_file.exists():
        print(f"[ERREUR] Fichier Silver manquant : {bronze_file.name}")
        continue

    bronze_df = pd.read_parquet(bronze_file)
    silver_df = pd.read_parquet(silver_file)

    same_rows = len(bronze_df) == len(silver_df)

    print(f"Fichier : {bronze_file.name}")
    print(f"  Bronze : {len(bronze_df):,} lignes")
    print(f"  Silver : {len(silver_df):,} lignes")
    print(f"  Nombre de lignes identique : {'OUI' if same_rows else 'NON'}")
    print()
