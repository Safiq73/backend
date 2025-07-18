#!/bin/bash

# CivicPulse Development Startup Script
# This script configures the environment for unrestricted local development

echo "🚀 CivicPulse Development Environment Setup"
echo "=========================================="

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment active: $VIRTUAL_ENV"
else
    echo "⚠️  No virtual environment detected. Consider activating one."
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
python -c "import fastapi, uvicorn, asyncpg" 2>/dev/null && echo "✅ Core dependencies installed" || echo "❌ Missing dependencies. Run: pip install -r requirements.txt"

# Show current configuration
echo ""
echo "🔧 Development Configuration:"
echo "   - Environment: DEVELOPMENT"
echo "   - Debug Mode: ENABLED"
echo "   - Authentication: DISABLED"
echo "   - Rate Limiting: DISABLED"
echo "   - Security Headers: DISABLED"
echo "   - CORS: FULLY OPEN (*)"
echo "   - Logging Level: DEBUG"
echo "   - IP Blacklisting: DISABLED"
echo "   - Email Verification: DISABLED"
echo "   - OTP Verification: DISABLED"
echo ""

# Show available endpoints
echo "🌐 Available Endpoints:"
echo "   - API Documentation: http://localhost:8000/docs"
echo "   - ReDoc: http://localhost:8000/redoc"
echo "   - OpenAPI Spec: http://localhost:8000/openapi.json"
echo "   - Health Check: http://localhost:8000/health"
echo "   - API Base: http://localhost:8000/api/v1"
echo ""

echo "🛡️  SECURITY NOTICE:"
echo "   This configuration is for LOCAL DEVELOPMENT ONLY!"
echo "   All security features are disabled for easier testing."
echo "   DO NOT use this configuration in production!"
echo ""

echo "🚀 Starting development server..."
echo "   Use Ctrl+C to stop the server"
echo "=========================================="
echo ""

# Start the development server
python run.py
