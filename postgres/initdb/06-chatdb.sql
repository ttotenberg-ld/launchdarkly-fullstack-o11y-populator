-- chatdb: conversation history for chat-service
\connect chatdb;

CREATE TABLE IF NOT EXISTS conversations (
    id            VARCHAR(40) PRIMARY KEY,
    user_key      VARCHAR(64) NOT NULL,
    model         VARCHAR(64),
    started_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    last_msg_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id              BIGSERIAL PRIMARY KEY,
    conversation_id VARCHAR(40) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(16) NOT NULL,         -- system | user | assistant
    content         TEXT NOT NULL,
    generation_id   VARCHAR(40),                  -- FK-like link to LD AI tracker cache
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    duration_ms     INTEGER,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_feedback (
    id              BIGSERIAL PRIMARY KEY,
    generation_id   VARCHAR(40) NOT NULL,
    sentiment       VARCHAR(16) NOT NULL,          -- positive | negative
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_generation_id ON messages(generation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_key ON conversations(user_key);
