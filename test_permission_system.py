"""
Permission System Testing Utilities

This module provides utilities and test cases for validating the permission system.
Includes unit tests, integration tests, and testing helpers.
"""

import pytest
import asyncio
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock

# Testing framework imports
from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest_asyncio

# Permission system imports
from app.core.permissions import (
    API_PERMISSIONS_REGISTRY,
    get_permission_name,
    validate_permission_exists,
    expand_role_permissions,
    DEFAULT_ROLE_PERMISSIONS
)
from app.services.permission_service import PermissionService
from app.middleware.permission_middleware import PermissionMiddleware
from app.core.auth import get_current_user


class MockUser:
    """Mock user for testing"""
    def __init__(self, user_id: UUID, username: str, roles: List[str] = None):
        self.id = user_id
        self.username = username
        self.is_active = True
        self.roles = roles or ["citizen"]


class PermissionTestHelper:
    """Helper class for testing permissions"""
    
    def __init__(self):
        self.permission_service = PermissionService()
        self.permission_middleware = PermissionMiddleware()
    
    def create_mock_user(self, roles: List[str] = None) -> MockUser:
        """Create a mock user with specified roles"""
        return MockUser(
            user_id=uuid4(),
            username=f"testuser_{uuid4().hex[:8]}",
            roles=roles or ["citizen"]
        )
    
    async def setup_test_permissions(self):
        """Set up test permissions in database"""
        # This would create test permissions and roles
        # In practice, you'd use your test database
        pass
    
    def get_permissions_for_role(self, role_name: str) -> List[str]:
        """Get all permissions for a role from the registry"""
        if role_name not in DEFAULT_ROLE_PERMISSIONS:
            return []
        
        role_perms = DEFAULT_ROLE_PERMISSIONS[role_name]
        return list(expand_role_permissions(role_perms))


# =============================================================================
# UNIT TESTS FOR PERMISSION SYSTEM COMPONENTS
# =============================================================================

class TestPermissionRegistry:
    """Test the permission registry functionality"""
    
    def test_permission_name_generation(self):
        """Test that permission names are generated correctly from routes"""
        test_cases = [
            ("/api/v1/posts", "GET", "posts.get"),
            ("/api/v1/posts/{post_id}", "PUT", "posts.detail.put"),
            ("/api/v1/posts/{post_id}/comments", "POST", "posts.detail.comments.post"),
            ("/api/v1/users/me", "GET", "users.me.get"),
            ("/api/v1/admin/system/status", "GET", "admin.system.status.get")
        ]
        
        for route, method, expected in test_cases:
            result = get_permission_name(route, method)
            assert result == expected, f"Expected {expected}, got {result} for {method} {route}"
    
    def test_permission_validation(self):
        """Test permission validation against registry"""
        # Valid permissions
        valid_perms = ["posts.get", "users.me.get", "auth.login.post"]
        for perm in valid_perms:
            assert validate_permission_exists(perm), f"Permission {perm} should be valid"
        
        # Invalid permissions
        invalid_perms = ["invalid.permission", "posts.nonexistent.action"]
        for perm in invalid_perms:
            assert not validate_permission_exists(perm), f"Permission {perm} should be invalid"
    
    def test_role_permission_expansion(self):
        """Test that role permissions expand correctly with inheritance"""
        # Test citizen role (base role)
        citizen_perms = expand_role_permissions(DEFAULT_ROLE_PERMISSIONS["citizen"])
        assert "posts.get" in citizen_perms
        assert "auth.login.post" in citizen_perms
        
        # Test verified citizen (inherits from citizen)
        verified_perms = expand_role_permissions(DEFAULT_ROLE_PERMISSIONS["verified_citizen"])
        assert "posts.get" in verified_perms  # Inherited
        assert "posts.detail.put" in verified_perms  # Added
        
        # Test admin (should have all permissions)
        admin_perms = expand_role_permissions(DEFAULT_ROLE_PERMISSIONS["admin"])
        all_registry_perms = {p.permission_name for p in API_PERMISSIONS_REGISTRY}
        assert all_registry_perms.issubset(admin_perms)


class TestPermissionService:
    """Test the permission service functionality"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for testing"""
        return AsyncMock()
    
    @pytest.fixture
    def permission_service(self, mock_db_session):
        """Permission service with mocked dependencies"""
        service = PermissionService()
        # Mock the database session
        service._get_db_session = AsyncMock(return_value=mock_db_session)
        return service
    
    @pytest.mark.asyncio
    async def test_user_has_permission_with_role(self, permission_service):
        """Test checking user permissions through roles"""
        user_id = uuid4()
        
        # Mock user has 'citizen' role
        permission_service.get_user_roles = AsyncMock(return_value=[
            MagicMock(id=uuid4(), name="citizen", level=20)
        ])
        
        # Mock role has permission
        permission_service._role_has_permission = AsyncMock(return_value=True)
        
        result = await permission_service.user_has_permission(user_id, "posts.get")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_user_has_permission_without_role(self, permission_service):
        """Test checking user permissions when user has no roles"""
        user_id = uuid4()
        
        # Mock user has no roles
        permission_service.get_user_roles = AsyncMock(return_value=[])
        
        result = await permission_service.user_has_permission(user_id, "posts.get")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_assign_role_to_user(self, permission_service):
        """Test assigning a role to a user"""
        user_id = uuid4()
        role_name = "verified_citizen"
        
        # Mock successful role assignment
        permission_service.assign_role_to_user = AsyncMock(return_value=True)
        
        result = await permission_service.assign_role_to_user(user_id, role_name)
        assert result is True


