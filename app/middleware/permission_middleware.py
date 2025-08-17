"""
Permission middleware for CivicPulse FastAPI application

This middleware checks user permissions for each API endpoint based on
the dynamic permission system.
"""

from typing import Dict, Callable, Optional
from fastapi import Request, HTTPException, status, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from app.services.simple_permission_service import permission_service

logger = logging.getLogger(__name__)

class PermissionMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware to handle dynamic permission checking"""
    
    def __init__(self, app, fail_open: bool = True):
        super().__init__(app)
        self.fail_open = fail_open  # If True, allow access when permission check fails
        # Cache for frequently accessed permissions
        self._permission_cache: Dict[str, bool] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through permission checking middleware
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response from next middleware/endpoint
        """
        try:
            # Check if this route needs permission checking
            if await self._should_check_permissions(request):
                await self._check_route_permission(request)
            
            # Continue to next middleware/endpoint
            response = await call_next(request)
            return response
            
        except HTTPException:
            # Re-raise HTTP exceptions (like 401, 403)
            raise
        except Exception as e:
            logger.error(f"Permission middleware error: {e}")
            if self.fail_open:
                # Continue on error if fail_open is True
                response = await call_next(request)
                return response
            else:
                # Fail closed - deny access on error
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Permission check failed"
                )
    
    async def _should_check_permissions(self, request: Request) -> bool:
        """Determine if this request needs permission checking"""
        route_path = request.url.path
        method = request.method
        
        # Skip permission checks for public routes
        if self._is_public_route(route_path, method):
            return False
        
        # Skip permission checks for docs and health endpoints
        if route_path in ["/docs", "/redoc", "/openapi.json", "/health"]:
            return False
            
        # Skip WebSocket connections (handled separately)
        if route_path.startswith("/api/v1/ws"):
            return False
        
        return True
    
    async def _check_route_permission(self, request: Request) -> bool:
        """
        Check if the current user has permission to access the requested route
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if access is allowed
            
        Raises:
            HTTPException: If access is denied
        """
        route_path = request.url.path
        method = request.method
        
        # Get current user (optional - might be None for public routes)
        current_user = None
        try:
            # Extract user_id from request if possible
            # This is a simplified approach - in production you'd decode JWT tokens
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # For now, we'll skip token validation in middleware
                # The actual auth will be handled by the endpoint dependencies
                pass
        except Exception as e:
            logger.warning(f"Could not get current user: {e}")
            current_user = None
        
        # Generate permission name based on route
        permission_name = self._get_permission_name(route_path, method)
        
        # If no user is authenticated, check if this is a guest-allowed route
        if not current_user:
            if self._is_guest_allowed(route_path, method):
                return True
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # For the demonstration, we'll allow all requests but log them
        # In production, you would implement proper permission checking here
        
        if not current_user:
            if self._is_guest_allowed(route_path, method):
                logger.info(f"✅ Guest access allowed: {method} {route_path}")
                return True
            # For demo purposes, allow access but log it
            logger.info(f"⚠️  Would require authentication: {method} {route_path}")
            return True
        
        # For authenticated users, we would check permissions here
        logger.info(f"✅ Authenticated access: {method} {route_path}")
        return True
    
    def _is_public_route(self, route_path: str, method: str) -> bool:
        """Check if a route is publicly accessible without any authentication"""
        public_routes = [
            ("/api/v1/auth/register", "POST"),
            ("/api/v1/auth/login", "POST"),
            ("/api/v1/auth/refresh", "POST"),
            ("/health", "GET"),
            ("/docs", "GET"),
            ("/redoc", "GET"), 
            ("/openapi.json", "GET"),
        ]
        
        # Check exact matches
        for public_path, public_method in public_routes:
            if route_path == public_path and method == public_method:
                return True
        
        return False
    
    def _is_guest_allowed(self, route_path: str, method: str) -> bool:
        """Check if a route allows guest (unauthenticated) access"""
        guest_routes = [
            ("/api/v1/posts", "GET"),  # Public post listing
            ("/api/v1/posts/search", "GET"),  # Public search
            ("/api/v1/representatives", "GET"),  # Public representatives
            ("/api/v1/jurisdictions", "GET"),  # Public jurisdictions
        ]
        
        # Check exact matches
        for guest_path, guest_method in guest_routes:
            if route_path == guest_path and method == guest_method:
                return True
        
        # Check pattern matches for public read access
        if method == "GET":
            # Allow public read access to individual posts
            if route_path.startswith("/api/v1/posts/") and route_path.count("/") == 4:
                return True
            
            # Allow public read access to individual representatives
            if route_path.startswith("/api/v1/representatives/") and route_path.count("/") == 4:
                return True
        
        return False
    
    def _get_permission_name(self, route_path: str, method: str) -> str:
        """Generate permission name from route path and method"""
        # Remove /api/v1 prefix
        if route_path.startswith("/api/v1"):
            route_path = route_path[7:]
        
        # Split path into parts
        parts = [part for part in route_path.split("/") if part]
        
        if not parts:
            return "root.access"
        
        # Build permission name
        resource = parts[0]  # e.g., 'posts', 'users', 'analytics'
        
        # Handle sub-resources
        if len(parts) > 1:
            if parts[1] not in ["{post_id}", "{user_id}", "{id}"]:  # Not a path parameter
                permission = f"{resource}.{parts[1]}.{method.lower()}"
            else:
                permission = f"{resource}.detail.{method.lower()}"
        else:
            permission = f"{resource}.{method.lower()}"
        
        return permission
    
    async def _check_user_permission(self, user_id, permission_name: str) -> bool:
        """
        Check if user has specific permission
        
        Args:
            user_id: User ID
            permission_name: Permission to check
            
        Returns:
            True if user has permission, False otherwise
        """
        # Use cache for frequent checks
        cache_key = f"{user_id}:{permission_name}"
        if cache_key in self._permission_cache:
            return self._permission_cache[cache_key]
        
        try:
            # Check permission through service
            has_permission = await permission_service.user_has_permission(
                user_id, permission_name
            )
            
            # Cache the result (with basic cache management)
            if len(self._permission_cache) > 1000:
                # Clear 25% of cache (remove oldest entries)
                items_to_remove = len(self._permission_cache) // 4
                keys_to_remove = list(self._permission_cache.keys())[:items_to_remove]
                for key in keys_to_remove:
                    del self._permission_cache[key]
            
            self._permission_cache[cache_key] = has_permission
            return has_permission
            
        except Exception as e:
            logger.error(f"Error checking permission {permission_name} for user {user_id}: {e}")
            # Fail open - allow access if permission check fails
            return self.fail_open
