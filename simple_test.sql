-- Simple permission system setup
-- Create system_roles table
CREATE TABLE IF NOT EXISTS system_roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    level INTEGER NOT NULL DEFAULT 0,
    color VARCHAR(7) DEFAULT '#6b7280',
    is_system_role BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert default roles
INSERT INTO system_roles (name, display_name, description, level, color, is_system_role) VALUES
('super_admin', 'Super Administrator', 'Full system access with all permissions', 100, '#dc2626', true),
('admin', 'Administrator', 'System administration with user and content management', 90, '#ea580c', true),
('moderator', 'Moderator', 'Content moderation and user management within jurisdiction', 70, '#ca8a04', true),
('representative', 'Representative', 'Elected or appointed official with jurisdiction-specific powers', 60, '#16a34a', true),
('verified_citizen', 'Verified Citizen', 'Verified user with enhanced posting and interaction privileges', 30, '#2563eb', true),
('citizen', 'Citizen', 'Regular user with basic posting and interaction rights', 20, '#7c3aed', true),
('guest', 'Guest', 'Unregistered user with read-only access', 10, '#6b7280', true)
ON CONFLICT (name) DO NOTHING;
