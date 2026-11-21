"""Customer loyalty and RFM segmentation."""

import plotly.express as px
import streamlit as st

from dashboard_data import (date_label, download_button, empty_state, filters,
                            read, rfm_segments, shared_filters)

st.title("Customer Analytics", icon=":material/groups:")
st.caption("Segmentation RFM calculée sur les ventes de la période sélectionnée.")
selection = shared_filters()
if selection is None:
    st.stop()
start, end, selected_countries, _bounds = selection
where, params = filters("s", start, end, selected_countries)

customers = read(
    f"""SELECT s.customer_id,
               MAX(s.sale_date)::date AS last_order_date,
               COUNT(DISTINCT s.invoice) AS frequency,
               SUM(s.sales_revenue) AS monetary
        FROM gold.sales s
        WHERE s.transaction_type = 'sale' AND s.customer_id IS NOT NULL
          AND {where}
        GROUP BY s.customer_id""", params
)
if empty_state(customers, "Aucun client identifié pour cette période."):
    st.stop()
rfm = rfm_segments(customers, end)
summary = (
    rfm.groupby("segment", as_index=False)
    .agg(clients=("customer_id", "count"),
         commandes=("frequency", "sum"),
         chiffre_affaires=("monetary", "sum"),
         panier_moyen_client=("monetary", "mean"))
    .sort_values("clients", ascending=False)
)
summary["part_clients_pct"] = (100 * summary["clients"] / summary["clients"].sum()).round(1)

st.subheader("Répartition des clients")
chart_col, table_col = st.columns((1, 1.4), gap="large")
with chart_col, st.container(border=True, key="rp-card-customers"):
    st.markdown("**Clients par segment**")
    fig = px.pie(summary, names="segment", values="clients", hole=0.58)
    st.plotly_chart(fig, width="stretch", alt="Part des clients par segment RFM")
with table_col:
    summary_display = summary.rename(columns={
        "segment": "Segment", "clients": "Clients", "commandes": "Commandes",
        "chiffre_affaires": "Chiffre d’affaires", "panier_moyen_client": "CA moyen/client",
        "part_clients_pct": "Part des clients (%)",
    })
    st.dataframe(summary_display, hide_index=True, width="stretch",
                 alt="Indicateurs par segment RFM")
    download_button(summary_display, "Exporter les segments CSV", "segments_rfm.csv", "rfm_summary_csv")

st.subheader("Explorer un segment")
segment_names = summary["segment"].tolist()
chosen_segment = st.selectbox("Segment client", segment_names, key="rfm_segment")
segment_clients = rfm.loc[rfm["segment"] == chosen_segment, [
    "customer_id", "recency_days", "frequency", "monetary", "rfm_score", "segment"
]].rename(columns={
    "customer_id": "Client", "recency_days": "Jours depuis le dernier achat",
    "frequency": "Commandes", "monetary": "Chiffre d’affaires",
    "rfm_score": "Score RFM", "segment": "Segment",
})
st.caption(f"Récence et fréquence évaluées du {start:%d/%m/%Y} au {end:%d/%m/%Y}.")
st.dataframe(segment_clients, hide_index=True, width="stretch", height=360,
             alt="Clients dans le segment sélectionné")
download_button(segment_clients, "Exporter les clients CSV", "clients_segment.csv", "rfm_customers_csv")
