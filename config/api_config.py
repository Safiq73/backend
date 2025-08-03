"""
Central configuration for API testing and development.
This file contains configurable URLs to avoid hardcoding across multiple test files.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Backend configuration
BACKEND_HOST = os.getenv('HOST', 'localhost')
BACKEND_PORT = int(os.getenv('PORT', '8000'))  # Convert to int immediately
BACKEND_PROTOCOL = os.getenv('BACKEND_PROTOCOL', 'http')

# Constructed URLs
BACKEND_URL = f"{BACKEND_PROTOCOL}://{BACKEND_HOST}:{BACKEND_PORT}"
API_BASE_URL = f"{BACKEND_URL}/api/v1"

# Common endpoints
ENDPOINTS = {
    'health': f"{BACKEND_URL}/health",
    'docs': f"{BACKEND_URL}/docs",
    'redoc': f"{BACKEND_URL}/redoc",
    'openapi': f"{BACKEND_URL}/openapi.json"
}

# For printing in run.py
def get_info_urls():
    return {
        'swagger': f"{BACKEND_URL}/docs",
        'redoc': f"{BACKEND_URL}/redoc", 
        'openapi': f"{BACKEND_URL}/openapi.json",
        'health': f"{BACKEND_URL}/health"
    }
