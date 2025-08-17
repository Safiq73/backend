"""
Development middleware for local testing
"""
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class DevelopmentMiddleware(BaseHTTPMiddleware):
    """Development middleware to bypass certain restrictions for local testing"""
    
    def __init__(self, app: ASGIApp, enable_auth: bool = False):
        super().__init__(app)
        self.enable_auth = enable_auth
    
    async def dispatch(self, request: Request, call_next):
        """Process request with development-specific modifications"""
        
        # Log all requests in development
        logger.debug(f"Development Request: {request.method} {request.url}")
        logger.debug(f"Headers: {dict(request.headers)}")
        
        # Add development headers to bypass certain checks
        if not self.enable_auth:
            # Add a development user context if auth is disabled
            request.state.development_mode = True
            request.state.skip_auth = True
            logger.debug("Authentication bypassed for development")
        
        response = await call_next(request)
        
        # Add development-specific response headers
        response.headers["X-Development-Mode"] = "true"
        response.headers["X-Auth-Disabled"] = str(not self.enable_auth)
        
        logger.debug(f"Response Status: {response.status_code}")
        
        return response
