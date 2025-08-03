# Core permission system constants and utilities
"""
Dynamic Permission System for CivicPulse

This module provides a dynamic permission system where permissions are based on 
actual API route names rather than static permission strings. This ensures:
1. Permissions automatically align with actual endpoints
2. No orphaned permissions for non-existent routes
3. Easier maintenance as routes change
4. Clear mapping between what users can access and actual API endpoints
"""

from enum import Enum
from typing import Dict, List, Set
from dataclasses import dataclass

# HTTP Methods that can be permitted
class PermissionMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    ALL = "*"  # Special case for all methods

@dataclass
class APIPermission:
    """Represents a permission for a specific API endpoint"""
    route_path: str  # e.g., "/api/v1/posts"
    method: PermissionMethod  # HTTP method
    description: str  # Human-readable description
    category: str  # Group permissions by feature area
    
    @property
    def permission_name(self) -> str:
        """Generate the permission name from route and method"""
        # Convert route path to permission name
        # /api/v1/posts -> posts
        # /api/v1/posts/{post_id} -> posts.detail
        # /api/v1/posts/{post_id}/comments -> posts.comments
        
        path_parts = [part for part in self.route_path.split("/") if part and not part.startswith("api")]
        
        # Handle version prefixes
        if path_parts and path_parts[0].startswith("v"):
            path_parts = path_parts[1:]
        
        # Convert path parameters to descriptive names
        processed_parts = []
        for part in path_parts:
            if part.startswith("{") and part.endswith("}"):
                # Convert {post_id} to "detail", {user_id} to "detail", etc.
                if "id" in part:
                    processed_parts.append("detail")
                else:
                    processed_parts.append(part.strip("{}"))
            else:
                processed_parts.append(part)
        
        permission_base = ".".join(processed_parts)
        
        if self.method == PermissionMethod.ALL:
            return permission_base
        else:
            return f"{permission_base}.{self.method.value.lower()}"

