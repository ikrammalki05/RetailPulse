"""Product performance with a product-level drill-down."""

import plotly.express as px
import streamlit as st

from dashboard_data import date_label, download_button, empty_state, filters, read, shared_filters

st.title("Product Analytics", icon=":material/inventory_2:")
st.caption("Classement filtré et exploration détaillée d’un produit.")
selection = shared_filters()
if selection is None:
    st.stop()
start, end, selected_countries, _bounds = selection
where, params = filters("s", start, end, selected_countries)

products = read(
    f"""SELECT s.stock_code AS reference,
               COALESCE(NULLIF(BTRIM(s.description), ''), 'Produit inconnu') AS product,
               SUM(s.sales_revenue) AS revenue,
               SUM(s.sales_quantity) AS quantity,
               COUNT(DISTINCT s.invoice) AS orders,
               COUNT(DISTINCT s.customer_id) AS customers
        FROM gold.sales s
        WHERE s.transaction_type = 'sale' AND {where}
          AND s.stock_code NOT IN ('POST', 'DOT', 'M')
        GROUP BY 1, 2 ORDER BY revenue DESC NULLS LAST""", params
)

st.subheader("Performance produit")
if empty_state(products):
    st.stop()
plot_col, table_col = st.columns((1, 1.4), gap="large")
with plot_col, st.container(border=True, key="rp-card-products"):
    st.markdown("**Top 10 par chiffre d’affaires**")
    top = products.head(10).sort_values("revenue")
    fig = px.bar(top, x="revenue", y="product", orientation="h",
                 labels={"revenue": "Chiffre d’affaires", "product": "Produit"})
    st.plotly_chart(fig, width="stretch", alt="Dix produits aux chiffres d’affaires les plus élevés")
with table_col:
    display = products.rename(columns={
        "reference": "Référence", "product": "Produit", "revenue": "Chiffre d’affaires",
        "quantity": "Unités", "orders": "Commandes", "customers": "Clients",
    })
    st.dataframe(display, hide_index=True, width="stretch", height=430,
                 alt="Classement des produits et indicateurs de vente")
    download_button(display, "Exporter le classement CSV", "performance_produits.csv", "products_csv")

st.subheader("Explorer un produit")
products["choice"] = products["reference"].astype(str) + " · " + products["product"].astype(str)
chosen = st.selectbox("Produit à explorer", products["choice"].tolist(), key="product_drilldown")
selected_product = products.loc[products["choice"] == chosen].iloc[0]
detail_params = {**params, "stock_code": selected_product["reference"]}
detail_where = where + " AND s.stock_code = :stock_code"
detail = read(
    f"""SELECT s.sale_date AS date, s.invoice AS commande,
               s.customer_id AS client, s.country AS pays,
               s.sales_quantity AS quantite, s.sales_revenue AS chiffre_affaires
        FROM gold.sales s
        WHERE s.transaction_type = 'sale' AND {detail_where}
        ORDER BY s.sale_date DESC LIMIT 10000""", detail_params
)
st.caption(f"Détail filtré pour {chosen} · période {date_label(start, end)} · export limité à 10 000 lignes.")
if not empty_state(detail):
    st.dataframe(detail, hide_index=True, width="stretch", height=300,
                 alt="Transactions pour le produit sélectionné")
    download_button(detail, "Exporter les transactions CSV", "transactions_produit.csv", "product_detail_csv")
