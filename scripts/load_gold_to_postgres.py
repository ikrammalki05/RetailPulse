from pathlib import Path
from getpass import getpass
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text, Date, DateTime
from sqlalchemy.engine import URL


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
GOLD_DIR = BASE_DIR / "data" / "gold" / "online_retail_ii"

FILES = {
    "sales": GOLD_DIR / "gold_sales.parquet",
    "daily_sales": GOLD_DIR / "gold_daily_sales.parquet",
    "product_performance": GOLD_DIR / "gold_product_performance.parquet",
}

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "RetailPulse"
DB_USER = "postgres"

# Taille modérée pour limiter la taille des requêtes INSERT multi-values.
CHUNK_SIZE = 500


# ============================================================
# LECTURE DES FICHIERS GOLD
# ============================================================

def read_gold_files():
    """Lit les fichiers Gold et vérifie leur présence."""

    dataframes = {}

    for table_name, file_path in FILES.items():
        if not file_path.exists():
            raise FileNotFoundError(f"Fichier introuvable : {file_path}")

        df = pd.read_parquet(file_path)

        if df.empty:
            raise ValueError(f"Le fichier {file_path.name} est vide.")

        dataframes[table_name] = df

        print(
            f"[OK] {file_path.name} : "
            f"{len(df):,} lignes, {len(df.columns)} colonnes"
        )
        print(f"     Colonnes : {list(df.columns)}")

    return dataframes


# ============================================================
# VÉRIFICATION DES TABLES POSTGRESQL
# ============================================================

def validate_database(conn, dataframes):
    """Vérifie l'existence des tables et la compatibilité des colonnes."""

    required_tables = {
        "sales",
        "daily_sales",
        "product_performance",
        "etl_load_log",
    }

    existing_tables = set(
        conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'gold'
                  AND table_type = 'BASE TABLE'
            """)
        ).scalars().all()
    )

    missing_tables = required_tables - existing_tables
    if missing_tables:
        raise RuntimeError(
            "Tables absentes dans le schéma gold : "
            + ", ".join(sorted(missing_tables))
        )

    for table_name, df in dataframes.items():
        db_columns = set(
            conn.execute(
                text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'gold'
                      AND table_name = :table_name
                """),
                {"table_name": table_name},
            ).scalars().all()
        )

        missing_columns = set(df.columns) - db_columns
        if missing_columns:
            raise RuntimeError(
                f"Colonnes manquantes dans gold.{table_name} : "
                + ", ".join(sorted(missing_columns))
            )

    print("[OK] Tables et colonnes vérifiées.")


# ============================================================
# NORMALISATION DES TYPES
# ============================================================

