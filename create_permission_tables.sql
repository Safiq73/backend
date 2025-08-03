-- Create api_permissions table
CREATE TABLE IF NOT EXISTS api_permissions (
    id SERIAL PRIMARY KEY,
    route_path VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    permission_name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(route_path, method)
);

-- Create user_roles table (junction table between users and system_roles)
CREATE TABLE IF NOT EXISTS user_roles (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES system_roles(id) ON DELETE CASCADE,
    assigned_by UUID REFERENCES users(id),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, role_id)
);

-- Create role_api_permissions table (junction table between roles and api permissions)
CREATE TABLE IF NOT EXISTS role_api_permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES system_roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES api_permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role_id, permission_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role_id ON user_roles(role_id);
CREATE INDEX IF NOT EXISTS idx_role_api_permissions_role_id ON role_api_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_role_api_permissions_permission_id ON role_api_permissions(permission_id);
CREATE INDEX IF NOT EXISTS idx_api_permissions_permission_name ON api_permissions(permission_name);
CREATE INDEX IF NOT EXISTS idx_api_permissions_route_method ON api_permissions(route_path, method);
