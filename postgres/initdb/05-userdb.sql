-- userdb: user profiles + preferences for user-service
\connect userdb;

CREATE TABLE IF NOT EXISTS users (
    key          VARCHAR(64) PRIMARY KEY,
    name         VARCHAR(255),
    email        VARCHAR(255) UNIQUE,
    plan         VARCHAR(32),
    role         VARCHAR(32),
    metro        VARCHAR(64),
    country      VARCHAR(8),
    created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login   TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_key         VARCHAR(64) PRIMARY KEY REFERENCES users(key) ON DELETE CASCADE,
    theme            VARCHAR(16) NOT NULL DEFAULT 'dark',
    email_notify     BOOLEAN NOT NULL DEFAULT TRUE,
    push_notify      BOOLEAN NOT NULL DEFAULT TRUE,
    sms_notify       BOOLEAN NOT NULL DEFAULT FALSE,
    language         VARCHAR(16) NOT NULL DEFAULT 'en',
    timezone         VARCHAR(64) NOT NULL DEFAULT 'America/New_York',
    updated_at       TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_plan ON users(plan);

-- A small starter population so GET /users/<id> returns something on a
-- cold start. Users from the simulator are upserted into this table as
-- they show up in X-User-* headers.
INSERT INTO users (key, name, email, plan, role, metro, country, last_login) VALUES
    ('usr-seed-alice', 'Alice Example',   'alice@launchdarkly.demo',      'gold',     'admin',  'San Francisco', 'US', NOW() - INTERVAL '1 day'),
    ('usr-seed-bob',   'Bob Example',     'bob@darklylaunch.com',          'free',     'reader', 'New York',      'US', NOW() - INTERVAL '2 days'),
    ('usr-seed-carol', 'Carol Example',   'carol@toggleflagly.com',        'platinum', 'writer', 'Boston',        'US', NOW() - INTERVAL '3 hours'),
    ('usr-seed-dave',  'Dave Example',    'dave@lunchdarkly.net',          'silver',   'reader', 'Chicago',       'US', NOW() - INTERVAL '5 hours'),
    ('usr-seed-eve',   'Eve Example',     'eve@launchbrightly.io',         'diamond',  'admin',  'Los Angeles',   'US', NOW() - INTERVAL '30 minutes')
ON CONFLICT (key) DO NOTHING;

INSERT INTO user_preferences (user_key) VALUES
    ('usr-seed-alice'), ('usr-seed-bob'), ('usr-seed-carol'),
    ('usr-seed-dave'), ('usr-seed-eve')
ON CONFLICT (user_key) DO NOTHING;
