import logging
import logging.config
import sys
from typing import Dict, Any
from pathlib import Path


def setup_logging(log_level: str = "DEBUG", log_file: str = None, enable_console: bool = True) -> None:
    """
    Configure logging for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path. If None, logs only to console
        enable_console: Force console logging for development
    """
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Define formatters
    formatters = {
        'detailed': {
            'format': '[%(asctime)s] %(levelname)-8s %(name)-25s %(funcName)-20s:%(lineno)-4d | %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '%(levelname)-8s | %(name)-20s | %(message)s'
        },
        'json': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "function": "%(funcName)s", "line": %(lineno)d, "message": "%(message)s"}',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    }
    
    # Define handlers - Always include console for development
    handlers = {
        'console': {
            'class': 'logging.StreamHandler',
            'level': log_level,
            'formatter': 'detailed',
            'stream': sys.stdout
        }
    }
    
    # Default root handlers - always include console
    root_handlers = ['console']
    
    # Add file handler if log_file is specified
    if log_file:
        handlers['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': log_level,
            'formatter': 'detailed',
            'filename': log_file,
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'encoding': 'utf8'
        }
        
        # Add error file handler
        error_log_file = str(log_path.parent / f"error_{log_path.name}")
        handlers['error_file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': error_log_file,
            'maxBytes': 5242880,  # 5MB
            'backupCount': 3,
            'encoding': 'utf8'
        }
        root_handlers.extend(['file', 'error_file'])
    
    # Define loggers
    loggers = {
        # Root logger
        '': {
            'level': log_level,
            'handlers': root_handlers
        },
        # FastAPI logger
        'fastapi': {
            'level': log_level,
            'handlers': ['console'] + (['file'] if log_file else []),
            'propagate': False
        },
        # Uvicorn loggers
        'uvicorn': {
            'level': 'INFO',
            'handlers': ['console'] + (['file'] if log_file else []),
            'propagate': False
        },
        'uvicorn.access': {
            'level': 'INFO',
            'handlers': ['console'] + (['file'] if log_file else []),
            'propagate': False
        },
        'uvicorn.error': {
            'level': 'INFO',
            'handlers': ['console'] + (['file'] if log_file else []),
            'propagate': False
        },
        # Database loggers
        'asyncpg': {
            'level': 'INFO',
            'handlers': ['console'] + (['file'] if log_file else []),
            'propagate': False
        },
        # Application specific loggers
        'app': {
            'level': log_level,
            'handlers': ['console'] + (['file'] if log_file else []),
            'propagate': False
        },
        'app.auth': {
            'level': log_level,
            'handlers': ['console'] + (['file'] if log_file else []),
            'propagate': False
        },
        'app.posts': {
            'level': log_level,
            'handlers': ['console'] + (['file'] if log_file else []),
            'propagate': False
        },
        'app.users': {
            'level': log_level,
            'handlers': ['console'] + (['file'] if log_file else []),
            'propagate': False
        },
        'app.database': {
            'level': log_level,
            'handlers': ['console'] + (['file'] if log_file else []),
            'propagate': False
        }
    }
    
    # Logging configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': formatters,
        'handlers': handlers,
        'loggers': loggers
    }
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Log configuration setup
    logger = logging.getLogger('app')
    logger.info(f"Logging configured with level: {log_level}")
    if log_file:
        logger.info(f"Logging to file: {log_file}")


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Logger name. If None, uses the calling module name
    
    Returns:
        Logger instance
    """
    if name is None:
        # Get the calling module name
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals['__name__']
    
    return logging.getLogger(name)


# Request logging middleware helper
def log_request_info(method: str, url: str, user_id: str = None, duration: float = None):
    """Log request information"""
    logger = get_logger('app.requests')
    
    user_info = f" | User: {user_id}" if user_id else " | User: Anonymous"
    duration_info = f" | Duration: {duration:.3f}s" if duration is not None else ""
    
    logger.info(f"{method} {url}{user_info}{duration_info}")


def log_error_with_context(logger: logging.Logger, error: Exception, context: Dict[str, Any] = None):
    """Log error with additional context"""
    error_msg = f"Error: {type(error).__name__}: {str(error)}"
    
    if context:
        context_str = " | ".join([f"{k}: {v}" for k, v in context.items()])
        error_msg += f" | Context: {context_str}"
    
    logger.error(error_msg, exc_info=True)


def log_performance_metric(operation: str, duration: float, context: Dict[str, Any] = None):
    """Log performance metrics"""
    logger = get_logger('app.performance')
    
    metric_msg = f"Performance | {operation} | Duration: {duration:.3f}s"
    
    if context:
        context_str = " | ".join([f"{k}: {v}" for k, v in context.items()])
        metric_msg += f" | {context_str}"
    
    if duration > 1.0:  # Slow operation threshold
        logger.warning(f"SLOW {metric_msg}")
    else:
        logger.info(metric_msg)
