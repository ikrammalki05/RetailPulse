"""Point d'entrée de RetailPulse Business Analytics."""

import streamlit as st

st.set_page_config(
    page_title="RetailPulse | Business Analytics",
    page_icon=":material/monitoring:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.logo(
    "assets/retailpulse_logo.svg",
    size="large",
    icon_image="assets/retailpulse_icon.svg",
)

# CSS is scoped to containers with explicit keys so the card treatment stays
# stable across Streamlit updates and does not depend on internal DOM selectors.
st.html(
    """
    <style>
      .st-key-rp-kpi-revenue, .st-key-rp-kpi-orders,
      .st-key-rp-kpi-customers, .st-key-rp-kpi-units,
      .st-key-rp-kpi-aov, .st-key-rp-card-overview-trend,
      .st-key-rp-card-overview-country, .st-key-rp-card-sales-revenue,
      .st-key-rp-card-sales-orders, .st-key-rp-card-sales-geography,
      .st-key-rp-card-products, .st-key-rp-card-customers, .st-key-rp-card-returns,
      .st-key-rp-card-quality, .st-key-rp-kpi-return-lines,
      .st-key-rp-kpi-return-invoices, .st-key-rp-kpi-return-value,
      .st-key-rp-kpi-quality-rows, .st-key-rp-kpi-quality-dates,
      .st-key-rp-kpi-quality-products, .st-key-rp-kpi-quality-sales {
        border-radius: 16px;
        border-color: #EAECF0;
        box-shadow: 0 5px 18px rgba(16, 24, 40, 0.055);
      }
      .st-key-rp-kpi-revenue, .st-key-rp-kpi-orders,
      .st-key-rp-kpi-customers, .st-key-rp-kpi-units,
      .st-key-rp-kpi-aov { background: #FFFFFF; }
    </style>
    """
)

pages = st.navigation(
    {
        "Vue d’ensemble": [
            st.Page("app_pages/overview.py", title="Executive Overview",
                    icon=":material/dashboard:", default=True,
                    help="Synthèse des ventes, comparaison de période et principaux signaux métier."),
        ],
        "Analyse métier": [
            st.Page("app_pages/sales.py", title="Sales Analytics", icon=":material/monitoring:",
                    help="Tendances, commandes, pays et détail des ventes exportable en CSV."),
            st.Page("app_pages/products.py", title="Product Analytics", icon=":material/inventory_2:",
                    help="Classement des produits, volumes, revenus et commandes sur la période filtrée."),
            st.Page("app_pages/customers.py", title="Customer Analytics", icon=":material/groups:",
                    help="Segments RFM et détail des clients selon récence, fréquence et montant."),
            st.Page("app_pages/returns.py", title="Returns & Cancellations", icon=":material/assignment_return:",
                    help="Suivi des retours et annulations, séparés du chiffre d’affaires des ventes."),
        ],
        "Suivi des données": [
            st.Page("app_pages/data_quality.py", title="Data Quality & Monitoring",
                    icon=":material/verified:",
                    help="Contrôles de complétude et de cohérence sur les lignes Gold filtrées."),
        ],
    },
    position="sidebar",
)

pages.run()
