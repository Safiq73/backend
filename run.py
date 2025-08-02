import uvicorn
from app.main import app
from config.api_config import get_info_urls

if __name__ == "__main__":
    urls = get_info_urls()
    print("🚀 Starting CivicPulse API in DEVELOPMENT MODE")
    print(f"📝 Swagger docs available at: {urls['swagger']}")
    print(f"📚 ReDoc available at: {urls['redoc']}")
    print(f"🔧 OpenAPI spec available at: {urls['openapi']}")
    print(f"❤️  Health check available at: {urls['health']}")
    print("⚠️  DEVELOPMENT MODE: All security features disabled for local testing")
    print("=" * 70)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="debug",  # More verbose logging
        access_log=True,    # Enable access logging
        use_colors=True,    # Colorful console output
        reload_dirs=["app"],  # Watch app directory for changes
        reload_delay=0.25,  # Faster reload
    )
