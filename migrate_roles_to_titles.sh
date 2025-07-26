#!/bin/bash

# Database Migration Script: Rename roles to titles
# This script applies the database schema changes to align with the code

echo "🚀 Starting database migration: roles → titles"
echo "================================================"

# Database connection details (update these as needed)
DB_HOST=${DB_HOST:-"localhost"}
DB_PORT=${DB_PORT:-"5432"}
DB_NAME=${DB_NAME:-"civicpulse"}
DB_USER=${DB_USER:-"civicpulse_user"}

# Migration file path
MIGRATION_FILE="app/db/migrations/001_rename_roles_to_titles.sql"

# Check if migration file exists
if [ ! -f "$MIGRATION_FILE" ]; then
    echo "❌ Migration file not found: $MIGRATION_FILE"
    exit 1
fi

echo "📋 Migration Overview:"
echo "- Rename 'roles' table to 'titles'"
echo "- Rename 'role_name' column to 'title_name'"
echo "- Rename 'role_type' column to 'title_type'"
echo "- Rename 'role' column in users table to 'title'"
echo "- Update indexes and foreign key references"
echo ""

# Prompt for confirmation
read -p "🤔 Do you want to proceed with this migration? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Migration cancelled"
    exit 1
fi

echo "🔄 Running migration..."

# Run the migration
if command -v psql >/dev/null 2>&1; then
    # Use psql if available
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$MIGRATION_FILE"
    RESULT=$?
else
    echo "❌ psql command not found. Please install PostgreSQL client tools or run the migration manually."
    echo "📁 Migration file location: $MIGRATION_FILE"
    exit 1
fi

if [ $RESULT -eq 0 ]; then
    echo "✅ Migration completed successfully!"
    echo ""
    echo "📊 Summary of changes:"
    echo "- ✅ roles table → titles table"
    echo "- ✅ role_name column → title_name column"
    echo "- ✅ role_type column → title_type column"
    echo "- ✅ users.role column → users.title column"
    echo "- ✅ Updated indexes and foreign keys"
    echo ""
    echo "🎉 Your database schema now matches the updated Python code!"
else
    echo "❌ Migration failed with exit code: $RESULT"
    echo "📝 Please check the error messages above and fix any issues before retrying."
    exit 1
fi
