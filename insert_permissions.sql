-- Insert API permissions based on actual routes
INSERT INTO api_permissions (route_path, method, permission_name, description, category) VALUES
-- Authentication & User Management
('/api/v1/auth/register', 'POST', 'auth.register.post', 'Register new user', 'auth'),
('/api/v1/auth/login', 'POST', 'auth.login.post', 'User login', 'auth'),
('/api/v1/auth/refresh', 'POST', 'auth.refresh.post', 'Refresh access token', 'auth'),
('/api/v1/auth/logout', 'POST', 'auth.logout.post', 'User logout', 'auth'),

-- User Profile Management
('/api/v1/users/me', 'GET', 'users.me.get', 'Get current user profile', 'users'),
('/api/v1/users/me', 'PUT', 'users.me.put', 'Update current user profile', 'users'),
('/api/v1/users/{user_id}', 'GET', 'users.detail.get', 'Get user profile by ID', 'users'),
('/api/v1/users', 'GET', 'users.get', 'List users (admin)', 'users'),
('/api/v1/users/{user_id}', 'DELETE', 'users.detail.delete', 'Delete user (admin)', 'users'),

-- Posts Management
('/api/v1/posts', 'GET', 'posts.get', 'List posts', 'posts'),
('/api/v1/posts', 'POST', 'posts.post', 'Create new post', 'posts'),
('/api/v1/posts/{post_id}', 'GET', 'posts.detail.get', 'Get post details', 'posts'),
('/api/v1/posts/{post_id}', 'PUT', 'posts.detail.put', 'Update post', 'posts'),
('/api/v1/posts/{post_id}', 'DELETE', 'posts.detail.delete', 'Delete post', 'posts'),
('/api/v1/posts/search', 'GET', 'posts.search.get', 'Search posts', 'posts'),

-- Comments Management
('/api/v1/posts/{post_id}/comments', 'GET', 'posts.detail.comments.get', 'List post comments', 'comments'),
('/api/v1/posts/{post_id}/comments', 'POST', 'posts.detail.comments.post', 'Create comment', 'comments'),
('/api/v1/comments/{comment_id}', 'PUT', 'comments.detail.put', 'Update comment', 'comments'),
('/api/v1/comments/{comment_id}', 'DELETE', 'comments.detail.delete', 'Delete comment', 'comments'),

-- Voting System
('/api/v1/posts/{post_id}/vote', 'POST', 'posts.detail.vote.post', 'Vote on post', 'votes'),
('/api/v1/comments/{comment_id}/vote', 'POST', 'comments.detail.vote.post', 'Vote on comment', 'votes'),
('/api/v1/posts/{post_id}/vote', 'DELETE', 'posts.detail.vote.delete', 'Remove vote on post', 'votes'),
('/api/v1/comments/{comment_id}/vote', 'DELETE', 'comments.detail.vote.delete', 'Remove vote on comment', 'votes'),

-- Follow System
('/api/v1/users/{user_id}/follow', 'POST', 'users.detail.follow.post', 'Follow user', 'follow'),
('/api/v1/users/{user_id}/follow', 'DELETE', 'users.detail.follow.delete', 'Unfollow user', 'follow'),
('/api/v1/users/me/followers', 'GET', 'users.me.followers.get', 'Get my followers', 'follow'),
('/api/v1/users/me/following', 'GET', 'users.me.following.get', 'Get users I follow', 'follow'),

-- Content Management
('/api/v1/analytics', 'GET', 'analytics.get', 'View analytics dashboard', 'analytics'),
('/api/v1/moderation/reports', 'GET', 'moderation.reports.get', 'View content reports', 'moderation'),
('/api/v1/moderation/reports', 'POST', 'moderation.reports.post', 'Report content', 'moderation'),

-- Permission Management (Admin only)
('/api/v1/permissions/roles', 'GET', 'permissions.roles.get', 'List all roles', 'permissions'),
('/api/v1/permissions/roles', 'POST', 'permissions.roles.post', 'Create new role', 'permissions'),
('/api/v1/permissions/roles/{role_id}', 'PUT', 'permissions.roles.detail.put', 'Update role', 'permissions'),
('/api/v1/permissions/roles/{role_id}', 'DELETE', 'permissions.roles.detail.delete', 'Delete role', 'permissions'),
('/api/v1/permissions/users/{user_id}/roles', 'GET', 'permissions.users.detail.roles.get', 'Get user roles', 'permissions'),
('/api/v1/permissions/users/{user_id}/roles', 'POST', 'permissions.users.detail.roles.post', 'Assign role to user', 'permissions'),
('/api/v1/permissions/users/{user_id}/roles/{role_id}', 'DELETE', 'permissions.users.detail.roles.detail.delete', 'Remove role from user', 'permissions')
ON CONFLICT (permission_name) DO NOTHING;
