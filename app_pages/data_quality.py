"""Completeness and business-rule checks for the selected Gold data."""

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard_data import date_label, download_button, empty_state, filters, read, shared_filters

st.title("Data Quality & Monitoring", icon=":material/verified:")
st.caption("Contrôles de complétude et de cohérence sur gold.sales.")
selection = shared_filters()
if selection is None:
    st.stop()
start, end, selected_countries, bounds = selection
# Keep undated rows visible to the quality checks; all other rows follow the shared range.
where, params = filters("s", start, end, selected_countries, include_missing_dates=True)

quality = read(
    f"""SELECT COUNT(*) AS lignes,
               COUNT(*) FILTER (WHERE s.sale_date IS NULL) AS date_manquante,
               COUNT(*) FILTER (WHERE s.stock_code IS NULL OR BTRIM(s.stock_code) = '') AS reference_manquante,
               COUNT(*) FILTER (WHERE s.customer_id IS NULL) AS client_manquant,
               COUNT(*) FILTER (WHERE s.country IS NULL OR BTRIM(s.country) = '') AS pays_manquant,
               COUNT(*) FILTER (WHERE s.description IS NULL OR BTRIM(s.description) = '') AS description_manquante,
               COUNT(*) FILTER (WHERE s.price IS NULL OR s.price <= 0) AS prix_invalide,
               COUNT(*) FILTER (WHERE s.transaction_type = 'sale'
                                  AND (s.quantity <= 0 OR s.price <= 0 OR s.sale_date IS NULL
                                       OR s.stock_code IS NULL OR BTRIM(s.stock_code) = '')) AS vente_incoherente,
               COUNT(*) FILTER (WHERE s.transaction_type = 'invalid') AS lignes_invalides
        FROM gold.sales s WHERE {where}""", params
).iloc[0]

types = read(
    f"""SELECT s.transaction_type AS type, COUNT(*) AS lignes,
               SUM(s.quantity) AS quantite_signee,
               SUM(s.line_amount) AS montant_signe
        FROM gold.sales s WHERE {where}
        GROUP BY s.transaction_type ORDER BY lignes DESC""", params
)

st.caption(
    f"Période : {date_label(start, end)} · période couverte par la source : "
    f"{bounds[0]:%d/%m/%Y} – {bounds[1]:%d/%m/%Y}. "
    "Les lignes sans date sont incluses dans les contrôles de complétude."
)
with st.container(horizontal=True, gap="medium"):
    with st.container(border=True, key="rp-kpi-quality-rows"):
        st.metric("Lignes contrôlées", f"{int(quality.lignes):,}".replace(",", " "))
    with st.container(border=True, key="rp-kpi-quality-dates"):
        st.metric("Dates manquantes", f"{int(quality.date_manquante):,}".replace(",", " "))
    with st.container(border=True, key="rp-kpi-quality-products"):
        st.metric("Références manquantes", f"{int(quality.reference_manquante):,}".replace(",", " "))
    with st.container(border=True, key="rp-kpi-quality-sales"):
        st.metric("Ventes incohérentes", f"{int(quality.vente_incoherente):,}".replace(",", " "))

checks = [
    {"Contrôle": "Date manquante", "Lignes": int(quality.date_manquante)},
    {"Contrôle": "Référence absente", "Lignes": int(quality.reference_manquante)},
    {"Contrôle": "Client non identifié", "Lignes": int(quality.client_manquant)},
    {"Contrôle": "Pays absent", "Lignes": int(quality.pays_manquant)},
    {"Contrôle": "Description absente", "Lignes": int(quality.description_manquante)},
    {"Contrôle": "Prix nul ou négatif", "Lignes": int(quality.prix_invalide)},
    {"Contrôle": "Ventes incohérentes", "Lignes": int(quality.vente_incoherente)},
    {"Contrôle": "Lignes classées invalides", "Lignes": int(quality.lignes_invalides)},
]
checks_frame = pd.DataFrame(checks).sort_values("Lignes", ascending=False)
checks_frame["Part des lignes (%)"] = (
    100 * checks_frame["Lignes"] / max(int(quality.lignes), 1)
).round(2)

st.subheader("Résultats des contrôles")
chart_col, table_col = st.columns((1, 1.3), gap="large")
with chart_col, st.container(border=True, key="rp-card-quality"):
    st.markdown("**Lignes concernées par contrôle**")
    nonzero = checks_frame.loc[checks_frame["Lignes"] > 0]
    if not empty_state(nonzero, "Aucune anomalie détectée par ces contrôles."):
        fig = px.bar(nonzero.sort_values("Lignes"), x="Lignes", y="Contrôle",
                     orientation="h")
        st.plotly_chart(fig, width="stretch", alt="Comptage des contrôles de qualité en échec")
with table_col:
    st.dataframe(checks_frame, hide_index=True, width="stretch",
                 alt="Résultats des contrôles de qualité")
    download_button(checks_frame, "Exporter les contrôles CSV", "controles_qualite.csv", "quality_checks_csv")

st.subheader("Répartition des transactions")
if not empty_state(types):
    st.dataframe(types, hide_index=True, width="stretch", alt="Types de transactions dans la sélection")
    download_button(types, "Exporter la répartition CSV", "types_transactions.csv", "quality_types_csv")

st.subheader("Historique ETL")
st.caption("Exécutions enregistrées dans gold.etl_load_log, indépendamment des filtres commerciaux.")
etl = read(
    """SELECT load_id, pipeline_name, source_name, target_table, rows_loaded,
              status, started_at, completed_at, error_message
       FROM gold.etl_load_log
       ORDER BY started_at DESC
       LIMIT 50"""
)
if empty_state(etl, "Aucune exécution ETL n’est journalisée dans gold.etl_load_log."):
    st.stop()

latest = etl.iloc[0]
successful = int((etl["status"].astype(str).str.upper() == "SUCCESS").sum())
success_rate = 100 * successful / len(etl)
last_status = str(latest["status"])
with st.container(horizontal=True, gap="medium"):
    with st.container(border=True):
        st.metric("Dernier statut", last_status)
        st.badge(
            "Opérationnel" if last_status.upper() == "SUCCESS" else "À vérifier",
            color="green" if last_status.upper() == "SUCCESS" else "orange",
            icon=":material/check_circle:" if last_status.upper() == "SUCCESS" else ":material/warning:",
        )
    with st.container(border=True):
        st.metric("Taux de réussite", f"{success_rate:.1f} %",
                  delta_description="sur les 50 dernières entrées maximum")
    with st.container(border=True):
        st.metric("Dernière exécution", str(latest["started_at"]))

etl_col, log_col = st.columns((1, 1.5), gap="large")
with etl_col, st.container(border=True):
    st.markdown("**Statuts observés**")
    status_counts = etl.groupby("status", dropna=False).size().rename("exécutions").reset_index()
    fig = px.pie(status_counts, names="status", values="exécutions", hole=0.58)
    st.plotly_chart(fig, width="stretch", alt="Répartition des statuts consignés dans le journal ETL")
with log_col:
    st.markdown("**Dernières entrées du journal**")
    etl_display = etl.rename(columns={
        "load_id": "ID", "pipeline_name": "Pipeline", "source_name": "Source",
        "target_table": "Table cible", "rows_loaded": "Lignes chargées",
        "status": "Statut", "started_at": "Début", "completed_at": "Fin",
        "error_message": "Erreur",
    })
    st.dataframe(etl_display, hide_index=True, width="stretch", height=380,
                 alt="Historique récent des chargements ETL")
    download_button(etl_display, "Exporter l’historique CSV", "historique_etl.csv", "etl_history_csv")
