# CivicPulse Raw SQL Database Implementation

This implementation provides a complete raw SQL-based database layer for CivicPulse using PostgreSQL with PostGIS for spatial operations. It offers full control over performance and complex spatial queries while maintaining security through parameterized queries.

## 🗄️ Database Schema Overview

### Core Tables
- **users** - User accounts with full-text search support
- **representatives** - Elected officials with spatial jurisdiction boundaries (PostGIS)
- **issues** - Civic issues with geolocation and auto-assignment
- **comments** - Threaded comments with path-based hierarchy
- **votes** - Voting system for issues and comments
- **notifications** - Real-time notification system
- **media** - External media references (S3/CDN URLs)
- **user_sessions** - JWT session management

### Spatial Features
- **PostGIS geometry columns** for precise spatial operations
- **Representative jurisdictions** as MultiPolygon boundaries
- **Issue locations** as Point coordinates
- **Spatial indexes** (GIST) for fast spatial queries
- **Automatic representative assignment** based on ST_Contains

### Full-Text Search
- **tsvector columns** for PostgreSQL full-text search
- **GIN indexes** for fast text search performance
- **Relevance ranking** with ts_rank scoring
- **Multi-table search** across issues, comments, and users

## 🚀 Quick Start

### 1. Install Dependencies
```bash
# PostgreSQL with PostGIS
brew install postgresql postgis  # macOS
# or
sudo apt-get install postgresql-13 postgresql-13-postgis-3  # Ubuntu

# Python dependencies
pip install asyncpg psycopg2-binary
```

### 2. Setup Database
```bash
# Create database and user
createdb civicpulse
psql civicpulse -c "CREATE EXTENSION postgis;"

# Initialize schema
cd backend
python app/init_db.py
```

### 3. Configuration
Update `app/core/config.py`:
```python
database_url = "postgresql://username:password@localhost:5432/civicpulse"
```

## 📋 SQL Query Examples

### Spatial Queries

#### Find Representatives for Location
```sql
SELECT r.title, r.office_name, u.name
FROM representatives r
JOIN users u ON r.user_id = u.id
WHERE ST_Contains(r.jurisdiction_boundary, ST_SetSRID(ST_MakePoint($1, $2), 4326))
  AND r.active = TRUE;
```

#### Issues Within Radius
```sql
SELECT i.title, ST_Distance(
    ST_Transform(i.location, 3857),
    ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 3857)
) as distance_meters
FROM issues i
WHERE ST_DWithin(
    ST_Transform(i.location, 3857),
    ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 3857),
    $3  -- radius in meters
)
ORDER BY distance_meters;
```

### Full-Text Search

#### Search Issues
```sql
SELECT title, description, ts_rank(search_vector, plainto_tsquery('english', $1)) as rank
FROM issues
WHERE search_vector @@ plainto_tsquery('english', $1)
ORDER BY rank DESC;
```

#### Search Across Multiple Tables
```sql
SELECT 'issue' as type, title, ts_rank(search_vector, query) as rank
FROM issues, plainto_tsquery('english', $1) query
WHERE search_vector @@ query

UNION ALL

SELECT 'user' as type, name, ts_rank(search_vector, query) as rank
FROM users, plainto_tsquery('english', $1) query
WHERE search_vector @@ query

ORDER BY rank DESC;
```

### Voting System

#### Cast Vote with Upsert
```sql
INSERT INTO votes (user_id, issue_id, vote_type)
VALUES ($1, $2, $3)
ON CONFLICT (user_id, issue_id) 
DO UPDATE SET vote_type = $3, updated_at = NOW();
```

#### Aggregate Vote Counts
```sql
SELECT 
    COUNT(CASE WHEN vote_type = 'upvote' THEN 1 END) as upvotes,
    COUNT(CASE WHEN vote_type = 'downvote' THEN 1 END) as downvotes
FROM votes 
WHERE issue_id = $1;
```

### Complex Analytics

#### Issue Clustering
```sql
WITH issue_clusters AS (
    SELECT 
        ST_ClusterKMeans(location, 5) OVER() as cluster_id,
        id, title, location
    FROM issues 
    WHERE status = 'open'
)
SELECT 
    cluster_id,
    COUNT(*) as issue_count,
    ST_Centroid(ST_Collect(location)) as cluster_center
FROM issue_clusters
GROUP BY cluster_id
HAVING COUNT(*) > 1;
```

