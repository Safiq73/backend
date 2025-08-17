"""
Rate limiting middleware for API endpoints
"""
import time
import asyncio
from typing import Dict, Optional
from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from anyio import EndOfStream
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using sliding window algorithm"""
    
    def __init__(self, app: ASGIApp, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients: Dict[str, Dict] = {}
        self.cleanup_interval = 300  # Clean up every 5 minutes
        self.last_cleanup = time.time()
        self.enabled = calls > 0  # Only enable if calls > 0
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address with better error handling"""
        try:
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                return forwarded_for.split(",")[0].strip()
            
            if request.client and hasattr(request.client, 'host'):
                return request.client.host
            
            # Fallback for cases where client info is not available
            return "unknown"
        except Exception as e:
            logger.warning(f"Could not determine client IP: {e}")
            return "unknown"
    
    def _cleanup_old_entries(self):
        """Clean up old entries to prevent memory leaks"""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        cutoff_time = now - self.period
        for client_ip in list(self.clients.keys()):
            client_data = self.clients[client_ip]
            client_data["requests"] = [
                req_time for req_time in client_data["requests"]
                if req_time > cutoff_time
            ]
            if not client_data["requests"]:
                del self.clients[client_ip]
        
        self.last_cleanup = now
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        # If rate limiting is disabled, just pass through
        if not self.enabled:
            return await call_next(request)
            
        try:
            client_ip = self._get_client_ip(request)
            current_time = time.time()
            
            # Skip rate limiting for health checks
            if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
                return await call_next(request)
            
            # Clean up old entries periodically
            self._cleanup_old_entries()
            
            # Initialize client data if not exists
            if client_ip not in self.clients:
                self.clients[client_ip] = {"requests": [], "blocked_until": 0}
            
            client_data = self.clients[client_ip]
            
            # Check if client is temporarily blocked
            if client_data["blocked_until"] > current_time:
                logger.warning(f"Rate limit exceeded - client blocked | IP: {client_ip}")
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={"Retry-After": str(int(client_data["blocked_until"] - current_time))}
                )
        except HTTPException:
            # Re-raise HTTP exceptions as they are expected
            raise
        except (EndOfStream, ConnectionError, asyncio.CancelledError) as e:
            # Handle ASGI stream and connection errors gracefully
            logger.warning(f"Connection issue for IP {client_ip}: {type(e).__name__}")
            raise
        except Exception as e:
            # Log unexpected errors but don't block the request
            logger.error(f"Rate limiting error for IP {client_ip if 'client_ip' in locals() else 'unknown'}: {e}")
            return await call_next(request)
        
        try:
            # Filter requests within the time window
            window_start = current_time - self.period
            client_data["requests"] = [
                req_time for req_time in client_data["requests"]
                if req_time > window_start
            ]
            
            # Check if rate limit is exceeded
            if len(client_data["requests"]) >= self.calls:
                # Block client for the remaining window period
                client_data["blocked_until"] = current_time + self.period
                logger.warning(f"Rate limit exceeded | IP: {client_ip} | Requests: {len(client_data['requests'])}")
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={"Retry-After": str(self.period)}
                )
            
            # Record the request
            client_data["requests"].append(current_time)
            
            # Process the request
            response = await call_next(request)
            
            # Add rate limit headers
            remaining = max(0, self.calls - len(client_data["requests"]))
            response.headers["X-RateLimit-Limit"] = str(self.calls)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(current_time + self.period))
            
            return response
            
        except HTTPException:
            # Re-raise HTTP exceptions as they are expected
            raise
        except (EndOfStream, ConnectionError, asyncio.CancelledError) as e:
            # Handle ASGI stream and connection errors gracefully
            logger.warning(f"Connection issue during request processing for IP {client_ip}: {type(e).__name__}")
            raise
        except Exception as e:
            # Log errors during request processing but still try to process the request
            logger.error(f"Error processing request for IP {client_ip}: {e}")
            # Try to process the request without rate limiting
            return await call_next(request)
