-- Migration: Add eVote feature tables
-- Created: 2025-08-18
-- Description: Adds representative eVote functionality with daily count tracking

-- Main eVotes table (current active votes)
CREATE TABLE representative_evotes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    representative_id UUID NOT NULL REFERENCES representatives(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Ensure one vote per user per representative
    CONSTRAINT unique_user_representative_evote UNIQUE (user_id, representative_id)
);

-- Historical daily counts table (only when transactions occur)
CREATE TABLE representative_evote_daily_counts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    representative_id UUID NOT NULL REFERENCES representatives(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_evotes INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Ensure one record per representative per day
    CONSTRAINT unique_representative_date UNIQUE (representative_id, date)
);

-- Indexes for performance
CREATE INDEX idx_representative_evotes_user_id ON representative_evotes (user_id);
CREATE INDEX idx_representative_evotes_representative_id ON representative_evotes (representative_id);
CREATE INDEX idx_representative_evotes_created_at ON representative_evotes (created_at);

CREATE INDEX idx_representative_evote_daily_counts_representative_id ON representative_evote_daily_counts (representative_id);
CREATE INDEX idx_representative_evote_daily_counts_date ON representative_evote_daily_counts (date);
CREATE INDEX idx_representative_evote_daily_counts_rep_date ON representative_evote_daily_counts (representative_id, date);

-- Add eVote count to representatives table for quick access
ALTER TABLE representatives ADD COLUMN evote_count INTEGER DEFAULT 0;
CREATE INDEX idx_representatives_evote_count ON representatives (evote_count DESC);

-- Trigger to update representatives.evote_count when evotes change
CREATE OR REPLACE FUNCTION update_representative_evote_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE representatives 
        SET evote_count = evote_count + 1 
        WHERE id = NEW.representative_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE representatives 
        SET evote_count = evote_count - 1 
        WHERE id = OLD.representative_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_representative_evote_count
    AFTER INSERT OR DELETE ON representative_evotes
    FOR EACH ROW
    EXECUTE FUNCTION update_representative_evote_count();

-- Initialize evote_count for existing representatives
UPDATE representatives 
SET evote_count = COALESCE((
    SELECT COUNT(*) 
    FROM representative_evotes 
    WHERE representative_id = representatives.id
), 0);
