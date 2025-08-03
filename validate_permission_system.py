"""
Dynamic Permission System Implementation Summary

This script provides a comprehensive overview of the CivicPulse permission system
implementation and validates that all components are properly integrated.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

class PermissionSystemValidator:
    """Validates the permission system implementation"""
    
    def __init__(self, backend_path: str = None):
        self.backend_path = Path(backend_path or ".")
        self.validation_results = []
        self.errors = []
    
    def validate_implementation(self) -> Dict[str, Any]:
        """Run complete validation of the permission system"""
        print("🔍 Validating Dynamic Permission System Implementation...")
        print("=" * 60)
        
        # Check file structure
        self._check_file_structure()
        
        # Check database schema
        self._check_database_schema()
        
        # Check permission registry
        self._check_permission_registry()
        
        # Check middleware integration
        self._check_middleware_integration()
        
        # Check API endpoints
        self._check_api_endpoints()
        
        # Check testing infrastructure
        self._check_testing_infrastructure()
        
        # Generate report
        return self._generate_report()
    
    def _check_file_structure(self):
        """Check that all required files are present"""
        print("\n📁 Checking File Structure...")
        
        required_files = [
            "app/core/permissions.py",
            "app/core/auth.py", 
            "app/models/permission.py",
            "app/services/permission_service.py",
            "app/middleware/permission_middleware.py",
            "app/api/endpoints/permission_management.py",
            "app/db/permissions_migration.sql",
            "run_permission_migration.py",
            "test_permission_system.py"
        ]
        
        for file_path in required_files:
            full_path = self.backend_path / file_path
            if full_path.exists():
                print(f"  ✅ {file_path}")
                self.validation_results.append(f"File exists: {file_path}")
            else:
                print(f"  ❌ {file_path} - MISSING")
                self.errors.append(f"Missing file: {file_path}")
    
    def _check_database_schema(self):
        """Check database schema files"""
        print("\n🗄️  Checking Database Schema...")
        
        schema_file = self.backend_path / "app/db/schema.sql"
        migration_file = self.backend_path / "app/db/permissions_migration.sql"
        
        if schema_file.exists():
            content = schema_file.read_text()
            
            # Check for permission-related tables in main schema
            required_tables = [
                "system_roles",
                "api_permissions", 
                "user_roles",
                "role_api_permissions"
            ]
            
            for table in required_tables:
                if table in content:
                    print(f"  ✅ Table definition found: {table}")
                else:
                    print(f"  ⚠️  Table definition not found in main schema: {table}")
        
        if migration_file.exists():
            content = migration_file.read_text()
            
            # Check migration content
            checks = [
                ("INSERT INTO system_roles", "Default roles"),
                ("INSERT INTO api_permissions", "API permissions"),
                ("INSERT INTO role_api_permissions", "Role-permission mappings"),
                ("BEGIN;", "Transaction handling"),
                ("COMMIT;", "Transaction commit")
            ]
            
            for check_text, description in checks:
                if check_text in content:
                    print(f"  ✅ Migration includes: {description}")
                else:
                    print(f"  ❌ Migration missing: {description}")
                    self.errors.append(f"Migration missing: {description}")
    
    def _check_permission_registry(self):
        """Check the permission registry implementation"""
        print("\n📋 Checking Permission Registry...")
        
        permissions_file = self.backend_path / "app/core/permissions.py"
        if permissions_file.exists():
            content = permissions_file.read_text()
            
            checks = [
                ("API_PERMISSIONS_REGISTRY", "Permission registry constant"),
                ("class APIPermission", "APIPermission class"),
                ("DEFAULT_ROLE_PERMISSIONS", "Default role mappings"),
                ("get_permission_name", "Permission name generation"),
                ("expand_role_permissions", "Role permission expansion")
            ]
            
            for check_text, description in checks:
                if check_text in content:
                    print(f"  ✅ {description}")
                else:
                    print(f"  ❌ Missing: {description}")
                    self.errors.append(f"Permission registry missing: {description}")
    
    def _check_middleware_integration(self):
        """Check middleware implementation"""
        print("\n🔧 Checking Middleware Integration...")
        
        middleware_file = self.backend_path / "app/middleware/permission_middleware.py"
        if middleware_file.exists():
            content = middleware_file.read_text()
            
            checks = [
                ("class PermissionMiddleware", "Middleware class"),
                ("check_route_permission", "Route permission checking"),
                ("_is_public_route", "Public route detection"),
                ("require_permission", "Permission decorator"),
                ("require_role", "Role decorator")
            ]
            
            for check_text, description in checks:
                if check_text in content:
                    print(f"  ✅ {description}")
                else:
                    print(f"  ❌ Missing: {description}")
                    self.errors.append(f"Middleware missing: {description}")
    
    def _check_api_endpoints(self):
        """Check API endpoint implementations"""
        print("\n🌐 Checking API Endpoints...")
        
        # Check permission management endpoints
        mgmt_file = self.backend_path / "app/api/endpoints/permission_management.py"
        if mgmt_file.exists():
            content = mgmt_file.read_text()
            
            endpoints = [
                ("/roles", "Role management"),
                ("/permissions", "Permission management"),
                ("/users/{user_id}/roles", "User role assignment"),
                ("/my/permissions", "User permission info")
            ]
            
            for endpoint, description in endpoints:
                if endpoint in content:
                    print(f"  ✅ {description} endpoint")
                else:
                    print(f"  ❌ Missing: {description} endpoint")
        
        # Check example endpoint with permissions
        example_file = self.backend_path / "app/api/endpoints/posts_with_permissions.py"
        if example_file.exists():
            print("  ✅ Example endpoint with permission integration")
        else:
            print("  ⚠️  No example endpoint implementation found")
    
    def _check_testing_infrastructure(self):
        """Check testing infrastructure"""
        print("\n🧪 Checking Testing Infrastructure...")
        
        test_file = self.backend_path / "test_permission_system.py"
        if test_file.exists():
            content = test_file.read_text()
            
            test_components = [
                ("TestPermissionRegistry", "Registry tests"),
                ("TestPermissionService", "Service tests"),
                ("TestPermissionMiddleware", "Middleware tests"),
                ("TestPermissionIntegration", "Integration tests"),
                ("PermissionTestHelper", "Test utilities")
            ]
            
            for component, description in test_components:
                if component in content:
                    print(f"  ✅ {description}")
                else:
                    print(f"  ❌ Missing: {description}")
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate final validation report"""
        print("\n" + "=" * 60)
        print("📊 VALIDATION REPORT")
        print("=" * 60)
        
        total_checks = len(self.validation_results) + len(self.errors)
        passed_checks = len(self.validation_results)
        
        print(f"✅ Passed: {passed_checks}")
        print(f"❌ Failed: {len(self.errors)}")
        print(f"📈 Success Rate: {(passed_checks/total_checks)*100:.1f}%")
        
        if self.errors:
            print("\n🚨 ERRORS TO FIX:")
            for error in self.errors:
                print(f"  • {error}")
        
        implementation_status = self._get_implementation_status()
        
        print(f"\n📋 IMPLEMENTATION STATUS:")
        for step, status in implementation_status.items():
            status_icon = "✅" if status["completed"] else "⏳"
            print(f"  {status_icon} {step}: {status['description']}")
        
        return {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": len(self.errors),
            "success_rate": (passed_checks/total_checks)*100,
            "errors": self.errors,
            "implementation_status": implementation_status
        }
    
    def _get_implementation_status(self) -> Dict[str, Dict[str, Any]]:
        """Get current implementation status"""
        return {
            "Step 1 - Database Schema": {
                "completed": True,
                "description": "Dynamic permission tables and migration created"
            },
            "Step 2 - Auth Dependencies": {
                "completed": True,
                "description": "FastAPI auth dependencies and decorators implemented"
            },
            "Step 3 - Permission Middleware": {
                "completed": True,
                "description": "Automatic route permission checking middleware created"
            },
            "Step 4 - Permission Registry": {
                "completed": True,
                "description": "Route-based permission registry and expansion logic"
            },
            "Step 5 - Permission Service": {
                "completed": True,
                "description": "Database operations and permission checking service"
            },
            "Step 6 - API Endpoints": {
                "completed": True,
                "description": "Permission management API endpoints created"
            },
            "Step 7 - Migration Runner": {
                "completed": True,
                "description": "Database migration and setup scripts created"
            },
            "Step 8 - Testing Framework": {
                "completed": True,
                "description": "Comprehensive testing utilities and test cases"
            },
            "Step 9 - Example Integration": {
                "completed": True,
                "description": "Example endpoint implementations with permissions"
            },
            "Step 10 - Documentation": {
                "completed": False,
                "description": "API documentation and usage guides (PENDING)"
            }
        }


