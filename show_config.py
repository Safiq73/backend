#!/usr/bin/env python3
"""
Configuration Summary Script
Shows the current URL configuration for easy verification and modification
"""

from config.api_config import BACKEND_URL, API_BASE_URL, ENDPOINTS, get_info_urls

def main():
    print("🔧 CivicPulse API URL Configuration")
    print("=" * 50)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base URL: {API_BASE_URL}")
    print()
    print("📍 Service Endpoints:")
    for name, url in get_info_urls().items():
        print(f"  {name.capitalize()}: {url}")
    print()
    print("🎯 To change the backend URL, set these environment variables:")
    print("  BACKEND_PROTOCOL=https (default: http)")
    print("  BACKEND_HOST=your-domain.com (default: localhost)")
    print("  BACKEND_PORT=443 (default: 8000)")
    print()
    print("Or modify config/api_config.py for permanent changes")

if __name__ == "__main__":
    main()
