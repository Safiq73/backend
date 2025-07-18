import uvicorn
from app.main import app

if __name__ == "__main__":
    print("🚀 Starting CivicPulse API in DEVELOPMENT MODE")
    print("📝 Swagger docs available at: http://localhost:8000/docs")
    print("📚 ReDoc available at: http://localhost:8000/redoc")
    print("🔧 OpenAPI spec available at: http://localhost:8000/openapi.json")
    print("❤️  Health check available at: http://localhost:8000/health")
    print("⚠️  DEVELOPMENT MODE: All security features disabled for local testing")
    print("=" * 70)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",  # More verbose logging
        access_log=True,    # Enable access logging
        use_colors=True,    # Colorful console output
        reload_dirs=["app"],  # Watch app directory for changes
        reload_delay=0.25,  # Faster reload
    )
