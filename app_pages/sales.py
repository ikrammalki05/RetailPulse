"""Sales analysis and period comparison."""

import plotly.express as px
import streamlit as st

from dashboard_data import date_label, download_button, empty_state, filters, read, shared_filters

st.title("Sales Analytics", icon=":material/monitoring:")
st.caption("Tendances, commandes et export des lignes de vente filtrées.")
selection = shared_filters()
if selection is None:
    st.stop()
start, end, selected_countries, _bounds = selection
where, params = filters("s", start, end, selected_countries)

monthly = read(
    f"""SELECT DATE_TRUNC('month', s.sale_date)::date AS month,
               COUNT(DISTINCT s.invoice) AS orders,
               COUNT(DISTINCT s.customer_id) AS customers,
               SUM(s.sales_quantity) AS units,
               SUM(s.sales_revenue) AS revenue
        FROM gold.sales s
        WHERE s.transaction_type = 'sale' AND {where}
        GROUP BY 1 ORDER BY 1""", params
)
st.subheader("Tendances mensuelles")
if not empty_state(monthly):
    rev_col, order_col = st.columns(2, gap="large")
    with rev_col, st.container(border=True, key="rp-card-sales-revenue"):
        st.markdown("**Chiffre d’affaires**")
        fig = px.line(monthly, x="month", y="revenue", markers=True,
                      labels={"month": "Mois", "revenue": "Chiffre d’affaires"})
        st.plotly_chart(fig, width="stretch", alt="Chiffre d’affaires mensuel")
    with order_col, st.container(border=True, key="rp-card-sales-orders"):
        st.markdown("**Commandes**")
        fig = px.bar(monthly, x="month", y="orders",
                     labels={"month": "Mois", "orders": "Commandes"})
        st.plotly_chart(fig, width="stretch", alt="Nombre de commandes par mois")
    download_button(monthly, "Exporter les ventes mensuelles CSV", "ventes_mensuelles.csv", "sales_monthly_csv")

st.subheader("Analyse géographique")
geography = read(
    f"""SELECT COALESCE(s.country, 'Non renseigné') AS pays,
               COUNT(DISTINCT s.invoice) AS commandes,
               COUNT(DISTINCT s.customer_id) AS clients,
               SUM(s.sales_quantity) AS unités,
               SUM(s.sales_revenue) AS chiffre_affaires
        FROM gold.sales s
        WHERE s.transaction_type = 'sale' AND {where}
        GROUP BY 1 ORDER BY chiffre_affaires DESC""", params
)
if not empty_state(geography):
    geo_chart, geo_table = st.columns((1, 1.3), gap="large")
    with geo_chart, st.container(border=True, key="rp-card-sales-geography"):
        st.markdown("**Chiffre d’affaires par pays**")
        top_countries = geography.head(12).sort_values("chiffre_affaires")
        fig = px.bar(top_countries, x="chiffre_affaires", y="pays", orientation="h",
                     labels={"chiffre_affaires": "Chiffre d’affaires", "pays": "Pays"})
        st.plotly_chart(fig, width="stretch", alt="Chiffre d’affaires des douze premiers pays")
    with geo_table:
        st.dataframe(geography, hide_index=True, width="stretch", height=380,
                     alt="Indicateurs de vente par pays")
        download_button(geography, "Exporter l’analyse géographique CSV", "ventes_par_pays.csv", "sales_geo_csv")

st.subheader("Détail des ventes")
details = read(
    f"""SELECT s.sale_date AS date, s.invoice AS commande,
               s.customer_id AS client, s.country AS pays,
               s.stock_code AS reference, s.description AS produit,
               s.sales_quantity AS quantite, s.sales_revenue AS chiffre_affaires
        FROM gold.sales s
        WHERE s.transaction_type = 'sale' AND {where}
        ORDER BY s.sale_date DESC, s.invoice
        LIMIT 100000""", params
)
st.caption(f"Période : {date_label(start, end)} · aperçu et export limités aux 100 000 premières lignes.")
if not empty_state(details):
    st.dataframe(details, hide_index=True, width="stretch", height=380,
                 alt="Lignes de vente selon les filtres")
    download_button(details, "Exporter les lignes CSV", "lignes_ventes.csv", "sales_detail_csv")