# Core API Permissions Registry
# This should be populated based on actual FastAPI routes
API_PERMISSIONS_REGISTRY: List[APIPermission] = [
    # Authentication & User Management
    APIPermission("/api/v1/auth/register", PermissionMethod.POST, "Register new user", "auth"),
    APIPermission("/api/v1/auth/login", PermissionMethod.POST, "User login", "auth"),
    APIPermission("/api/v1/auth/refresh", PermissionMethod.POST, "Refresh access token", "auth"),
    APIPermission("/api/v1/auth/logout", PermissionMethod.POST, "User logout", "auth"),
    
    # User Profile Management
    APIPermission("/api/v1/users/me", PermissionMethod.GET, "Get current user profile", "users"),
    APIPermission("/api/v1/users/me", PermissionMethod.PUT, "Update current user profile", "users"),
    APIPermission("/api/v1/users/{user_id}", PermissionMethod.GET, "Get user profile by ID", "users"),
    APIPermission("/api/v1/users", PermissionMethod.GET, "List users (admin)", "users"),
    APIPermission("/api/v1/users/{user_id}", PermissionMethod.DELETE, "Delete user (admin)", "users"),
    
    # Posts Management
    APIPermission("/api/v1/posts", PermissionMethod.GET, "List posts", "posts"),
    APIPermission("/api/v1/posts", PermissionMethod.POST, "Create new post", "posts"),
    APIPermission("/api/v1/posts/{post_id}", PermissionMethod.GET, "Get post details", "posts"),
    APIPermission("/api/v1/posts/{post_id}", PermissionMethod.PUT, "Update post", "posts"),
    APIPermission("/api/v1/posts/{post_id}", PermissionMethod.DELETE, "Delete post", "posts"),
    APIPermission("/api/v1/posts/search", PermissionMethod.GET, "Search posts", "posts"),
    
    # Comments Management
    APIPermission("/api/v1/posts/{post_id}/comments", PermissionMethod.GET, "List post comments", "comments"),
    APIPermission("/api/v1/posts/{post_id}/comments", PermissionMethod.POST, "Create comment", "comments"),
    APIPermission("/api/v1/comments/{comment_id}", PermissionMethod.PUT, "Update comment", "comments"),
    APIPermission("/api/v1/comments/{comment_id}", PermissionMethod.DELETE, "Delete comment", "comments"),
    
    # Voting System
    APIPermission("/api/v1/posts/{post_id}/vote", PermissionMethod.POST, "Vote on post", "voting"),
    APIPermission("/api/v1/posts/{post_id}/vote", PermissionMethod.DELETE, "Remove vote from post", "voting"),
    APIPermission("/api/v1/comments/{comment_id}/vote", PermissionMethod.POST, "Vote on comment", "voting"),
    APIPermission("/api/v1/comments/{comment_id}/vote", PermissionMethod.DELETE, "Remove vote from comment", "voting"),
    
    # Follow System
    APIPermission("/api/v1/follows", PermissionMethod.GET, "List user follows", "follows"),
    APIPermission("/api/v1/follows", PermissionMethod.POST, "Follow user/topic", "follows"),
    APIPermission("/api/v1/follows/{follow_id}", PermissionMethod.DELETE, "Unfollow", "follows"),
    APIPermission("/api/v1/users/{user_id}/followers", PermissionMethod.GET, "Get user followers", "follows"),
    APIPermission("/api/v1/users/{user_id}/following", PermissionMethod.GET, "Get user following", "follows"),
    
    # Notifications
    APIPermission("/api/v1/notifications", PermissionMethod.GET, "List notifications", "notifications"),
    APIPermission("/api/v1/notifications/{notification_id}", PermissionMethod.PUT, "Mark notification as read", "notifications"),
    APIPermission("/api/v1/notifications/mark-all-read", PermissionMethod.POST, "Mark all notifications as read", "notifications"),
    
    # Representatives & Government Data
    APIPermission("/api/v1/representatives", PermissionMethod.GET, "List representatives", "representatives"),
    APIPermission("/api/v1/representatives/{rep_id}", PermissionMethod.GET, "Get representative details", "representatives"),
    APIPermission("/api/v1/representatives", PermissionMethod.POST, "Create representative (admin)", "representatives"),
    APIPermission("/api/v1/representatives/{rep_id}", PermissionMethod.PUT, "Update representative (admin)", "representatives"),
    APIPermission("/api/v1/representatives/{rep_id}", PermissionMethod.DELETE, "Delete representative (admin)", "representatives"),
    
    # Jurisdictions
    APIPermission("/api/v1/jurisdictions", PermissionMethod.GET, "List jurisdictions", "jurisdictions"),
    APIPermission("/api/v1/jurisdictions/{jurisdiction_id}", PermissionMethod.GET, "Get jurisdiction details", "jurisdictions"),
    
    # File Uploads
    APIPermission("/api/v1/upload", PermissionMethod.POST, "Upload files", "files"),
    APIPermission("/api/v1/upload/avatar", PermissionMethod.POST, "Upload avatar", "files"),
    
    # Analytics (Admin/Moderator)
    APIPermission("/api/v1/analytics/posts", PermissionMethod.GET, "Post analytics", "analytics"),
    APIPermission("/api/v1/analytics/users", PermissionMethod.GET, "User analytics", "analytics"),
    APIPermission("/api/v1/analytics/engagement", PermissionMethod.GET, "Engagement analytics", "analytics"),
    
    # Admin Management
    APIPermission("/api/v1/admin/users", PermissionMethod.GET, "Admin user management", "admin"),
    APIPermission("/api/v1/admin/posts/moderate", PermissionMethod.POST, "Moderate posts", "admin"),
    APIPermission("/api/v1/admin/comments/moderate", PermissionMethod.POST, "Moderate comments", "admin"),
    APIPermission("/api/v1/admin/system/status", PermissionMethod.GET, "System status", "admin"),
]

