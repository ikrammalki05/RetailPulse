from pathlib import Path

import pandas as pd


GOLD_DIR = Path("data/gold/online_retail_ii")

SALES_FILE = GOLD_DIR / "gold_sales.parquet"
DAILY_FILE = GOLD_DIR / "gold_daily_sales.parquet"
PRODUCT_FILE = GOLD_DIR / "gold_product_performance.parquet"
REPORT_FILE = GOLD_DIR / "gold_quality_report.csv"

ALLOWED_TYPES = {
    "sale",
    "cancellation",
    "adjustment",
    "return",
    "invalid",
}

NON_COMMERCIAL_TYPES = {
    "cancellation",
    "adjustment",
    "return",
    "invalid",
}


def check_file_exists(path):
    assert path.exists(), f"Fichier manquant : {path}"
    print(f"[OK] Fichier present : {path.name}")


def main():
    print("=" * 60)
    print("RETAILPULSE - TESTS DE QUALITE GOLD")
    print("=" * 60)

    # 1. Presence des fichiers
    for path in [SALES_FILE, DAILY_FILE, PRODUCT_FILE, REPORT_FILE]:
        check_file_exists(path)

    # 2. Chargement
    sales = pd.read_parquet(SALES_FILE)
    daily = pd.read_parquet(DAILY_FILE)
    products = pd.read_parquet(PRODUCT_FILE)
    report = pd.read_csv(REPORT_FILE)

    # 3. Nombre total de lignes
    total_row = report.loc[
        report["metric"] == "total_rows", "value"
    ]

    assert len(total_row) == 1, (
        "Le rapport doit contenir exactement une metrique total_rows."
    )

    expected_total = int(total_row.iloc[0])

    assert len(sales) == expected_total, (
        f"Nombre de lignes incoherent : "
        f"Gold={len(sales)}, rapport={expected_total}"
    )

    print(f"[OK] Nombre de lignes : {len(sales):,}")

    # 4. Classification
    assert sales["transaction_type"].notna().all(), (
        "Certaines lignes n'ont pas de classification."
    )

    actual_types = set(sales["transaction_type"].unique())

    assert actual_types.issubset(ALLOWED_TYPES), (
        f"Classification inconnue : {actual_types - ALLOWED_TYPES}"
    )

    counts = sales["transaction_type"].value_counts()

    assert int(counts.sum()) == len(sales), (
        "La somme des categories ne correspond pas au total."
    )

    print("[OK] Classification des transactions")

    print("\nRepartition des transactions :")
    for transaction_type in sorted(ALLOWED_TYPES):
        print(
            f"  {transaction_type:15s}: "
            f"{int(counts.get(transaction_type, 0)):>10,}"
        )

    # 5. Validite des ventes
    valid_sales = sales[sales["transaction_type"] == "sale"]

    assert valid_sales["quantity"].notna().all(), (
        "Une vente possede une quantite manquante."
    )
    assert (valid_sales["quantity"] > 0).all(), (
        "Une vente possede une quantite non positive."
    )
    assert valid_sales["price"].notna().all(), (
        "Une vente possede un prix manquant."
    )
    assert (valid_sales["price"] > 0).all(), (
        "Une vente possede un prix non positif."
    )
    assert valid_sales["invoice_date"].notna().all(), (
        "Une vente possede une date manquante."
    )

    print(f"[OK] Lignes de vente valides : {len(valid_sales):,}")

    # 6. Chiffre d'affaires des ventes
    expected_revenue = (
        valid_sales["quantity"] * valid_sales["price"]
    )
    actual_revenue = valid_sales["sales_revenue"]

    assert actual_revenue.notna().all(), (
        "Le chiffre d'affaires contient des valeurs manquantes."
    )
    assert (actual_revenue >= 0).all(), (
        "Le chiffre d'affaires des ventes contient une valeur negative."
    )
    assert (
        (expected_revenue - actual_revenue).abs() < 1e-8
    ).all(), "Le calcul du chiffre d'affaires est incoherent."

    assert valid_sales["sales_quantity"].notna().all(), (
        "La quantite vendue contient des valeurs manquantes."
    )
    assert (
        valid_sales["sales_quantity"] == valid_sales["quantity"]
    ).all(), "La quantite commerciale ne correspond pas aux ventes."

    print(f"[OK] Chiffre d'affaires : {actual_revenue.sum():,.2f}")

    # 7. Les transactions non commerciales ne contribuent pas aux ventes
    non_commercial = sales[
        sales["transaction_type"].isin(NON_COMMERCIAL_TYPES)
    ]

    assert (non_commercial["sales_revenue"] == 0).all(), (
        "Une transaction non commerciale contribue au chiffre d'affaires."
    )

    assert (non_commercial["sales_quantity"] == 0).all(), (
        "Une transaction non commerciale contribue aux quantites vendues."
    )

    print(
        "[OK] Aucune contribution des annulations, ajustements, "
        "retours et lignes invalides aux ventes"
    )

    # 8. Controle specifique des ajustements
    adjustments = sales[
        sales["transaction_type"] == "adjustment"
    ]

    if not adjustments.empty:
        descriptions = (
            adjustments["description"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.casefold()
        )

        assert descriptions.eq("adjust bad debt").all(), (
            "Un ajustement ne correspond pas a la description attendue."
        )

        assert (adjustments["sales_revenue"] == 0).all(), (
            "Un ajustement contribue au chiffre d'affaires."
        )

    print(f"[OK] Ajustements identifies : {len(adjustments):,}")

    # 9. Coherence des agregations
    assert daily["revenue"].notna().all(), (
        "Montant journalier manquant."
    )
    assert products["revenue"].notna().all(), (
        "Montant produit manquant."
    )
    assert (daily["revenue"] >= 0).all(), (
        "Montant journalier negatif inattendu."
    )
    assert (products["revenue"] >= 0).all(), (
        "Montant produit negatif inattendu."
    )

    daily_total = daily["revenue"].sum()
    product_total = products["revenue"].sum()
    sales_total = actual_revenue.sum()

    assert abs(daily_total - sales_total) < 0.01, (
        "Le total journalier ne correspond pas aux ventes."
    )
    assert abs(product_total - sales_total) < 0.01, (
        "Le total produit ne correspond pas aux ventes."
    )

    print("[OK] Agregations journalieres et produits coherentes")

    print("\n" + "=" * 60)
    print("TOUS LES TESTS SONT PASSES.")
    print("=" * 60)


if __name__ == "__main__":
    main()