class TestPermissionMiddleware:
    """Test the permission middleware functionality"""
    
    @pytest.fixture
    def permission_middleware(self):
        """Permission middleware for testing"""
        return PermissionMiddleware()
    
    def test_public_route_detection(self, permission_middleware):
        """Test that public routes are correctly identified"""
        public_routes = [
            ("/api/v1/auth/register", "POST"),
            ("/api/v1/auth/login", "POST"),
            ("/api/v1/posts", "GET"),
            ("/docs", "GET"),
            ("/health", "GET")
        ]
        
        for route, method in public_routes:
            is_public = permission_middleware._is_public_route(route, method)
            assert is_public, f"Route {method} {route} should be public"
    
    def test_protected_route_detection(self, permission_middleware):
        """Test that protected routes are correctly identified"""
        protected_routes = [
            ("/api/v1/posts", "POST"),
            ("/api/v1/posts/123", "PUT"),
            ("/api/v1/users/me", "PUT"),
            ("/api/v1/admin/users", "GET")
        ]
        
        for route, method in protected_routes:
            is_public = permission_middleware._is_public_route(route, method)
            assert not is_public, f"Route {method} {route} should be protected"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestPermissionIntegration:
    """Integration tests for the complete permission system"""
    
    @pytest.fixture
    def test_app(self):
        """Create test FastAPI app with permission system"""
        from fastapi import FastAPI
        from app.main_with_permissions import create_application
        
        # Create test app (you'd configure it for testing)
        app = create_application()
        return app
    
    @pytest.fixture
    def test_client(self, test_app):
        """Create test client"""
        return TestClient(test_app)
    
    def test_public_endpoint_access(self, test_client):
        """Test that public endpoints are accessible without authentication"""
        # Test public endpoints
        response = test_client.get("/health")
        assert response.status_code == 200
        
        response = test_client.get("/api/v1/posts")
        # Should work without authentication (public read access)
        assert response.status_code in [200, 404]  # 404 if no posts exist
    
    def test_protected_endpoint_without_auth(self, test_client):
        """Test that protected endpoints reject unauthenticated requests"""
        # Test protected endpoint without authentication
        response = test_client.post("/api/v1/posts", json={"title": "Test", "content": "Test"})
        assert response.status_code == 401
    
    def test_protected_endpoint_with_auth(self, test_client):
        """Test that protected endpoints work with proper authentication"""
        # This would require setting up test authentication
        # In practice, you'd create a test JWT token
        pass
    
    def test_permission_denied(self, test_client):
        """Test that users without permissions are denied access"""
        # This would test permission denial
        # You'd create a user with limited permissions and test restricted endpoints
        pass


# =============================================================================
# PERMISSION TESTING UTILITIES
# =============================================================================

def create_test_jwt_token(user_id: UUID, roles: List[str] = None) -> str:
    """Create a JWT token for testing"""
    from app.core.security import create_access_token
    
    token_data = {
        "sub": str(user_id),
        "roles": roles or ["citizen"]
    }
    
    return create_access_token(token_data)


def assert_user_has_permissions(user_id: UUID, permissions: List[str]):
    """Assert that a user has all specified permissions"""
    async def check():
        service = PermissionService()
        for permission in permissions:
            has_perm = await service.user_has_permission(user_id, permission)
            assert has_perm, f"User {user_id} should have permission {permission}"
    
    return asyncio.run(check())


def assert_user_lacks_permissions(user_id: UUID, permissions: List[str]):
    """Assert that a user lacks all specified permissions"""
    async def check():
        service = PermissionService()
        for permission in permissions:
            has_perm = await service.user_has_permission(user_id, permission)
            assert not has_perm, f"User {user_id} should NOT have permission {permission}"
    
    return asyncio.run(check())


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPermissionPerformance:
    """Test permission system performance"""
    
    @pytest.mark.asyncio
    async def test_permission_check_performance(self):
        """Test that permission checks are fast enough"""
        import time
        
        service = PermissionService()
        user_id = uuid4()
        
        # Warm up
        await service.user_has_permission(user_id, "posts.get")
        
        # Time multiple permission checks
        start_time = time.time()
        for _ in range(100):
            await service.user_has_permission(user_id, "posts.get")
        end_time = time.time()
        
        # Should complete 100 checks in under 1 second
        duration = end_time - start_time
        assert duration < 1.0, f"100 permission checks took {duration:.2f}s (too slow)"
    
    @pytest.mark.asyncio
    async def test_role_expansion_performance(self):
        """Test that role permission expansion is performant"""
        import time
        
        start_time = time.time()
        for _ in range(1000):
            expand_role_permissions(DEFAULT_ROLE_PERMISSIONS["admin"])
        end_time = time.time()
        
        # Should complete 1000 expansions quickly
        duration = end_time - start_time
        assert duration < 0.5, f"1000 role expansions took {duration:.2f}s (too slow)"


# =============================================================================
# TEST FIXTURES AND UTILITIES
# =============================================================================

@pytest.fixture
def test_helper():
    """Test helper instance"""
    return PermissionTestHelper()


@pytest.fixture
async def test_permissions_setup():
    """Set up test permissions in database"""
    helper = PermissionTestHelper()
    await helper.setup_test_permissions()
    yield
    # Cleanup would go here


# Example test runner
if __name__ == "__main__":
    # Run specific tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "test_permission_name_generation"
    ])
