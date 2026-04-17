-- Create one logical database per stateful service.
-- Runs once on first container start; container has no persistent volume
-- so every `docker compose up` produces a deterministic fresh state.

CREATE DATABASE inventorydb;
CREATE DATABASE orderdb;
CREATE DATABASE paymentdb;
CREATE DATABASE userdb;
CREATE DATABASE chatdb;

-- `app` role already exists (created by POSTGRES_USER env var).
-- Grant full access to each service DB.
GRANT ALL PRIVILEGES ON DATABASE inventorydb TO app;
GRANT ALL PRIVILEGES ON DATABASE orderdb     TO app;
GRANT ALL PRIVILEGES ON DATABASE paymentdb   TO app;
GRANT ALL PRIVILEGES ON DATABASE userdb      TO app;
GRANT ALL PRIVILEGES ON DATABASE chatdb      TO app;
