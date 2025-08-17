"""
Security headers middleware
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Security headers for regular pages
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }
        
        # Relaxed CSP for Swagger UI to allow external CDN resources
        self.swagger_csp = "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; font-src 'self' cdn.jsdelivr.net; img-src 'self' data: cdn.jsdelivr.net"
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response"""
        response = await call_next(request)
        
        # Use relaxed CSP for Swagger UI endpoints
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            # Apply relaxed security headers for Swagger UI
            for header, value in self.security_headers.items():
                if header == "Content-Security-Policy":
                    response.headers[header] = self.swagger_csp
                else:
                    response.headers[header] = value
        else:
            # Apply standard security headers for other endpoints
            for header, value in self.security_headers.items():
                response.headers[header] = value
        
        # Add additional headers for API responses
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response
