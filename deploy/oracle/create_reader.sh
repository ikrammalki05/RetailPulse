#!/bin/sh
set -eu

: "${DASHBOARD_DB_PASSWORD:?DASHBOARD_DB_PASSWORD must be configured}"

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=ON_ERROR_STOP=1 <<'SQL'
\getenv reader_password DASHBOARD_DB_PASSWORD
CREATE ROLE retailpulse_reader LOGIN PASSWORD :'reader_password';
SQL