#### Representative Workload
```sql
SELECT 
    r.title, u.name,
    COUNT(i.id) as total_issues,
    AVG(EXTRACT(EPOCH FROM (i.resolved_at - i.created_at))/3600) as avg_resolution_hours
FROM representatives r
JOIN users u ON r.user_id = u.id
LEFT JOIN issues i ON r.id = i.assigned_representative_id
GROUP BY r.id, r.title, u.name;
```

## 🔧 Service Layer Architecture

### Database Services
```python
# High-level service methods
user = await UserService.create_user(email, password_hash, name)
issues = await IssueService.get_issues_near_location(lng, lat, radius)
representatives = await RepresentativeService.get_representatives_for_location(lng, lat)
```

### Direct SQL Access
```python
# Direct SQL for complex operations
async with db_manager.get_connection() as conn:
    result = await conn.fetch(custom_query, param1, param2)
```

## 🔒 Security Features

### Parameterized Queries
All queries use parameterized statements to prevent SQL injection:
```python
await conn.fetch("SELECT * FROM users WHERE email = $1", email)
```

### Session Management
JWT tokens are tracked with secure session management:
```sql
CREATE TABLE user_sessions (
    refresh_token_hash VARCHAR(255),
    expires_at TIMESTAMP WITH TIME ZONE,
    ip_address INET,
    revoked BOOLEAN DEFAULT FALSE
);
```

## ⚡ Performance Optimizations

### Indexes
- **Spatial indexes** (GIST) on geometry columns
- **Full-text indexes** (GIN) on tsvector columns
- **Composite indexes** for common query patterns
- **Partial indexes** for filtered queries

### Triggers
- **Automatic vote count updates** via triggers
- **Activity tracking** with trigger-based logging
- **Search vector maintenance** via generated columns

### Connection Pooling
```python
pool = await asyncpg.create_pool(
    database_url,
    min_size=5,
    max_size=20,
    command_timeout=60
)
```

## 📊 Analytics & Reporting

### Dashboard Metrics
- Real-time issue counts by status/type
- Resolution time analytics
- User engagement metrics
- Spatial distribution analysis

### Performance Tracking
```sql
-- Daily analytics table for trend analysis
CREATE TABLE daily_analytics (
    date DATE PRIMARY KEY,
    total_users BIGINT,
    new_issues BIGINT,
    resolved_issues BIGINT,
    avg_resolution_time_hours DECIMAL(10,2)
);
```

## 🗺️ Spatial Data Management

### Representative Boundaries
Import GeoJSON boundaries:
```sql
INSERT INTO representatives (jurisdiction_boundary)
VALUES (ST_GeomFromGeoJSON($1));
```

### Spatial Queries
- **Point-in-polygon** for representative assignment
- **Distance calculations** for nearby issues
- **Clustering analysis** for issue hotspots
- **Coverage analysis** for jurisdiction overlap

## 🔄 Database Migrations

### Schema Updates
```sql
-- Add new column with default
ALTER TABLE issues ADD COLUMN priority_score INTEGER DEFAULT 0;

-- Create new index
CREATE INDEX CONCURRENTLY idx_issues_priority ON issues (priority_score DESC);
```

### Data Migration Scripts
```python
# Migrate existing data
async def migrate_priority_scores():
    async with db_manager.get_connection() as conn:
        await conn.execute("""
            UPDATE issues 
            SET priority_score = urgency_level * upvotes - downvotes
            WHERE priority_score = 0
        """)
```

## 🧪 Testing & Development

### Sample Data
```bash
# Insert sample data
python app/init_db.py sample
```

### SQL Demonstrations
```bash
# Run comprehensive SQL examples
python app/demo_sql_operations.py
```

### Database Reset
```bash
# Reset database (development only)
python app/init_db.py reset
```

## 📈 Monitoring & Maintenance

### Query Performance
```sql
-- Monitor slow queries
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC;
```

### Database Maintenance
```sql
-- Regular maintenance tasks
VACUUM ANALYZE;
REINDEX INDEX CONCURRENTLY idx_issues_location;
```

## 🔍 Debugging & Logging

### SQL Logging
```python
# Enable SQL query logging
logging.getLogger('asyncpg').setLevel(logging.DEBUG)
```

### Performance Profiling
```sql
-- Explain query plans
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM issues WHERE ST_DWithin(location, $1, $2);
```

This raw SQL implementation provides maximum performance and flexibility while maintaining security and scalability for the CivicPulse platform.
