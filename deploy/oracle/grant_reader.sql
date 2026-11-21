GRANT CONNECT ON DATABASE retailpulse TO retailpulse_reader;
GRANT USAGE ON SCHEMA gold TO retailpulse_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO retailpulse_reader;

-- Restored objects are owned by retailpulse_admin, so future Gold tables
-- created by that role will be readable by the dashboard account.
ALTER DEFAULT PRIVILEGES FOR ROLE retailpulse_admin IN SCHEMA gold
    GRANT SELECT ON TABLES TO retailpulse_reader;
