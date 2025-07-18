"""
Comprehensive test suite for authentication endpoints
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import create_application
from app.core.config import settings


@pytest.fixture
def client():
    """Create test client"""
    app = create_application()
    return TestClient(app)


@pytest.fixture
def mock_user_service():
    """Mock user service"""
    with patch('app.api.endpoints.auth.user_service') as mock:
        yield mock


@pytest.fixture
def mock_auth_service():
    """Mock auth service"""
    with patch('app.api.endpoints.auth.auth_service') as mock:
        yield mock


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_register_success(self, client, mock_user_service, mock_auth_service):
        """Test successful user registration"""
        # Mock responses
        mock_user_service.create_user.return_value = asyncio.Future()
        mock_user_service.create_user.return_value.set_result({
            'id': 'test-user-id',
            'email': 'test@example.com',
            'username': 'testuser',
            'display_name': 'Test User'
        })
        
        mock_auth_service.create_tokens.return_value = asyncio.Future()
        mock_auth_service.create_tokens.return_value.set_result({
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token',
            'token_type': 'bearer'
        })
        
        # Test registration
        response = client.post('/api/v1/auth/register', json={
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPass123!',
            'display_name': 'Test User'
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == 'User registered successfully'
        assert 'user' in data['data']
        assert 'tokens' in data['data']
    
    def test_register_validation_error(self, client):
        """Test registration with validation errors"""
        # Test weak password
        response = client.post('/api/v1/auth/register', json={
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'weak',  # Too weak
            'display_name': 'Test User'
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email"""
        response = client.post('/api/v1/auth/register', json={
            'email': 'invalid-email',
            'username': 'testuser',
            'password': 'TestPass123!',
            'display_name': 'Test User'
        })
        
        assert response.status_code == 422
    
    def test_register_reserved_username(self, client):
        """Test registration with reserved username"""
        response = client.post('/api/v1/auth/register', json={
            'email': 'test@example.com',
            'username': 'admin',  # Reserved username
            'password': 'TestPass123!',
            'display_name': 'Test User'
        })
        
        assert response.status_code == 422
    
    def test_register_temporary_email(self, client, mock_user_service):
        """Test registration with temporary email"""
        response = client.post('/api/v1/auth/register', json={
            'email': 'test@tempmail.com',  # Temporary email
            'username': 'testuser',
            'password': 'TestPass123!',
            'display_name': 'Test User'
        })
        
        assert response.status_code == 400
        assert 'temporary email' in response.json()['detail'].lower()
    
    def test_login_success(self, client, mock_auth_service):
        """Test successful login"""
        # Mock successful authentication
        mock_auth_service.authenticate_user.return_value = asyncio.Future()
        mock_auth_service.authenticate_user.return_value.set_result({
            'id': 'test-user-id',
            'email': 'test@example.com',
            'username': 'testuser',
            'display_name': 'Test User'
        })
        
        mock_auth_service.create_tokens.return_value = asyncio.Future()
        mock_auth_service.create_tokens.return_value.set_result({
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token',
            'token_type': 'bearer'
        })
        
        response = client.post('/api/v1/auth/login', json={
            'email': 'test@example.com',
            'password': 'TestPass123!'
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == 'Login successful'
        assert 'tokens' in data['data']
    
    def test_login_invalid_credentials(self, client, mock_auth_service):
        """Test login with invalid credentials"""
        # Mock authentication failure
        mock_auth_service.authenticate_user.return_value = asyncio.Future()
        mock_auth_service.authenticate_user.return_value.set_result(None)
        
        response = client.post('/api/v1/auth/login', json={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 401
        assert 'Invalid credentials' in response.json()['detail']
    
    def test_logout_success(self, client, mock_auth_service):
        """Test successful logout"""
        mock_auth_service.revoke_token.return_value = asyncio.Future()
        mock_auth_service.revoke_token.return_value.set_result(True)
        
        response = client.post('/api/v1/auth/logout', json={
            'refresh_token': 'test-refresh-token'
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == 'Logged out successfully'


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limit_exceeded(self, client):
        """Test rate limiting"""
        # Make requests until rate limit is exceeded
        for _ in range(settings.rate_limit_per_minute + 1):
            response = client.get('/api/v1/auth/login')
            if response.status_code == 429:
                assert 'Rate limit exceeded' in response.json()['detail']
                assert 'Retry-After' in response.headers
                break
        else:
            pytest.fail("Rate limit was not enforced")


class TestSecurityHeaders:
    """Test security headers"""
    
    def test_security_headers_present(self, client):
        """Test that security headers are present"""
        response = client.get('/health')
        
        expected_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Strict-Transport-Security',
            'Referrer-Policy',
            'Content-Security-Policy'
        ]
        
        for header in expected_headers:
            assert header in response.headers
    
    def test_api_cache_headers(self, client):
        """Test API cache headers"""
        response = client.get('/api/v1/health')
        
        assert response.headers.get('Cache-Control') == 'no-store, no-cache, must-revalidate, max-age=0'
        assert response.headers.get('Pragma') == 'no-cache'
        assert response.headers.get('Expires') == '0'


class TestInputSanitization:
    """Test input sanitization"""
    
    def test_xss_prevention(self, client):
        """Test XSS prevention in input"""
        malicious_input = '<script>alert("xss")</script>'
        
        response = client.post('/api/v1/auth/register', json={
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPass123!',
            'display_name': malicious_input
        })
        
        # Should either sanitize or reject the input
        assert response.status_code in [200, 400, 422]
        
        if response.status_code == 200:
            # Input should be sanitized
            data = response.json()
            assert '<script>' not in str(data)
    
    def test_sql_injection_prevention(self, client):
        """Test SQL injection prevention"""
        malicious_input = "'; DROP TABLE users; --"
        
        response = client.post('/api/v1/auth/login', json={
            'email': malicious_input,
            'password': 'TestPass123!'
        })
        
        # Should not cause a server error
        assert response.status_code != 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
