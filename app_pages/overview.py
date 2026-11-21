"""Executive overview page."""

from datetime import timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard_data import (date_label, download_button, empty_state, filters,
                            money, read, shared_filters)

st.title("Executive Overview", icon=":material/dashboard:")
st.caption("Les indicateurs se mettent à jour avec les filtres partagés à gauche.")
selection = shared_filters()
if selection is None:
    st.stop()
start, end, selected_countries, _bounds = selection
where, params = filters("s", start, end, selected_countries)

current = read(
    f"""SELECT COUNT(*) AS lines,
               COUNT(DISTINCT s.invoice) AS orders,
               COUNT(DISTINCT s.customer_id) AS customers,
               COALESCE(SUM(s.sales_quantity), 0) AS units,
               COALESCE(SUM(s.sales_revenue), 0) AS revenue
        FROM gold.sales s
        WHERE s.transaction_type = 'sale' AND {where}""", params
).iloc[0]

period_days = (end - start).days + 1
previous_end = start - timedelta(days=1)
previous_start = previous_end - timedelta(days=period_days - 1)
previous_where, previous_params = filters(
    "s", previous_start, previous_end, selected_countries
)
previous = read(
    f"""SELECT COUNT(DISTINCT s.invoice) AS orders,
               COUNT(DISTINCT s.customer_id) AS customers,
               COALESCE(SUM(s.sales_quantity), 0) AS units,
               COALESCE(SUM(s.sales_revenue), 0) AS revenue
        FROM gold.sales s
        WHERE s.transaction_type = 'sale' AND {previous_where}""",
    previous_params,
).iloc[0]

def delta_pct(now, before):
    if not before:
        return None
    return (float(now) - float(before)) / float(before) * 100

avg_order = float(current.revenue) / int(current.orders) if current.orders else 0
previous_avg = float(previous.revenue) / int(previous.orders) if previous.orders else 0
with st.container(horizontal=True, gap="medium", key="rp-kpi-strip"):
    with st.container(border=True, key="rp-kpi-revenue"):
        st.metric("Chiffre d’affaires", money(current.revenue),
                  delta_pct(current.revenue, previous.revenue),
                  delta_description=f"vs. {date_label(previous_start, previous_end)}")
    with st.container(border=True, key="rp-kpi-orders"):
        st.metric("Commandes", f"{int(current.orders):,}".replace(",", " "),
                  delta_pct(current.orders, previous.orders),
                  delta_description="vs. période précédente")
    with st.container(border=True, key="rp-kpi-customers"):
        st.metric("Clients identifiés", f"{int(current.customers):,}".replace(",", " "),
                  delta_pct(current.customers, previous.customers),
                  delta_description="vs. période précédente")
    with st.container(border=True, key="rp-kpi-units"):
        st.metric("Unités vendues", f"{int(current.units):,}".replace(",", " "),
                  delta_pct(current.units, previous.units),
                  delta_description="vs. période précédente")
    with st.container(border=True, key="rp-kpi-aov"):
        st.metric("Panier moyen", money(avg_order), delta_pct(avg_order, previous_avg),
                  delta_description="vs. période précédente")

monthly = read(
    f"""SELECT DATE_TRUNC('month', s.sale_date)::date AS month,
               SUM(s.sales_revenue) AS revenue,
               COUNT(DISTINCT s.invoice) AS orders
        FROM gold.sales s
        WHERE s.transaction_type = 'sale' AND {where}
        GROUP BY 1 ORDER BY 1""", params
)
country_data = read(
    f"""SELECT COALESCE(s.country, 'Non renseigné') AS country,
               SUM(s.sales_revenue) AS revenue,
               COUNT(DISTINCT s.invoice) AS orders
        FROM gold.sales s
        WHERE s.transaction_type = 'sale' AND {where}
        GROUP BY 1 ORDER BY revenue DESC LIMIT 10""", params
)
products = read(
    f"""SELECT s.stock_code AS reference,
               COALESCE(NULLIF(BTRIM(s.description), ''), 'Produit inconnu') AS product,
               SUM(s.sales_revenue) AS revenue,
               SUM(s.sales_quantity) AS quantity,
               COUNT(DISTINCT s.invoice) AS orders
        FROM gold.sales s
        WHERE s.transaction_type = 'sale' AND {where}
          AND s.stock_code NOT IN ('POST', 'DOT', 'M')
        GROUP BY 1, 2 HAVING COUNT(DISTINCT s.invoice) >= 10
        ORDER BY revenue DESC LIMIT 1""", params
)

st.subheader("Vue commerciale")
trend_col, country_col = st.columns((1.5, 1), gap="large")
with trend_col, st.container(border=True, key="rp-card-overview-trend"):
    st.markdown("**Chiffre d’affaires mensuel**")
    if not empty_state(monthly):
        fig = px.line(monthly, x="month", y="revenue", markers=True,
                      labels={"month": "Mois", "revenue": "Chiffre d’affaires"})
        fig.update_layout(margin=dict(l=8, r=8, t=12, b=8), hovermode="x unified")
        st.plotly_chart(fig, width="stretch", alt="Évolution mensuelle du chiffre d’affaires")
with country_col, st.container(border=True, key="rp-card-overview-country"):
    st.markdown("**Pays en tête**")
    if not empty_state(country_data):
        country_view = country_data.sort_values("revenue")
        fig = px.bar(country_view, x="revenue", y="country", orientation="h",
                     labels={"revenue": "Chiffre d’affaires", "country": "Pays"})
        fig.update_layout(margin=dict(l=4, r=4, t=12, b=8))
        st.plotly_chart(fig, width="stretch", alt="Top des pays par chiffre d’affaires")

insights = []
if not monthly.empty:
    best_month = monthly.loc[monthly.revenue.idxmax()]
    insights.append(f"**Meilleur mois :** {pd.Timestamp(best_month.month):%B %Y}, avec {money(best_month.revenue)} de chiffre d’affaires.")
if not country_data.empty and current.revenue:
    leader = country_data.iloc[0]
    share = float(leader.revenue) / float(current.revenue) * 100
    insights.append(f"**Pays principal :** {leader.country} représente {share:.1f} % du chiffre d’affaires sélectionné.")
if not products.empty:
    item = products.iloc[0]
    insights.append(f"**Produit en tête :** {item.product}, {money(item.revenue)} sur {int(item.orders):,} commandes.")
if previous.revenue and current.revenue:
    change = delta_pct(current.revenue, previous.revenue)
    insights.append(f"**Évolution :** le chiffre d’affaires est {'en hausse' if change >= 0 else 'en baisse'} de {abs(change):.1f} % par rapport à la période précédente.")

if insights:
    st.subheader("Signaux métier")
    with st.container(border=True):
        for insight in insights:
            st.markdown(f"- {insight}")

st.caption(f"Période : {date_label(start, end)} · ventes valides uniquement.")
download_button(monthly, "Exporter la tendance CSV", "tendance_mensuelle.csv", "overview_csv")
