"""
Custom exception handlers for consistent API responses
"""
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.schemas import APIResponse
from app.core.logging_config import get_logger
import traceback

logger = get_logger('app.exceptions')


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle HTTPException and format it as APIResponse
    """
    logger.warning(f"HTTP Exception | Status: {exc.status_code} | Detail: {exc.detail} | Path: {request.url.path}")
    
    # Format the response as APIResponse
    response_data = APIResponse(
        success=False,
        message=exc.detail,
        data=None,
        errors=[exc.detail] if exc.detail else None
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data.dict()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors and format them as APIResponse
    """
    logger.warning(f"Validation Exception | Errors: {exc.errors()} | Path: {request.url.path}")
    
    # Extract error messages
    error_messages = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_messages.append(f"{field}: {message}")
    
    response_data = APIResponse(
        success=False,
        message="Validation failed",
        data=None,
        errors=error_messages
    )
    
    return JSONResponse(
        status_code=422,
        content=response_data.dict()
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions and format them as APIResponse
    """
    logger.error(f"Unexpected Exception | Type: {type(exc).__name__} | Message: {str(exc)} | Path: {request.url.path}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    response_data = APIResponse(
        success=False,
        message="An unexpected error occurred",
        data=None,
        errors=["Internal server error"]
    )
    
    return JSONResponse(
        status_code=500,
        content=response_data.dict()
    )
