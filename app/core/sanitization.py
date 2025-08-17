"""
Input sanitization utilities
"""
import re
import html
from typing import Optional, List
from urllib.parse import urlparse


class InputSanitizer:
    """Sanitize and validate user input"""
    
    # HTML tag patterns
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    SCRIPT_PATTERN = re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)
    STYLE_PATTERN = re.compile(r'<style[^>]*>.*?</style>', re.IGNORECASE | re.DOTALL)
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
        r"(--|#|/\*|\*/)",
        r"('|(\\')|(;|\\x00|\\n|\\r|\\x1a))"
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"javascript:",
        r"vbscript:",
        r"onload=",
        r"onerror=",
        r"onclick=",
        r"onmouseover=",
        r"onfocus=",
        r"onblur=",
        r"onchange=",
        r"onsubmit=",
        r"<iframe",
        r"<object",
        r"<embed",
        r"<link",
        r"<meta",
        r"<form",
        r"<input",
        r"<button",
        r"<textarea",
        r"<select",
        r"<option"
    ]
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """Remove HTML tags and sanitize content"""
        if not text:
            return ""
        
        # Remove script and style tags with their content
        text = InputSanitizer.SCRIPT_PATTERN.sub('', text)
        text = InputSanitizer.STYLE_PATTERN.sub('', text)
        
        # Remove all HTML tags
        text = InputSanitizer.HTML_TAG_PATTERN.sub('', text)
        
        # HTML encode remaining content
        text = html.escape(text)
        
        return text.strip()
    
    @staticmethod
    def sanitize_sql(text: str) -> str:
        """Sanitize input to prevent SQL injection"""
        if not text:
            return ""
        
        # Check for SQL injection patterns
        for pattern in InputSanitizer.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                # Log potential attack
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Potential SQL injection attempt detected: {text[:100]}")
                
                # Remove suspicious content
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    @staticmethod
    def sanitize_xss(text: str) -> str:
        """Sanitize input to prevent XSS attacks"""
        if not text:
            return ""
        
        # Check for XSS patterns
        for pattern in InputSanitizer.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                # Log potential attack
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Potential XSS attempt detected: {text[:100]}")
                
                # Remove suspicious content
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    @staticmethod
    def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
        """Comprehensive text sanitization"""
        if not text:
            return ""
        
        # Apply all sanitization methods
        text = InputSanitizer.sanitize_html(text)
        text = InputSanitizer.sanitize_sql(text)
        text = InputSanitizer.sanitize_xss(text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Truncate if max_length specified
        if max_length and len(text) > max_length:
            text = text[:max_length].strip()
        
        return text
    
    @staticmethod
    def sanitize_url(url: str) -> Optional[str]:
        """Sanitize and validate URL"""
        if not url:
            return None
        
        try:
            parsed = urlparse(url)
            
            # Only allow http/https schemes
            if parsed.scheme not in ['http', 'https']:
                return None
            
            # Reconstruct URL to ensure it's properly formatted
            sanitized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            if parsed.query:
                sanitized += f"?{parsed.query}"
            
            return sanitized
        
        except Exception:
            return None
    
    @staticmethod
    def sanitize_email(email: str) -> Optional[str]:
        """Sanitize and validate email"""
        if not email:
            return None
        
        # Basic email validation
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        # Clean the email
        email = email.strip().lower()
        
        # Validate format
        if not email_pattern.match(email):
            return None
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'[<>"\[\]\\]',
            r'javascript:',
            r'<script',
            r'--',
            r';'
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, email, re.IGNORECASE):
                return None
        
        return email
    
    @staticmethod
    def sanitize_username(username: str) -> Optional[str]:
        """Sanitize and validate username"""
        if not username:
            return None
        
        # Clean the username
        username = username.strip().lower()
        
        # Only allow alphanumeric characters and underscores
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return None
        
        # Check length
        if len(username) < 3 or len(username) > 50:
            return None
        
        # Check for reserved usernames
        reserved = [
            'admin', 'administrator', 'root', 'system', 'api',
            'www', 'mail', 'ftp', 'support', 'help', 'info',
            'contact', 'abuse', 'postmaster', 'webmaster'
        ]
        
        if username in reserved:
            return None
        
        return username
    
    @staticmethod
    def sanitize_search_query(query: str) -> str:
        """Sanitize search query"""
        if not query:
            return ""
        
        # Remove special characters that could be used for injection
        query = re.sub(r'[<>"\';(){}[\]\\]', '', query)
        
        # Normalize whitespace
        query = re.sub(r'\s+', ' ', query).strip()
        
        # Limit length
        if len(query) > 200:
            query = query[:200].strip()
        
        return query


def sanitize_request_data(data: dict) -> dict:
    """Sanitize all string values in request data"""
    sanitized = {}
    
    for key, value in data.items():
        if isinstance(value, str):
            if key in ['email']:
                sanitized[key] = InputSanitizer.sanitize_email(value)
            elif key in ['username']:
                sanitized[key] = InputSanitizer.sanitize_username(value)
            elif key in ['url', 'avatar_url', 'website']:
                sanitized[key] = InputSanitizer.sanitize_url(value)
            elif key in ['search', 'query']:
                sanitized[key] = InputSanitizer.sanitize_search_query(value)
            else:
                max_length = 2000 if key in ['content', 'description'] else 500
                sanitized[key] = InputSanitizer.sanitize_text(value, max_length)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_request_data(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_request_data(item) if isinstance(item, dict) 
                else InputSanitizer.sanitize_text(str(item)) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value
    
    return sanitized
