-- Migration: Add token blacklist table for JWT token revocation
-- This table stores hashed tokens that have been revoked before their natural expiration

CREATE TABLE IF NOT EXISTS token_blacklist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash VARCHAR(64) UNIQUE NOT NULL, -- SHA-256 hash of the token
    expires_at INTEGER NOT NULL, -- Unix timestamp when the token expires
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_token_blacklist_hash ON token_blacklist (token_hash);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires ON token_blacklist (expires_at);

-- Clean up expired tokens automatically
CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS void AS $$
BEGIN
    DELETE FROM token_blacklist WHERE expires_at < extract(epoch from now());
END;
$$ LANGUAGE plpgsql;

-- Schedule cleanup to run periodically (if using pg_cron extension)
-- SELECT cron.schedule('cleanup-expired-tokens', '0 0 * * *', 'SELECT cleanup_expired_tokens()');

-- For manual cleanup, you can run:
-- SELECT cleanup_expired_tokens();
