
from pathlib import Path

import pandas as pd


# ============================================================
# 1. CONFIGURATION
# ============================================================

SILVER_DIR = Path("data/silver/online_retail_ii")
GOLD_DIR = Path("data/gold/online_retail_ii")

REQUIRED_COLUMNS = [
    "invoice",
    "stock_code",
    "description",
    "quantity",
    "invoice_date",
    "price",
    "customer_id",
    "country",
]


# ============================================================
# 2. CHARGEMENT DES DONNEES SILVER
# ============================================================

def load_silver_data():
    """Charge et combine les fichiers Parquet de Silver."""

    if not SILVER_DIR.exists():
        raise FileNotFoundError(
            f"Dossier Silver introuvable : {SILVER_DIR.resolve()}"
        )

    files = sorted(SILVER_DIR.glob("*.parquet"))

    if not files:
        raise FileNotFoundError(
            f"Aucun fichier Parquet trouve dans {SILVER_DIR}"
        )

    dataframes = []

    for file in files:
        print(f"[LECTURE] {file.name}")

        df = pd.read_parquet(file)

        missing_columns = [
            column
            for column in REQUIRED_COLUMNS
            if column not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Colonnes manquantes dans {file.name} : "
                f"{missing_columns}"
            )

        # Conserver la provenance du fichier source.
        if "source_file" not in df.columns:
            df["source_file"] = file.name

        dataframes.append(df)

    combined = pd.concat(dataframes, ignore_index=True)

    print(f"\nNombre total de lignes Silver : {len(combined):,}")

    return combined


# ============================================================
# 3. CLASSIFICATION DES TRANSACTIONS
# ============================================================

def classify_transactions(df):
    """
    Classification des lignes :
    - cancellation : facture commençant par C
    - adjustment   : ajustement comptable identifié
    - return       : quantité négative hors annulation/ajustement
    - invalid      : ligne ne respectant pas les règles de vente
    - sale         : vente valide
    """

    df = df.copy()

    # Normalisation des champs.
    df["invoice"] = df["invoice"].astype("string").str.strip()
    df["stock_code"] = df["stock_code"].astype("string").str.strip()
    df["country"] = df["country"].astype("string").str.strip()

    df["quantity"] = pd.to_numeric(
        df["quantity"], errors="coerce"
    )

    df["price"] = pd.to_numeric(
        df["price"], errors="coerce"
    )

    df["invoice_date"] = pd.to_datetime(
        df["invoice_date"], errors="coerce"
    )

    # Montant signé informatif : quantité x prix.
    # Ce montant n'est pas automatiquement le montant net comptable.
    df["line_amount"] = df["quantity"] * df["price"]

    # Annulations : numéro de facture commençant par C.
    is_cancellation = (
        df["invoice"]
        .str.upper()
        .str.startswith("C", na=False)
    )

    # Ajustements comptables connus.
    description_normalized = (
        df["description"]
        .astype("string")
        .str.strip()
        .str.casefold()
    )

    is_adjustment = (
        description_normalized
        .eq("adjust bad debt")
        .fillna(False)
    )

    # Retours : quantité négative.
    is_return = (
        df["quantity"].notna()
        & (df["quantity"] < 0)
    )

    # Critères d'invalidité d'une vente.
    is_invalid = (
        df["quantity"].isna()
        | (df["quantity"] <= 0)
        | df["price"].isna()
        | (df["price"] <= 0)
        | df["invoice_date"].isna()
        | df["invoice"].isna()
        | df["stock_code"].isna()
        | (df["stock_code"] == "")
    )

    # Priorité : annulation, ajustement, retour, invalide, vente.
    conditions = [
        is_cancellation,
        ~is_cancellation & is_adjustment,
        ~is_cancellation & ~is_adjustment & is_return,
        (
            ~is_cancellation
            & ~is_adjustment
            & ~is_return
            & is_invalid
        ),
    ]

    choices = [
        "cancellation",
        "adjustment",
        "return",
        "invalid",
    ]

    df["transaction_type"] = pd.Series(
        "sale",
        index=df.index,
        dtype="string",
    )

    for condition, choice in zip(conditions, choices):
        df.loc[condition, "transaction_type"] = choice

    # Indicateurs commerciaux : seules les ventes sont comptabilisées.
    is_sale = df["transaction_type"] == "sale"

    df["sales_quantity"] = df["quantity"].where(is_sale, 0)

    df["sales_revenue"] = (
        df["quantity"] * df["price"]
    ).where(is_sale, 0)

    # Colonnes temporelles pour les analyses.
    df["sale_date"] = df["invoice_date"].dt.date

    df["sale_month"] = (
        df["invoice_date"]
        .dt.to_period("M")
        .astype("string")
    )

    return df


