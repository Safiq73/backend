-- Migration: Add follows table for user follow/unfollow functionality
-- Created: 2025-07-30

-- Create follows table
CREATE TABLE follows (
    follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    followed_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mutual BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Primary key is the combination of follower_id and followed_id
    PRIMARY KEY (follower_id, followed_id),
    
    -- Prevent self-following
    CONSTRAINT no_self_follow CHECK (follower_id != followed_id)
);

-- Create indexes for performance
CREATE INDEX idx_follows_follower_id ON follows (follower_id);
CREATE INDEX idx_follows_followed_id ON follows (followed_id);
CREATE INDEX idx_follows_mutual ON follows (mutual);
CREATE INDEX idx_follows_created_at ON follows (created_at DESC);

-- Create compound indexes for common queries
CREATE INDEX idx_follows_follower_mutual ON follows (follower_id, mutual);
CREATE INDEX idx_follows_followed_mutual ON follows (followed_id, mutual);

-- Create function to update mutual status
CREATE OR REPLACE FUNCTION update_mutual_status()
RETURNS TRIGGER AS $$
BEGIN
    -- If this is an INSERT operation
    IF TG_OP = 'INSERT' THEN
        -- Check if the reverse relationship exists and update mutual status
        IF EXISTS (
            SELECT 1 FROM follows 
            WHERE follower_id = NEW.followed_id AND followed_id = NEW.follower_id
        ) THEN
            -- Update both relationships to mutual = true
            UPDATE follows 
            SET mutual = TRUE 
            WHERE (follower_id = NEW.follower_id AND followed_id = NEW.followed_id)
               OR (follower_id = NEW.followed_id AND followed_id = NEW.follower_id);
        END IF;
        RETURN NEW;
    END IF;
    
    -- If this is a DELETE operation
    IF TG_OP = 'DELETE' THEN
        -- Update the reverse relationship to mutual = false if it exists
        UPDATE follows 
        SET mutual = FALSE 
        WHERE follower_id = OLD.followed_id AND followed_id = OLD.follower_id;
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update mutual status
CREATE TRIGGER follows_mutual_trigger
    AFTER INSERT OR DELETE ON follows
    FOR EACH ROW
    EXECUTE FUNCTION update_mutual_status();

-- Add follow count columns to users table for performance
ALTER TABLE users ADD COLUMN IF NOT EXISTS followers_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS following_count INTEGER DEFAULT 0;

-- Create function to update user follow counts
CREATE OR REPLACE FUNCTION update_user_follow_counts()
RETURNS TRIGGER AS $$
BEGIN
    -- If this is an INSERT operation
    IF TG_OP = 'INSERT' THEN
        -- Increment following count for follower
        UPDATE users 
        SET following_count = following_count + 1 
        WHERE id = NEW.follower_id;
        
        -- Increment followers count for followed user
        UPDATE users 
        SET followers_count = followers_count + 1 
        WHERE id = NEW.followed_id;
        
        RETURN NEW;
    END IF;
    
    -- If this is a DELETE operation
    IF TG_OP = 'DELETE' THEN
        -- Decrement following count for follower
        UPDATE users 
        SET following_count = GREATEST(following_count - 1, 0)
        WHERE id = OLD.follower_id;
        
        -- Decrement followers count for followed user
        UPDATE users 
        SET followers_count = GREATEST(followers_count - 1, 0)
        WHERE id = OLD.followed_id;
        
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update user follow counts
CREATE TRIGGER follows_count_trigger
    AFTER INSERT OR DELETE ON follows
    FOR EACH ROW
    EXECUTE FUNCTION update_user_follow_counts();

-- Initialize existing user follow counts (if any users exist)
UPDATE users SET 
    followers_count = (
        SELECT COUNT(*) 
        FROM follows 
        WHERE followed_id = users.id
    ),
    following_count = (
        SELECT COUNT(*) 
        FROM follows 
        WHERE follower_id = users.id
    );
