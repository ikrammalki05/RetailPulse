from getpass import getpass

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from load_gold_to_postgres import FILES, DB_HOST, DB_PORT, DB_NAME, DB_USER


def main():
    password = getpass(f"Mot de passe PostgreSQL pour {DB_USER} : ")

    url = URL.create(
        drivername="postgresql+psycopg",
        username=DB_USER,
        password=password,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )

    engine = create_engine(url, pool_pre_ping=True)

    try:
        with engine.connect() as conn:
            print("\n=== SCHEMA POSTGRESQL ===")

            for table_name, parquet_path in FILES.items():
                print(f"\n--- gold.{table_name} ---")

                columns = conn.execute(
                    text("""
                        SELECT column_name, data_type, ordinal_position
                        FROM information_schema.columns
                        WHERE table_schema = 'gold'
                          AND table_name = :table_name
                        ORDER BY ordinal_position
                    """),
                    {"table_name": table_name},
                ).fetchall()

                if not columns:
                    print("[ERREUR] Table absente.")
                    continue

                pg_columns = [row[0] for row in columns]
                for name, dtype, position in columns:
                    print(f"{position:>2}. {name} ({dtype})")

                count = conn.execute(
                    text(f'SELECT COUNT(*) FROM gold."{table_name}"')
                ).scalar_one()

                df = pd.read_parquet(parquet_path)
                parquet_columns = list(df.columns)

                print(f"\nLignes PostgreSQL : {count:,}")
                print(f"Lignes Parquet    : {len(df):,}")
                print(f"Colonnes Parquet  : {len(parquet_columns)}")

                missing_pg = [
                    col for col in parquet_columns if col not in pg_columns
                ]
                extra_pg = [
                    col for col in pg_columns if col not in parquet_columns
                ]

                print("Colonnes Parquet absentes de PostgreSQL :", missing_pg)
                print("Colonnes PostgreSQL absentes de Parquet :", extra_pg)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
