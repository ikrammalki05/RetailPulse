from pathlib import Path
import pandas as pd

DATA_DIR = Path("data/source/olist")

for file_path in sorted(DATA_DIR.glob("*.csv")):
    df = pd.read_csv(file_path, nrows=5)

    print(f"\nFichier : {file_path.name}")
    print(f"Colonnes : {list(df.columns)}")
    print(f"Types :\n{df.dtypes}")
    print(f"Aperçu :\n{df.head(3)}")