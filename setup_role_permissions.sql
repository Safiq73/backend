-- Set up basic role-permission mappings for the citizen role
-- Citizens should be able to:
-- - View posts and comments
-- - Create posts and comments  
-- - Vote on posts and comments
-- - Update their own profile
-- - Follow/unfollow users

INSERT INTO role_api_permissions (role_id, permission_id)
SELECT sr.id, ap.id 
FROM system_roles sr, api_permissions ap 
WHERE sr.name = 'citizen' 
AND ap.permission_name IN (
    'posts.get',
    'posts.detail.get', 
    'posts.post',
    'posts.detail.comments.get',
    'posts.detail.comments.post',
    'posts.detail.vote.post',
    'posts.detail.vote.delete',
    'comments.detail.vote.post', 
    'comments.detail.vote.delete',
    'users.me.get',
    'users.me.put',
    'users.detail.get',
    'users.detail.follow.post',
    'users.detail.follow.delete',
    'users.me.followers.get',
    'users.me.following.get',
    'posts.search.get'
)
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Set up admin permissions (all permissions)
INSERT INTO role_api_permissions (role_id, permission_id)
SELECT sr.id, ap.id 
FROM system_roles sr, api_permissions ap 
WHERE sr.name = 'admin'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Set up super_admin permissions (all permissions)
INSERT INTO role_api_permissions (role_id, permission_id)
SELECT sr.id, ap.id 
FROM system_roles sr, api_permissions ap 
WHERE sr.name = 'super_admin'
ON CONFLICT (role_id, permission_id) DO NOTHING;
