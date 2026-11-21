"""Returns and cancellations analysis, separate from gross sales."""

import plotly.express as px
import streamlit as st

from dashboard_data import date_label, download_button, empty_state, filters, money, read, shared_filters

st.title("Returns & Cancellations", icon=":material/assignment_return:")
st.caption("Retours et annulations sont suivis séparément et ne sont pas déduits du CA des ventes.")
selection = shared_filters()
if selection is None:
    st.stop()
start, end, selected_countries, _bounds = selection
where, params = filters("s", start, end, selected_countries)
return_filter = "s.transaction_type IN ('return', 'cancellation')"

summary = read(
    f"""SELECT s.transaction_type AS type,
               COUNT(*) AS lignes,
               COUNT(DISTINCT s.invoice) AS factures,
               COUNT(DISTINCT s.customer_id) AS clients,
               SUM(s.quantity) AS quantite_signee,
               SUM(s.line_amount) AS montant_signe
        FROM gold.sales s
        WHERE {return_filter} AND {where}
        GROUP BY 1 ORDER BY lignes DESC""", params
)
if empty_state(summary, "Aucun retour ou aucune annulation dans cette sélection."):
    st.stop()

total_lines = int(summary["lignes"].sum())
total_amount = float(summary["montant_signe"].sum())
with st.container(horizontal=True, gap="medium"):
    with st.container(border=True, key="rp-kpi-return-lines"):
        st.metric("Lignes de retour / annulation", f"{total_lines:,}".replace(",", " "))
    with st.container(border=True, key="rp-kpi-return-invoices"):
        st.metric("Factures concernées", f"{int(summary.factures.sum()):,}".replace(",", " "))
    with st.container(border=True, key="rp-kpi-return-value"):
        st.metric("Montant signé", money(total_amount))

chart_col, table_col = st.columns((1, 1.3), gap="large")
with chart_col, st.container(border=True, key="rp-card-returns"):
    st.markdown("**Lignes par type**")
    fig = px.bar(summary, x="type", y="lignes", color="type",
                 labels={"type": "Type", "lignes": "Lignes"})
    st.plotly_chart(fig, width="stretch", alt="Nombre de lignes de retour et annulation")
with table_col:
    st.markdown("**Synthèse**")
    st.dataframe(summary, hide_index=True, width="stretch", alt="Synthèse des retours et annulations")
    download_button(summary, "Exporter la synthèse CSV", "retours_annulations.csv", "returns_summary_csv")

details = read(
    f"""SELECT s.sale_date AS date, s.transaction_type AS type,
               s.invoice AS facture, s.customer_id AS client, s.country AS pays,
               s.stock_code AS reference, s.description AS produit,
               s.quantity AS quantite_signee, s.line_amount AS montant_signe
        FROM gold.sales s
        WHERE {return_filter} AND {where}
        ORDER BY s.sale_date DESC LIMIT 100000""", params
)
st.subheader("Détail des transactions")
st.caption(f"Période : {date_label(start, end)} · export plafonné à 100 000 lignes.")
st.dataframe(details, hide_index=True, width="stretch", height=380,
             alt="Transactions de retour et annulation")
download_button(details, "Exporter le détail CSV", "detail_retours.csv", "returns_detail_csv")
