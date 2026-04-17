-- paymentdb: payments + transaction history for payment-service
\connect paymentdb;

CREATE TABLE IF NOT EXISTS payments (
    id               VARCHAR(32) PRIMARY KEY,
    order_id         VARCHAR(32) NOT NULL,
    amount_cents     INTEGER NOT NULL,
    currency         VARCHAR(8) NOT NULL DEFAULT 'USD',
    status           VARCHAR(16) NOT NULL DEFAULT 'pending',
    provider         VARCHAR(32) NOT NULL DEFAULT 'stripe',
    fraud_score      NUMERIC(4,3),
    processor_version VARCHAR(8) NOT NULL DEFAULT 'v1',
    user_plan        VARCHAR(32),
    created_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at     TIMESTAMP
);

CREATE TABLE IF NOT EXISTS refunds (
    id               VARCHAR(32) PRIMARY KEY,
    payment_id       VARCHAR(32) NOT NULL REFERENCES payments(id),
    amount_cents     INTEGER NOT NULL,
    status           VARCHAR(16) NOT NULL DEFAULT 'completed',
    created_at       TIMESTAMP NOT NULL DEFAULT NOW()
);

-- The v3 processor has this index; v1/v2 simulate not having it via a
-- query pattern that hits a function of created_at.
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at DESC);

-- Seed historical payments for demo data + `/balance` queries
INSERT INTO payments (id, order_id, amount_cents, currency, status, provider, fraud_score, processor_version, user_plan, created_at, completed_at) VALUES
    ('txn_seed00000001', 'ord_seed00000001', 12998, 'USD', 'completed', 'stripe', 0.021, 'v1', 'gold',     NOW() - INTERVAL '3 days',    NOW() - INTERVAL '3 days'),
    ('txn_seed00000002', 'ord_seed00000002',  2999, 'USD', 'completed', 'stripe', 0.044, 'v1', 'free',     NOW() - INTERVAL '2 days',    NOW() - INTERVAL '2 days'),
    ('txn_seed00000003', 'ord_seed00000003', 17998, 'USD', 'completed', 'stripe', 0.012, 'v1', 'platinum', NOW() - INTERVAL '1 days',    NOW() - INTERVAL '1 days'),
    ('txn_seed00000004', 'ord_seed00000004',  4999, 'USD', 'completed', 'stripe', 0.033, 'v1', 'silver',   NOW() - INTERVAL '12 hours',  NOW() - INTERVAL '12 hours'),
    ('txn_seed00000005', 'ord_seed00000005',  9998, 'USD', 'completed', 'stripe', 0.028, 'v1', 'diamond',  NOW() - INTERVAL '2 hours',   NOW() - INTERVAL '2 hours')
ON CONFLICT (id) DO NOTHING;
