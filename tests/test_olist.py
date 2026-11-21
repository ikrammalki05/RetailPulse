
from pathlib import Path
import pandas as pd

DATA_DIR = Path("data/source/olist")

for file in sorted(DATA_DIR.glob("*.xlsx")):
    try:
        df = pd.read_excel(file, engine="openpyxl")
        print(f"\nFichier : {file.name}")
        print(f"Nombre de lignes : {len(df):,}")
        print(f"Nombre de colonnes : {len(df.columns)}")
        print(f"Colonnes : {list(df.columns)}")
    except Exception as e:
        print(f"Erreur pour {file.name} : {e}")
