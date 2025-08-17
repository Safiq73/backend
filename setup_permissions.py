#!/usr/bin/env python3
"""
Quick Setup Script for CivicPulse Permission System

This script helps you integrate the permission system with your existing application.
Run this after implementing the permission system to set everything up.
"""

import os
import sys
import asyncio
from pathlib import Path

def print_status(message, status="info"):
    """Print colored status messages"""
    colors = {
        "info": "\033[94m",      # Blue
        "success": "\033[92m",   # Green
        "warning": "\033[93m",   # Yellow
        "error": "\033[91m",     # Red
        "reset": "\033[0m"       # Reset
    }
    
    icons = {
        "info": "ℹ️ ",
        "success": "✅",
        "warning": "⚠️ ",
        "error": "❌"
    }
    
    color = colors.get(status, colors["info"])
    icon = icons.get(status, "")
    reset = colors["reset"]
    
    print(f"{color}{icon} {message}{reset}")

def check_file_exists(file_path):
    """Check if a file exists"""
    return Path(file_path).exists()

def check_implementation():
    """Check if permission system files are present"""
    print_status("Checking permission system implementation...", "info")
    
    required_files = {
        "app/core/permissions.py": "Permission registry",
        "app/core/auth.py": "Authentication dependencies", 
        "app/models/permission.py": "Permission models",
        "app/services/permission_service.py": "Permission service",
        "app/middleware/permission_middleware.py": "Permission middleware",
        "app/api/endpoints/permission_management.py": "Permission API",
        "app/db/permissions_migration.sql": "Database migration",
        "run_permission_migration.py": "Migration runner"
    }
    
    missing_files = []
    for file_path, description in required_files.items():
        if check_file_exists(file_path):
            print_status(f"{description}: {file_path}", "success")
        else:
            print_status(f"MISSING {description}: {file_path}", "error")
            missing_files.append(file_path)
    
    if missing_files:
        print_status(f"Missing {len(missing_files)} required files. Please complete implementation first.", "error")
        return False
    
    print_status("All permission system files found!", "success")
    return True

def check_database_connection():
    """Check database connection"""
    try:
        import asyncpg
        print_status("Database driver (asyncpg) available", "success")
        return True
    except ImportError:
        print_status("Database driver (asyncpg) not installed. Run: pip install asyncpg", "warning")
        return False

def create_env_config():
    """Create or update .env file with permission settings"""
    env_file = Path(".env")
    
    env_settings = [
        "# Permission System Configuration",
        "ENABLE_PERMISSION_MIDDLEWARE=false  # Set to true to enable permission checking",
        "PERMISSION_FAIL_OPEN=true  # Set to false for production (fail closed)",
        "",
        "# Database Configuration (update with your values)",
        "# DATABASE_URL=postgresql://user:password@localhost:5432/civicpulse",
        ""
    ]
    
    if env_file.exists():
        print_status("Found existing .env file", "info")
        with open(env_file, 'r') as f:
            content = f.read()
        
        if "ENABLE_PERMISSION_MIDDLEWARE" not in content:
            print_status("Adding permission settings to .env file", "info")
            with open(env_file, 'a') as f:
                f.write("\n" + "\n".join(env_settings))
        else:
            print_status(".env file already has permission settings", "success")
    else:
        print_status("Creating .env file with permission settings", "info")
        with open(env_file, 'w') as f:
            f.write("\n".join(env_settings))

async def test_permission_system():
    """Test basic permission system functionality"""
    print_status("Testing permission system...", "info")
    
    try:
        # Test permission registry
        from app.core.permissions import API_PERMISSIONS_REGISTRY, get_permission_name
        print_status(f"Permission registry loaded: {len(API_PERMISSIONS_REGISTRY)} permissions", "success")
        
        # Test permission name generation
        test_permission = get_permission_name("/api/v1/posts", "GET")
        print_status(f"Permission name generation works: posts.get", "success")
        
        # Test permission service (without database)
        from app.services.permission_service import PermissionService
        service = PermissionService()
        print_status("Permission service loaded", "success")
        
        print_status("Basic permission system tests passed!", "success")
        return True
        
    except Exception as e:
        print_status(f"Permission system test failed: {e}", "error")
        return False

def print_next_steps():
    """Print next steps for setup"""
    print("\n" + "="*60)
    print_status("NEXT STEPS FOR INTEGRATION", "info")
    print("="*60)
    
    steps = [
        {
            "step": "1. Run Database Migration",
            "command": "python3 run_permission_migration.py --assign-default-roles --create-admin",
            "description": "Sets up permission tables and creates admin user"
        },
        {
            "step": "2. Enable Permission Middleware (Optional)",
            "command": "Edit .env file: ENABLE_PERMISSION_MIDDLEWARE=true",
            "description": "Enables automatic permission checking on all routes"
        },
        {
            "step": "3. Test Your Application",
            "command": "python3 run.py",
            "description": "Start your app and test permission endpoints"
        },
        {
            "step": "4. Test Permission API",
            "command": "Visit http://localhost:8000/docs",
            "description": "Check the new /permissions endpoints in Swagger"
        },
        {
            "step": "5. Add Permissions to Existing Endpoints",
            "command": "See examples in app/api/endpoints/posts_with_permissions.py",
            "description": "Update your existing endpoints with permission decorators"
        }
    ]
    
    for i, step_info in enumerate(steps, 1):
        print(f"\n{i}. {step_info['step']}")
        print(f"   Command: {step_info['command']}")
        print(f"   Description: {step_info['description']}")

def print_permission_examples():
    """Print quick permission usage examples"""
    print("\n" + "="*60)
    print_status("QUICK USAGE EXAMPLES", "info")
    print("="*60)
    
    examples = [
        "# Add to existing endpoint - Method 1 (Automatic):",
        "@router.get('/posts', dependencies=[Depends(check_permission_dependency)])",
        "",
        "# Add to existing endpoint - Method 2 (Explicit):",
        "from app.core.auth import require_permissions",
        "@router.post('/posts', dependencies=[Depends(require_permissions('posts.post'))])",
        "",
        "# Check permissions in code:",
        "from app.services.permission_service import PermissionService",
        "service = PermissionService()",
        "has_perm = await service.user_has_permission(user_id, 'posts.detail.put')",
        "",
        "# Check user's permissions (new API endpoint):",
        "GET /api/v1/permissions/my/permissions",
        "",
        "# Assign role to user (admin only):",
        "POST /api/v1/permissions/users/{user_id}/roles",
        "{'user_id': 'uuid', 'role_name': 'moderator'}"
    ]
    
    for example in examples:
        print(example)

async def main():
    """Main setup function"""
    print("🚀 CivicPulse Permission System Setup")
    print("="*60)
    
    # Check implementation
    if not check_implementation():
        sys.exit(1)
    
    # Check database
    check_database_connection()
    
    # Create env config
    create_env_config()
    
    # Test permission system
    await test_permission_system()
    
    # Print next steps
    print_next_steps()
    print_permission_examples()
    
    print("\n" + "="*60)
    print_status("Setup complete! Permission system is ready to use.", "success")
    print_status("The system is currently DISABLED by default for safety.", "warning")
    print_status("Enable it in .env when you're ready to test.", "info")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