def normalize_dataframe_for_postgres(df, table_name, conn):
    """
    Aligne les colonnes date/date-heure du DataFrame sur les types
    PostgreSQL. Les colonnes DATE sont converties en objets date Python,
    et les colonnes TIMESTAMP en datetime.
    """
    df = df.copy()

    db_types = conn.execute(
        text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'gold'
              AND table_name = :table_name
        """),
        {"table_name": table_name},
    ).mappings().all()

    type_map = {row["column_name"]: row["data_type"] for row in db_types}

    for column in df.columns:
        pg_type = type_map.get(column)

        if pg_type == "date":
            # Pandas peut lire les dates Parquet comme chaînes ou timestamps.
            converted = pd.to_datetime(df[column], errors="raise")
            df[column] = converted.dt.date

        elif pg_type in ("timestamp without time zone", "timestamp with time zone"):
            converted = pd.to_datetime(df[column], errors="raise")

            if pg_type == "timestamp without time zone":
                # Retire un éventuel fuseau horaire sans modifier l'heure locale.
                if getattr(converted.dt, "tz", None) is not None:
                    converted = converted.dt.tz_localize(None)
            else:
                # PostgreSQL TIMESTAMPTZ attend des valeurs cohérentes avec fuseau.
                if getattr(converted.dt, "tz", None) is None:
                    converted = converted.dt.tz_localize("UTC")
                else:
                    converted = converted.dt.tz_convert("UTC")

            df[column] = converted

    return df


# ============================================================
# CHARGEMENT DANS POSTGRESQL
# ============================================================

def load_to_postgres(dataframes, engine):
    """Remplace les données Gold et vérifie chaque chargement."""

    load_results = []

    with engine.begin() as conn:
        # Valider avant de vider les tables.
        validate_database(conn, dataframes)

        started_at = datetime.now()

        conn.execute(
            text("""
                TRUNCATE TABLE
                    gold.sales,
                    gold.daily_sales,
                    gold.product_performance
                RESTART IDENTITY
            """)
        )

        for table_name, df in dataframes.items():
            print(f"\nChargement de gold.{table_name}...")

            df_to_load = normalize_dataframe_for_postgres(
                df=df,
                table_name=table_name,
                conn=conn,
            )

            # Important : Pandas peut inférer VARCHAR pour une colonne
            # contenant des objets date Python. On précise donc les types
            # SQLAlchemy d'après le vrai schéma PostgreSQL.
            db_types = conn.execute(
                text("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'gold'
                      AND table_name = :table_name
                """),
                {"table_name": table_name},
            ).mappings().all()

            dtype_map = {}
            for column_info in db_types:
                column = column_info["column_name"]
                pg_type = column_info["data_type"]
                if column not in df_to_load.columns:
                    continue
                if pg_type == "date":
                    dtype_map[column] = Date()
                elif pg_type == "timestamp without time zone":
                    dtype_map[column] = DateTime(timezone=False)
                elif pg_type == "timestamp with time zone":
                    dtype_map[column] = DateTime(timezone=True)

            # Multi-values peut dépasser les limites de paramètres SQL avec
            # de gros lots ; un lot de 500 lignes limite ce risque.
            df_to_load.to_sql(
                name=table_name,
                con=conn,
                schema="gold",
                if_exists="append",
                index=False,
                chunksize=CHUNK_SIZE,
                method="multi",
                dtype=dtype_map or None,
            )

            expected_rows = len(df_to_load)
            actual_rows = conn.execute(
                text(f"SELECT COUNT(*) FROM gold.{table_name}")
            ).scalar_one()

            if actual_rows != expected_rows:
                raise RuntimeError(
                    f"Erreur pour gold.{table_name} : "
                    f"{expected_rows:,} lignes attendues, "
                    f"{actual_rows:,} lignes trouvées."
                )

            print(
                f"[OK] {table_name} : "
                f"{actual_rows:,} lignes chargées."
            )

            load_results.append({
                "table_name": table_name,
                "rows_loaded": actual_rows,
            })

        completed_at = datetime.now()

        for result in load_results:
            conn.execute(
                text("""
                    INSERT INTO gold.etl_load_log (
                        pipeline_name,
                        source_name,
                        target_table,
                        rows_loaded,
                        status,
                        started_at,
                        completed_at
                    )
                    VALUES (
                        :pipeline_name,
                        :source_name,
                        :target_table,
                        :rows_loaded,
                        :status,
                        :started_at,
                        :completed_at
                    )
                """),
                {
                    "pipeline_name": "RetailPulse Gold ETL",
                    "source_name": str(GOLD_DIR),
                    "target_table": result["table_name"],
                    "rows_loaded": result["rows_loaded"],
                    "status": "SUCCESS",
                    "started_at": started_at,
                    "completed_at": completed_at,
                },
            )

    return load_results


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():
    print("=" * 60)
    print("RETAILPULSE - CHARGEMENT GOLD VERS POSTGRESQL")
    print("=" * 60)

    dataframes = read_gold_files()

    print("\nConnexion à PostgreSQL...")

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
            conn.execute(text("SELECT 1"))

        print("[OK] Connexion PostgreSQL établie.")
        print(
            "\nATTENTION : les données actuellement présentes "
            "dans les trois tables Gold seront remplacées."
        )

        confirmation = input(
            "Tape OUI pour lancer le chargement : "
        ).strip().upper()

        if confirmation != "OUI":
            print("Chargement annulé. Aucune table n'a été vidée.")
            return

        results = load_to_postgres(dataframes, engine)

        print("\n" + "=" * 60)
        print("CHARGEMENT TERMINÉ AVEC SUCCÈS")
        print("=" * 60)

        for result in results:
            print(
                f"gold.{result['table_name']} : "
                f"{result['rows_loaded']:,} lignes"
            )

        print("\nVérification finale dans PostgreSQL :")
        with engine.connect() as conn:
            for table_name in FILES:
                count = conn.execute(
                    text(f"SELECT COUNT(*) FROM gold.{table_name}")
                ).scalar_one()
                print(f"  {table_name} = {count:,}")

            log_count = conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM gold.etl_load_log
                    WHERE pipeline_name = :pipeline_name
                      AND status = 'SUCCESS'
                """),
                {"pipeline_name": "RetailPulse Gold ETL"},
            ).scalar_one()

            print(f"  Chargements réussis journalisés : {log_count}")

    except Exception as exc:
        print(f"\n[ERREUR] Le chargement a échoué : {exc}")
        print(
            "La transaction est annulée si l'erreur survient "
            "pendant le chargement transactionnel."
        )
        raise

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
