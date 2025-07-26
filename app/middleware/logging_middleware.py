import time
import uuid
import asyncio
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from anyio import EndOfStream
from app.core.logging_config import get_logger, log_request_info, log_performance_metric

"""


"""



class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses
    """
    
    def __init__(self, app, enable_request_logging: bool = True, enable_performance_logging: bool = True):
        super().__init__(app)
        self.enable_request_logging = enable_request_logging
        self.enable_performance_logging = enable_performance_logging
        self.logger = get_logger('app.middleware')

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Extract user info if available
        user_id = None
        if hasattr(request.state, 'user') and request.state.user:
            user_id = request.state.user.get('id')
        
        # Log request start
        if self.enable_request_logging:
            self.logger.info(
                f"Request START | ID: {request_id} | "
                f"{request.method} {request.url.path} | "
                f"Client: {request.client.host if request.client else 'unknown'} | "
                f"User: {user_id or 'anonymous'}"
            )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log request completion
            if self.enable_request_logging:
                self.logger.info(
                    f"Request END | ID: {request_id} | "
                    f"{request.method} {request.url.path} | "
                    f"Status: {response.status_code} | "
                    f"Duration: {duration:.3f}s | "
                    f"User: {user_id or 'anonymous'}"
                )
            
            # Log performance metrics
            if self.enable_performance_logging:
                log_performance_metric(
                    f"{request.method} {request.url.path}",
                    duration,
                    {
                        'status_code': response.status_code,
                        'user_id': user_id,
                        'request_id': request_id
                    }
                )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except (EndOfStream, ConnectionError, asyncio.CancelledError) as e:
            duration = time.time() - start_time
            # Log connection issues but don't spam logs
            self.logger.warning(
                f"Connection issue | ID: {request_id} | "
                f"{request.method} {request.url.path} | "
                f"Error: {type(e).__name__} | "
                f"Duration: {duration:.3f}s"
            )
            # Re-raise connection-related exceptions
            raise
        except Exception as e:
            duration = time.time() - start_time
            
            # Log error
            self.logger.error(
                f"Request ERROR | ID: {request_id} | "
                f"{request.method} {request.url.path} | "
                f"Error: {type(e).__name__}: {str(e)} | "
                f"Duration: {duration:.3f}s | "
                f"User: {user_id or 'anonymous'}",
                exc_info=True
            )
            
            # Re-raise the exception
            raise
