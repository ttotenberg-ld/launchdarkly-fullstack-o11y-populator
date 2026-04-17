-- orderdb: orders + line items for order-service
\connect orderdb;

CREATE TABLE IF NOT EXISTS orders (
    id              VARCHAR(32) PRIMARY KEY,
    user_key        VARCHAR(64) NOT NULL,
    user_email      VARCHAR(255),
    user_plan       VARCHAR(32),
    layout_variant  VARCHAR(32) NOT NULL DEFAULT 'unknown',
    promo_variant   VARCHAR(32) NOT NULL DEFAULT 'unknown',
    total_cents     INTEGER NOT NULL,
    status          VARCHAR(16) NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id              BIGSERIAL PRIMARY KEY,
    order_id        VARCHAR(32) NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id      VARCHAR(32) NOT NULL,
    product_name    VARCHAR(255),
    quantity        INTEGER NOT NULL DEFAULT 1,
    price_cents     INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_user_key ON orders(user_key);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);

-- A small pool of historical orders so /orders returns something
-- immediately even before the simulator has run. Later orders are
-- inserted live during checkout.
INSERT INTO orders (id, user_key, user_email, user_plan, total_cents, status, created_at, completed_at) VALUES
    ('ord_seed00000001', 'usr-seed-alice',   'alice@launchdarkly.demo',    'gold',     12998, 'completed', NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'),
    ('ord_seed00000002', 'usr-seed-bob',     'bob@darklylaunch.com',        'free',      2999, 'completed', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days'),
    ('ord_seed00000003', 'usr-seed-carol',   'carol@toggleflagly.com',      'platinum', 17998, 'completed', NOW() - INTERVAL '1 days', NOW() - INTERVAL '1 days'),
    ('ord_seed00000004', 'usr-seed-dave',    'dave@lunchdarkly.net',        'silver',    4999, 'shipped',   NOW() - INTERVAL '12 hours', NULL),
    ('ord_seed00000005', 'usr-seed-eve',     'eve@launchbrightly.io',       'diamond',   9998, 'processing', NOW() - INTERVAL '2 hours', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO order_items (order_id, product_id, product_name, quantity, price_cents) VALUES
    ('ord_seed00000001', 'prod_001', 'Feature Flag Starter Kit', 1, 2999),
    ('ord_seed00000001', 'prod_006', 'Experimentation Platform',  1, 9999),
    ('ord_seed00000002', 'prod_001', 'Feature Flag Starter Kit',  1, 2999),
    ('ord_seed00000003', 'prod_008', 'Release Automation',        1, 14999),
    ('ord_seed00000003', 'prod_004', 'Targeting Rules Package',   1, 2999),
    ('ord_seed00000004', 'prod_002', 'Progressive Rollout Pro',   1, 4999),
    ('ord_seed00000005', 'prod_005', 'Segment Builder',           1, 5999),
    ('ord_seed00000005', 'prod_004', 'Targeting Rules Package',   1, 3999)
ON CONFLICT DO NOTHING;
