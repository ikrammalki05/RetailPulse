-- À exécuter une seule fois par un administrateur PostgreSQL dans la base
-- RetailPulse. Remplacer le secret d'exemple avant d'exécuter la première ligne.
-- Ne pas réutiliser le mot de passe de postgres.

CREATE ROLE retailpulse_reader
    LOGIN
    PASSWORD 'REMPLACER_PAR_UN_SECRET_LONG_ET_UNIQUE';

GRANT CONNECT ON DATABASE "RetailPulse" TO retailpulse_reader;
GRANT USAGE ON SCHEMA gold TO retailpulse_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO retailpulse_reader;

-- Pour que les prochaines tables Gold créées par postgres restent lisibles.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA gold
    GRANT SELECT ON TABLES TO retailpulse_reader;