# ============================================================
# 4. CREATION DE GOLD_SALES
# ============================================================

def build_gold_sales(df):
    """Conserve le détail de toutes les lignes classifiées."""

    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    output_file = GOLD_DIR / "gold_sales.parquet"

    df.to_parquet(output_file, index=False)

    print(f"[OK] Detail des transactions : {output_file}")

    return df


# ============================================================
# 5. CREATION DE GOLD_DAILY_SALES
# ============================================================

def build_daily_sales(df):
    """Agrège les ventes valides par jour."""

    sales = df[df["transaction_type"] == "sale"].copy()

    daily = (
        sales.groupby("sale_date", dropna=False)
        .agg(
            revenue=("sales_revenue", "sum"),
            quantity_sold=("sales_quantity", "sum"),
            transaction_lines=("invoice", "size"),
            distinct_invoices=("invoice", "nunique"),
            distinct_customers=("customer_id", "nunique"),
        )
        .reset_index()
        .sort_values("sale_date")
    )

    daily["sale_date"] = daily["sale_date"].astype("string")

    output_file = GOLD_DIR / "gold_daily_sales.parquet"

    daily.to_parquet(output_file, index=False)

    print(f"[OK] Ventes quotidiennes : {output_file}")

    return daily


# ============================================================
# 6. CREATION DE GOLD_PRODUCT_PERFORMANCE
# ============================================================

def build_product_performance(df):
    """Calcule les indicateurs de performance des produits."""

    sales = df[df["transaction_type"] == "sale"].copy()

    # Remplacer les descriptions absentes pour le regroupement.
    sales["product_description"] = (
        sales["description"]
        .fillna("Unknown product")
        .astype("string")
        .str.strip()
        .replace("", "Unknown product")
    )

    products = (
        sales.groupby(
            ["stock_code", "product_description"],
            dropna=False,
        )
        .agg(
            revenue=("sales_revenue", "sum"),
            quantity_sold=("sales_quantity", "sum"),
            transaction_lines=("invoice", "size"),
            distinct_invoices=("invoice", "nunique"),
            distinct_customers=("customer_id", "nunique"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
    )

    output_file = GOLD_DIR / "gold_product_performance.parquet"

    products.to_parquet(output_file, index=False)

    print(f"[OK] Performance des produits : {output_file}")

    return products


# ============================================================
# 7. RAPPORT DE CONTROLE GOLD
# ============================================================

def build_quality_report(df):
    """Enregistre les volumes et anomalies détectés."""

    transaction_types = [
        "sale",
        "cancellation",
        "adjustment",
        "return",
        "invalid",
    ]

    counts = (
        df["transaction_type"]
        .value_counts()
        .reindex(transaction_types, fill_value=0)
    )

    report = pd.DataFrame(
        [
            {
                "metric": "total_rows",
                "value": len(df),
            },
            {
                "metric": "valid_sales",
                "value": int(counts["sale"]),
            },
            {
                "metric": "cancellations",
                "value": int(counts["cancellation"]),
            },
            {
                "metric": "adjustments",
                "value": int(counts["adjustment"]),
            },
            {
                "metric": "returns",
                "value": int(counts["return"]),
            },
            {
                "metric": "invalid_rows",
                "value": int(counts["invalid"]),
            },
            {
                "metric": "missing_customer_id",
                "value": int(df["customer_id"].isna().sum()),
            },
            {
                "metric": "exact_duplicate_rows",
                "value": int(df.duplicated().sum()),
            },
        ]
    )

    output_file = GOLD_DIR / "gold_quality_report.csv"

    report.to_csv(output_file, index=False)

    print(f"[OK] Rapport qualite : {output_file}")

    print("\nRepartition des lignes :")

    for transaction_type, count in counts.items():
        print(f"  {transaction_type}: {count:,}")

    return report


# ============================================================
# 8. EXECUTION PRINCIPALE
# ============================================================

def main():
    print("=" * 60)
    print("RETAILPULSE - CONSTRUCTION DE LA COUCHE GOLD")
    print("=" * 60)

    silver_df = load_silver_data()

    classified_df = classify_transactions(silver_df)

    # Les fichiers Gold seront écrits uniquement lors de l'exécution.
    build_gold_sales(classified_df)
    build_daily_sales(classified_df)
    build_product_performance(classified_df)
    build_quality_report(classified_df)

    print("\n" + "=" * 60)
    print("COUCHE GOLD GENEREE AVEC SUCCES")
    print(f"Dossier de sortie : {GOLD_DIR.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
