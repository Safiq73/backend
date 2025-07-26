# Database Schema Migration: Roles → Titles

## Overview
This migration renames all "role" related terminology to "title" terminology throughout the CivicPulse application to avoid confusion between permission-based roles and position titles.

## Changes Made

### 1. Database Schema (`/app/db/schema.sql`)
- **Table renamed**: `roles` → `titles`
- **Columns renamed**: 
  - `role_name` → `title_name`
  - `role_type` → `title_type`
  - `users.role` → `users.title` (foreign key column)
- **Index updated**: `idx_users_role` → `idx_users_title`

### 2. Database Service (`/app/services/db_service.py`)
- **Methods renamed**:
  - `create_role()` → `create_title()`
  - `get_role_by_id()` → `get_title_by_id()`
  - `get_all_roles()` → `get_all_titles()`
  - `update_role()` → `update_title()`
  - `delete_role()` → `delete_title()`
- **SQL queries updated**: All JOIN operations now use `titles` table and `title_*` columns
- **Parameter mappings updated**: `title_data.get('title_name')` instead of `role_data.get('role_name')`

### 3. User Service (`/app/services/user_service.py`)
- **Field mappings updated**: 
  - `role_name` → `title_name`
  - `role_type` → `title_type`
- **Method name updated**: `_format_user_with_role()` → `_format_user_with_title()`

### 4. Pydantic Models (`/app/models/pydantic_models.py`)
- **Model classes renamed**:
  - `RoleBase` → `TitleBase`
  - `RoleCreate` → `TitleCreate`
  - `RoleUpdate` → `TitleUpdate`
  - `RoleResponse` → `TitleResponse`
- **Field names updated**: `role_info` → `title_info` in `UserResponse` and `AuthorInfo`
- **Comments updated**: Added clarification about titles vs permission roles

### 5. API Endpoints (`/app/api/endpoints/roles.py`)
- **Function names updated**:
  - `create_role()` → `create_title()`
  - `get_all_roles()` → `get_all_titles()`
  - `update_role()` → `update_title()`
  - `delete_role()` → `delete_title()`
- **Variable names updated**: All `role` variables renamed to `title`
- **Response models updated**: Using `TitleResponse` instead of `RoleResponse`

### 6. Model Imports (`/app/models/__init__.py`)
- **Exports updated**: All `Role*` class exports changed to `Title*`

### 7. Static Data Schema (`/static-data/maps/db_schema.sql`)
- **Table renamed**: `roles` → `titles`
- **Columns renamed**: `role_name` → `title_name`, `role_type` → `title_type`
- **Index names updated**: `roles_*` → `titles_*`
- **Foreign key updated**: `representatives.role_id` → `representatives.title_id`

### 8. Static Data Scripts (`/static-data/maps/insert_representitives.py`)
- **Variable names updated**: `jurisdiction_roles_level_rank_map` → `jurisdiction_titles_level_rank_map`
- **Method names updated**: 
  - `get_roles_by_level_rank()` → `get_titles_by_level_rank()`
  - `process_jurisdiction_role_mapping()` → `process_jurisdiction_title_mapping()`
- **SQL queries updated**: FROM `roles` → FROM `titles`, `role_id` → `title_id`
- **Data structure updated**: All role references changed to title references

## Migration Script
A migration script has been created at `/backend/migrate_roles_to_titles.sh` that:
1. Renames the database table from `roles` to `titles`
2. Renames columns: `role_name` → `title_name`, `role_type` → `title_type`
3. Renames the users table column: `role` → `title`
4. Updates indexes and foreign key references
5. Provides verification that the migration completed successfully

## Running the Migration

### Prerequisites
- PostgreSQL client tools (psql) installed
- Database connection credentials configured
- Application stopped (to avoid conflicts during migration)

### Steps
1. **Backup your database** (highly recommended):
   ```bash
   pg_dump -h localhost -U civicpulse_user -d civicpulse > backup_before_migration.sql
   ```

2. **Run the migration script**:
   ```bash
   cd backend
   ./migrate_roles_to_titles.sh
   ```

3. **Test the application** to ensure everything works correctly

### Manual Migration (Alternative)
If you prefer to run the migration manually:
```sql
-- Connect to your database and run:
\i app/db/migrations/001_rename_roles_to_titles.sql
```

## Verification
After migration, verify that:
1. ✅ The `titles` table exists with correct column names
2. ✅ The `roles` table no longer exists
3. ✅ Users table has `title` column (not `role`)
4. ✅ Foreign key constraints are working
5. ✅ API endpoints respond correctly
6. ✅ User profiles show title information

## Rollback Plan
If you need to rollback this migration:
1. Restore from the backup created before migration
2. Or create a reverse migration script that:
   - Renames `titles` back to `roles`
   - Renames columns back to original names
   - Updates all code references back to role terminology

## Impact Assessment
- **Breaking Changes**: API endpoints that referenced "role" now use "title"
- **Database**: Structure changed but data preserved
- **Frontend**: May need updates if it directly references role fields
- **Performance**: No performance impact expected
- **Compatibility**: Existing data remains intact, just with new terminology

## Post-Migration Tasks
1. Update any frontend code that references role fields
2. Update API documentation to reflect title terminology
3. Test all user-related functionality
4. Update any external integrations that rely on role field names
5. Consider adding rep_accounts enhancement (next phase)

---
**Migration Date**: 2025-07-26  
**Version**: 1.0  
**Status**: Ready for execution