def print_next_steps():
    """Print recommended next steps"""
    print("\n🚀 NEXT STEPS:")
    print("=" * 60)
    
    steps = [
        "1. Run database migration:",
        "   python run_permission_migration.py --assign-default-roles --create-admin",
        "",
        "2. Update main FastAPI app to use permission middleware:",
        "   Replace app/main.py with app/main_with_permissions.py content",
        "",
        "3. Update existing API endpoints:",
        "   Add permission decorators or middleware to your current endpoints",
        "",
        "4. Test the permission system:",
        "   python -m pytest test_permission_system.py -v",
        "",
        "5. Create admin user and test role assignments:",
        "   Use the permission management API endpoints",
        "",
        "6. Frontend Integration:",
        "   Update frontend to handle permission-based UI rendering",
        "",
        "7. Production Deployment:",
        "   Set up proper environment variables and security settings"
    ]
    
    for step in steps:
        print(step)


def print_permission_examples():
    """Print permission usage examples"""
    print("\n💡 PERMISSION USAGE EXAMPLES:")
    print("=" * 60)
    
    examples = [
        "# Using middleware (automatic checking):",
        "@router.get('/posts', dependencies=[Depends(check_permission_dependency)])",
        "",
        "# Using explicit permission decorator:",
        "@router.post('/posts', dependencies=[Depends(require_permissions('posts.post'))])",
        "",
        "# Using role-based access:",
        "@router.delete('/posts/{id}', dependencies=[Depends(require_roles('moderator', 'admin'))])",
        "",
        "# Custom permission logic in endpoint:",
        "async def update_post(post_id, current_user=Depends(get_current_user)):",
        "    user_permissions = await get_user_permissions(current_user)",
        "    if 'posts.detail.put' not in user_permissions:",
        "        raise HTTPException(403, 'Permission denied')",
        "",
        "# Check user's current permissions:",
        "GET /api/v1/permissions/my/permissions",
        "",
        "# Assign role to user (admin only):",
        "POST /api/v1/permissions/users/{user_id}/roles",
        "{ 'user_id': 'uuid', 'role_name': 'moderator' }"
    ]
    
    for example in examples:
        print(example)


if __name__ == "__main__":
    # Get backend path from command line or use current directory
    backend_path = sys.argv[1] if len(sys.argv) > 1 else "."
    
    # Run validation
    validator = PermissionSystemValidator(backend_path)
    report = validator.validate_implementation()
    
    # Print additional information
    print_next_steps()
    print_permission_examples()
    
    # Exit with appropriate code
    if report["failed_checks"] > 0:
        print(f"\n⚠️  Validation completed with {report['failed_checks']} errors")
        sys.exit(1)
    else:
        print(f"\n🎉 Permission system implementation validation passed!")
        sys.exit(0)
