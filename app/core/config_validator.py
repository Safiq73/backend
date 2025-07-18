"""
Configuration validation utilities
"""
import os
import re
from typing import List, Dict, Any
from urllib.parse import urlparse


class ConfigValidator:
    """Validate application configuration"""
    
    @staticmethod
    def validate_database_url(url: str) -> bool:
        """Validate database URL format"""
        try:
            parsed = urlparse(url)
            return (
                parsed.scheme in ['postgresql', 'postgres'] and
                parsed.hostname and
                parsed.port and
                parsed.path.startswith('/')
            )
        except Exception:
            return False
    
    @staticmethod
    def validate_secret_key(key: str, min_length: int = 32, is_debug: bool = False) -> bool:
        """Validate secret key strength"""
        if not key:
            return False
        
        # More lenient validation for development
        if is_debug:
            return len(key) >= 16  # Minimum 16 chars for development
        
        if len(key) < min_length:
            return False
        
        # Check for common weak keys
        weak_keys = [
            'secret',
            'password',
            '123456',
            'change-me',
            'dev-key',
            'test-key'
        ]
        
        return not any(weak in key.lower() for weak in weak_keys)
    
    @staticmethod
    def validate_cors_origins(origins: List[str]) -> bool:
        """Validate CORS origins"""
        if not origins:
            return False
        
        # "*" is allowed for development but not recommended for production
        if "*" in origins:
            return len(origins) == 1  # Should be the only origin if present
        
        # Validate each origin
        for origin in origins:
            try:
                parsed = urlparse(origin)
                if not (parsed.scheme and parsed.netloc):
                    return False
            except Exception:
                return False
        
        return True
    
    @staticmethod
    def validate_email_config(host: str, port: int, user: str, password: str) -> bool:
        """Validate email configuration"""
        return all([
            host and isinstance(host, str),
            isinstance(port, int) and 1 <= port <= 65535,
            user and isinstance(user, str),
            password and isinstance(password, str)
        ])
    
    @staticmethod
    def validate_rate_limits(per_minute: int, per_hour: int) -> bool:
        """Validate rate limit settings"""
        return (
            isinstance(per_minute, int) and per_minute > 0 and
            isinstance(per_hour, int) and per_hour > 0 and
            per_hour >= per_minute
        )
    
    @staticmethod
    def validate_production_config(config: Dict[str, Any]) -> List[str]:
        """Validate production configuration and return list of issues"""
        issues = []
        
        # Debug mode check
        if config.get('debug', False):
            issues.append("Debug mode should be disabled in production")
        
        # Secret key validation
        if not ConfigValidator.validate_secret_key(config.get('secret_key', ''), is_debug=config.get('debug', False)):
            issues.append("Secret key is weak or too short")
        
        # Database URL validation
        if not ConfigValidator.validate_database_url(config.get('database_url', '')):
            issues.append("Database URL is invalid")
        
        # CORS validation
        origins = config.get('allowed_origins', [])
        if not ConfigValidator.validate_cors_origins(origins):
            issues.append("CORS origins are invalid")
        
        if '*' in origins:
            issues.append("Wildcard CORS origin (*) should not be used in production")
        
        # SSL/TLS checks
        if config.get('database_url', '').startswith('postgresql://'):
            issues.append("Database connection should use SSL in production")
        
        # File upload limits
        max_file_size = config.get('max_file_size', 0)
        if max_file_size > 50 * 1024 * 1024:  # 50MB
            issues.append("File upload size limit is too high")
        
        # Rate limiting
        rate_per_minute = config.get('rate_limit_per_minute', 0)
        rate_per_hour = config.get('rate_limit_per_hour', 0)
        if not ConfigValidator.validate_rate_limits(rate_per_minute, rate_per_hour):
            issues.append("Rate limit configuration is invalid")
        
        return issues


def validate_environment() -> None:
    """Validate environment configuration on startup"""
    from app.core.config import settings
    
    # Convert settings to dict for validation
    config_dict = {
        'debug': settings.debug,
        'secret_key': settings.secret_key,
        'database_url': settings.database_url,
        'allowed_origins': settings.allowed_origins,
        'max_file_size': settings.max_file_size,
        'rate_limit_per_minute': settings.rate_limit_per_minute,
        'rate_limit_per_hour': settings.rate_limit_per_hour
    }
    
    # Validate production configuration
    if not settings.debug:
        issues = ConfigValidator.validate_production_config(config_dict)
        if issues:
            print("⚠️  Production Configuration Issues:")
            for issue in issues:
                print(f"  - {issue}")
            print("\nReview your configuration before deploying to production.")
    
    # Always validate critical settings
    critical_issues = []
    
    # More lenient validation for development
    if not ConfigValidator.validate_secret_key(settings.secret_key, is_debug=settings.debug):
        if settings.debug:
            critical_issues.append("Secret key should be at least 16 characters for development")
        else:
            critical_issues.append("Secret key is weak or missing for production")
    
    if not ConfigValidator.validate_database_url(settings.database_url):
        critical_issues.append("Database URL is invalid")
    
    if critical_issues:
        print("❌ Critical Configuration Errors:")
        for issue in critical_issues:
            print(f"  - {issue}")
        
        # Only raise error for production issues or database problems
        if not settings.debug or any("database" in issue.lower() for issue in critical_issues):
            raise ValueError("Critical configuration errors detected")
        else:
            print("⚠️  Development mode - continuing with warnings...")
    
    print("✅ Configuration validation passed")
