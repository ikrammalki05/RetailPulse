"""Configuration serveur et accès PostgreSQL en lecture seule."""

from datetime import date
import math
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text

load_dotenv()


def setting(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value:
        return value
    try:
        return str(st.secrets.get(name, default))
    except (FileNotFoundError, RuntimeError):
        return default


@st.cache_resource(show_spinner=False)
def get_engine():
    """Secrets stay on the server; users never enter database credentials."""
    database_url = setting("DATABASE_URL")
    if database_url:
        return create_engine(database_url, pool_pre_ping=True, pool_recycle=1800)

    host = setting("DB_HOST", "localhost")
    port = int(setting("DB_PORT", "5432"))
    database = setting("DB_NAME", "RetailPulse")
    user = setting("DB_USER", "retailpulse_reader")
    password = setting("DB_PASSWORD")
    if not password:
        raise RuntimeError(
            "La connexion PostgreSQL n’est pas configurée sur le serveur. "
            "Définissez DB_PASSWORD dans .env (local) ou dans les secrets "
            "de la plateforme de déploiement."
        )
    return create_engine(
        URL.create("postgresql+psycopg", username=user, password=password,
                   host=host, port=port, database=database),
        pool_pre_ping=True,
        pool_recycle=1800,
    )


def cache_namespace() -> str:
    """Partition cached query results by database, without storing passwords."""
    return "|".join((setting("DB_HOST", "localhost"),
                    setting("DB_PORT", "5432"),
                    setting("DB_NAME", "RetailPulse"),
                    setting("DB_USER", "retailpulse_reader")))


@st.cache_data(ttl=300, max_entries=128, show_spinner=False)
def query_frame(_engine, namespace: str, sql: str, params: dict) -> pd.DataFrame:
    """Run a parameterized SELECT in a PostgreSQL read-only transaction."""
    del namespace  # Used as a cache key to avoid cross-database cache reuse.
    with _engine.connect() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        return pd.read_sql(text(sql), connection, params=params)


def read(sql: str, params: dict | None = None) -> pd.DataFrame:
    return query_frame(get_engine(), cache_namespace(), sql, params or {})


def date_bounds() -> tuple[date, date]:
    bounds = read(
        """SELECT MIN(sale_date)::date AS first_day,
                         MAX(sale_date)::date AS last_day
                  FROM gold.sales WHERE transaction_type = 'sale'"""
    )
    if bounds.empty or pd.isna(bounds.loc[0, "first_day"]):
        raise ValueError("Aucune vente valide n’est disponible dans gold.sales.")
    return (pd.Timestamp(bounds.loc[0, "first_day"]).date(),
            pd.Timestamp(bounds.loc[0, "last_day"]).date())


def countries() -> list[str]:
    values = read(
        """SELECT DISTINCT country FROM gold.sales
           WHERE country IS NOT NULL ORDER BY country"""
    )
    return values["country"].tolist()


def filters(alias: str, start: date, end: date,
            selected_countries: list[str],
            include_missing_dates: bool = False) -> tuple[str, dict]:
    """Build safe named binds for the shared date and country filters."""
    if include_missing_dates:
        conditions = [f"({alias}.sale_date IS NULL OR "
                      f"({alias}.sale_date >= :start_date AND "
                      f"{alias}.sale_date <= :end_date))"]
    else:
        conditions = [f"{alias}.sale_date >= :start_date",
                      f"{alias}.sale_date <= :end_date"]
    params: dict = {"start_date": start, "end_date": end}
    if selected_countries:
        names = []
        for index, country in enumerate(selected_countries):
            name = f"country_{index}"
            names.append(f":{name}")
            params[name] = country
        conditions.append(f"{alias}.country IN ({', '.join(names)})")
    return " AND ".join(conditions), params


def shared_filters() -> tuple[date, date, list[str], tuple[date, date]] | None:
    """Render the global sidebar filters and return their current values."""
    try:
        first, last = date_bounds()
        country_options = countries()
    except Exception as exc:
        st.error(f"Connexion PostgreSQL indisponible : {exc}", icon=":material/error:")
        st.caption("Configurez les secrets du serveur ; aucun identifiant n’est demandé aux visiteurs.")
        return None

    with st.sidebar:
        st.markdown("### Filtres globaux")
        selected_dates = st.date_input(
            "Période", value=(first, last), min_value=first, max_value=last,
            key="global_date_range",
        )
        selected_countries = st.multiselect(
            "Pays", country_options, default=country_options,
            key="global_countries",
            help="Une sélection vide affiche tous les pays.",
        )

    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        start, end = selected_dates
    elif isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 1:
        start = end = selected_dates[0]
    else:
        start = end = selected_dates
    # Keep the date range valid while a user is selecting its first endpoint.
    start = start or first
    end = end or last
    return start, end, selected_countries, (first, last)


def date_label(start: date, end: date) -> str:
    return f"{start:%d/%m/%Y} – {end:%d/%m/%Y}"


def csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")


def download_button(frame: pd.DataFrame, label: str, filename: str, key: str) -> None:
    st.download_button(
        label, data=csv_bytes(frame), file_name=filename,
        mime="text/csv", key=key, icon=":material/download:",
    )


def empty_state(frame: pd.DataFrame, message: str = "Aucun résultat pour ces filtres.") -> bool:
    if frame.empty:
        st.info(message)
        return True
    return False


def rfm_segments(customers: pd.DataFrame, end: date) -> pd.DataFrame:
    """Compute transparent 1-5 quintile RFM scores and business segments."""
    if customers.empty:
        return customers.assign(segment=pd.Series(dtype="string"))
    result = customers.copy()
    result["last_order_date"] = pd.to_datetime(result["last_order_date"])
    result["recency_days"] = (
        pd.Timestamp(end) - result["last_order_date"]
    ).dt.days

    def score(values: pd.Series, higher_is_better: bool) -> pd.Series:
        ranks = values.rank(method="first", ascending=higher_is_better)
        return (5 * ranks / len(values)).apply(math.ceil).clip(1, 5).astype(int)

    result["R"] = score(result["recency_days"], False)
    result["F"] = score(result["frequency"], True)
    result["M"] = score(result["monetary"], True)
    result["rfm_score"] = result[["R", "F", "M"]].astype(str).agg("".join, axis=1)

    def segment(row) -> str:
        r, f, m = row["R"], row["F"], row["M"]
        if r >= 4 and f >= 4 and m >= 4:
            return "Meilleurs clients"
        if r >= 3 and f >= 3:
            return "Clients fidèles"
        if r >= 4 and f <= 2:
            return "Nouveaux clients"
        if r <= 2 and f >= 3:
            return "À réactiver"
        if r <= 2 and f <= 2:
            return "Clients à risque"
        return "Clients réguliers"

    result["segment"] = result.apply(segment, axis=1)
    return result


def money(value) -> str:
    return f"{float(value):,.2f}".replace(",", " ")