# Default Role Permissions
DEFAULT_ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "citizen": [
        # Basic user permissions
        "auth.post",  # Can login/logout
        "users.me.get", "users.me.put",  # Can view/edit own profile
        "users.detail.get",  # Can view other user profiles
        "posts.get", "posts.post", "posts.detail.get", "posts.search.get",  # Can view and create posts
        "posts.comments.get", "posts.comments.post",  # Can view and create comments
        "posts.detail.vote.post", "posts.detail.vote.delete",  # Can vote on posts
        "comments.detail.vote.post", "comments.detail.vote.delete",  # Can vote on comments
        "follows.get", "follows.post", "follows.detail.delete",  # Can follow/unfollow
        "users.detail.followers.get", "users.detail.following.get",  # Can view follow lists
        "notifications.get", "notifications.detail.put", "notifications.mark-all-read.post",  # Can manage notifications
        "representatives.get", "representatives.detail.get",  # Can view representatives
        "jurisdictions.get", "jurisdictions.detail.get",  # Can view jurisdictions
        "upload.post", "upload.avatar.post",  # Can upload files
    ],
    
    "verified_citizen": [
        # All citizen permissions plus additional verified features
        "*citizen",  # Inherit all citizen permissions
        "posts.detail.put",  # Can edit own posts
        "comments.detail.put",  # Can edit own comments
    ],
    
    "representative": [
        # All verified citizen permissions plus representative features
        "*verified_citizen",  # Inherit all verified citizen permissions
        "representatives.post", "representatives.detail.put",  # Can manage own representative profile
    ],
    
    "moderator": [
        # All representative permissions plus moderation
        "*representative",  # Inherit all representative permissions
        "admin.posts.moderate.post",  # Can moderate posts
        "admin.comments.moderate.post",  # Can moderate comments
        "analytics.posts.get", "analytics.engagement.get",  # Can view analytics
    ],
    
    "admin": [
        # Full system access
        "*",  # All permissions
    ]
}

def get_permission_name(route_path: str, method: str) -> str:
    """
    Generate permission name from route path and HTTP method
    
    Args:
        route_path: The API route path (e.g., "/api/v1/posts/{post_id}")
        method: The HTTP method (e.g., "GET", "POST")
    
    Returns:
        Permission name (e.g., "posts.detail.get")
    """
    # Find matching permission in registry
    for perm in API_PERMISSIONS_REGISTRY:
        if perm.route_path == route_path and perm.method.value == method:
            return perm.permission_name
    
    # If not found in registry, generate dynamically
    api_perm = APIPermission(route_path, PermissionMethod(method), "", "dynamic")
    return api_perm.permission_name

def get_permissions_by_category() -> Dict[str, List[APIPermission]]:
    """Group all permissions by category for easier management"""
    categories = {}
    for perm in API_PERMISSIONS_REGISTRY:
        if perm.category not in categories:
            categories[perm.category] = []
        categories[perm.category].append(perm)
    return categories

def expand_role_permissions(role_permissions: List[str]) -> Set[str]:
    """
    Expand role permissions including wildcards and inheritance
    
    Args:
        role_permissions: List of permission patterns for a role
    
    Returns:
        Set of all expanded permission names
    """
    expanded = set()
    
    for perm in role_permissions:
        if perm == "*":
            # All permissions
            expanded.update([p.permission_name for p in API_PERMISSIONS_REGISTRY])
        elif perm.startswith("*"):
            # Inherit from another role
            role_name = perm[1:]
            if role_name in DEFAULT_ROLE_PERMISSIONS:
                expanded.update(expand_role_permissions(DEFAULT_ROLE_PERMISSIONS[role_name]))
        elif "." in perm and perm.endswith("*"):
            # Category wildcard (e.g., "posts.*")
            prefix = perm[:-1]
            expanded.update([p.permission_name for p in API_PERMISSIONS_REGISTRY 
                           if p.permission_name.startswith(prefix)])
        else:
            # Direct permission
            expanded.add(perm)
    
    return expanded

def validate_permission_exists(permission_name: str) -> bool:
    """Check if a permission name corresponds to an actual API endpoint"""
    return any(p.permission_name == permission_name for p in API_PERMISSIONS_REGISTRY)
