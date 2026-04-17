-- inventorydb: products + stock table for inventory-service (also read by search-service)
\connect inventorydb;

CREATE TABLE IF NOT EXISTS products (
    id           VARCHAR(32) PRIMARY KEY,
    name         VARCHAR(255) NOT NULL,
    price_cents  INTEGER NOT NULL,
    category     VARCHAR(64) NOT NULL,
    description  TEXT,
    tags         TEXT[],
    created_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inventory (
    product_id   VARCHAR(32) PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    stock        INTEGER NOT NULL DEFAULT 0,
    reserved     INTEGER NOT NULL DEFAULT 0,
    -- seed_stock is the "restock to" baseline read by the retention reaper.
    -- When stock drifts to 0 from sustained simulator reservations, the reaper
    -- resets stock back to this value so the demo never permanently runs out.
    seed_stock   INTEGER NOT NULL DEFAULT 0,
    updated_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reservations (
    id              VARCHAR(32) PRIMARY KEY,
    order_id        VARCHAR(32) NOT NULL,
    product_id      VARCHAR(32) NOT NULL REFERENCES products(id),
    quantity        INTEGER NOT NULL,
    status          VARCHAR(16) NOT NULL DEFAULT 'reserved',
    expires_at      TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reservations_order_id ON reservations(order_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
-- Deliberately NO index on products.name — demos a sequential scan when
-- search does LIKE queries against it.

-- Seed data. Matches the in-memory PRODUCTS dict from the previous
-- inventory-service implementation so prod_001..prod_008 stay stable.
INSERT INTO products (id, name, price_cents, category, description, tags) VALUES
    ('prod_001', 'Feature Flag Starter Kit',    2999,  'kits',      'Everything a new team needs to launch feature flags.',       ARRAY['starter','beginner','flags']),
    ('prod_002', 'Progressive Rollout Pro',     4999,  'tools',     'Percentage rollouts with automated guardrails.',             ARRAY['rollout','progressive','release']),
    ('prod_003', 'A/B Testing Suite',           7999,  'suites',    'Run experiments with statistical rigor.',                    ARRAY['testing','ab','experiment']),
    ('prod_004', 'Targeting Rules Package',     3999,  'packages',  'Segment-driven flag targeting.',                             ARRAY['targeting','rules','segments']),
    ('prod_005', 'Segment Builder',             5999,  'tools',     'Visual segment construction.',                               ARRAY['segments','builder','targeting']),
    ('prod_006', 'Experimentation Platform',    9999,  'platforms', 'Full experimentation stack.',                                ARRAY['experiment','platform','analytics']),
    ('prod_007', 'SDK Integration Kit',         1999,  'kits',      'Drop-in SDK examples for common stacks.',                    ARRAY['sdk','integration','developer']),
    ('prod_008', 'Release Automation',          14999, 'platforms', 'Automate the full release lifecycle.',                       ARRAY['release','automation','cicd'])
ON CONFLICT (id) DO NOTHING;

INSERT INTO inventory (product_id, stock, seed_stock) VALUES
    ('prod_001', 150, 150),
    ('prod_002',  75,  75),
    ('prod_003',  45,  45),
    ('prod_004', 200, 200),
    ('prod_005', 100, 100),
    ('prod_006',  30,  30),
    ('prod_007', 500, 500),
    ('prod_008',  25,  25)
ON CONFLICT (product_id) DO NOTHING;
