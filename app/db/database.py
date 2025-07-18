import asyncpg
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any, List, Union
from contextlib import asynccontextmanager
import logging
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Async PostgreSQL database manager with connection pooling"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def create_pool(self):
        """Create database connection pool"""
        try:
            # Create asyncpg pool for raw SQL operations
            self.pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60,
                server_settings={
                    'application_name': 'civicpulse_api',
                    'timezone': 'UTC'
                }
            )
            
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    
    async def close_pool(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
        logger.info("Database connection pool closed")
    
    async def check_and_create_tables(self):
        """Check if tables exist and create them if they don't"""
        try:
            async with self.get_connection() as conn:
                # Check if the essential tables exist
                required_tables = ['users', 'posts', 'comments', 'votes']
                missing_tables = []
                
                for table_name in required_tables:
                    table_exists = await conn.fetchval(
                        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = $1)",
                        table_name
                    )
                    if not table_exists:
                        missing_tables.append(table_name)
                
                if missing_tables:
                    logger.info(f"Missing tables: {missing_tables}. Creating database schema...")
                    await self._initialize_database_schema(conn)
                    logger.info("Database schema created successfully")
                else:
                    logger.info("All required database tables already exist")
                    
        except Exception as e:
            logger.error(f"Error checking/creating tables: {e}")
            raise
    
    async def _initialize_database_schema(self, conn: asyncpg.Connection):
        """Initialize database schema from SQL files"""
        sql_dir = Path(__file__).parent
        
        # Run schema creation
        schema_file = sql_dir / "schema.sql"
        if schema_file.exists():
            await self._run_sql_file(conn, schema_file)
            logger.info("Database schema applied successfully")
        else:
            logger.warning(f"Schema file not found: {schema_file}")
        
        # Run triggers
        triggers_file = sql_dir / "triggers.sql"
        if triggers_file.exists():
            await self._run_sql_file(conn, triggers_file)
            logger.info("Database triggers applied successfully")
        else:
            logger.warning(f"Triggers file not found: {triggers_file}")
    
    async def _run_sql_file(self, conn: asyncpg.Connection, file_path: Path):
        """Run SQL commands from a file"""
        logger.info(f"Running SQL file: {file_path}")
        sql_content = file_path.read_text()
        
        # For triggers.sql, execute the entire content as one statement
        # since it contains complex functions with dollar-quoted strings
        if file_path.name == 'triggers.sql':
            try:
                await conn.execute(sql_content)
                logger.info("Triggers file executed successfully")
            except Exception as e:
                logger.error(f"Error executing triggers file: {e}")
                # Skip triggers if they fail - they're not critical for basic functionality
                logger.warning("Skipping triggers - application will work without them")
        else:
            # For other files, split by semicolon and execute each statement
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            for i, statement in enumerate(statements, 1):
                try:
                    await conn.execute(statement)
                    logger.debug(f"Statement {i} executed successfully")
                except Exception as e:
                    logger.error(f"Error executing statement {i}: {e}")
                    logger.error(f"Statement: {statement[:200]}...")
                    # Skip extensions that might already exist or other non-critical errors
                    if any(keyword in str(e).lower() for keyword in ['already exists', 'extension', 'duplicate']):
                        logger.warning(f"Skipping non-critical error: {e}")
                        continue
                    else:
                        raise
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get database connection from pool"""
        if not self.pool:
            await self.create_pool()
        
        async with self.pool.acquire() as connection:
            yield connection

# Global database manager instance
db_manager = DatabaseManager()

# Dependency for FastAPI
async def get_db_connection():
    """FastAPI dependency to get database connection"""
    async with db_manager.get_connection() as connection:
        yield connection

# Alternative dependency function (for backwards compatibility)
async def get_db():
    """FastAPI dependency to get database connection"""
    async with db_manager.get_connection() as connection:
        yield connection

async def execute_query(
    connection: asyncpg.Connection,
    query: str,
    *args,
    fetch_one: bool = False,
    fetch_all: bool = False,
    return_count: bool = False
) -> Union[str, Dict[str, Any], List[Dict[str, Any]], int, None]:
    """
    Execute SQL query with proper error handling
    
    Args:
        connection: Database connection
        query: SQL query string
        *args: Query parameters
        fetch_one: Return single record
        fetch_all: Return all records
        return_count: Return affected row count
    
    Returns:
        Query result based on fetch parameters
    """
    try:
        if fetch_one:
            result = await connection.fetchrow(query, *args)
            return dict(result) if result else None
        elif fetch_all:
            results = await connection.fetch(query, *args)
            return [dict(row) for row in results]
        else:
            result = await connection.execute(query, *args)
            if return_count:
                # Extract number from "INSERT 0 5" or "UPDATE 3" etc.
                return int(result.split()[-1]) if result.split() else 0
            return result
    except asyncpg.PostgresError as e:
        logger.error(f"PostgreSQL error: {e}")
        raise
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise

async def execute_transaction(
    connection: asyncpg.Connection,
    queries: List[Dict[str, Any]]
) -> List[Any]:
    """
    Execute multiple queries in a transaction
    
    Args:
        connection: Database connection
        queries: List of query dictionaries with 'query', 'params', and options
    
    Returns:
        List of query results
    """
    async with connection.transaction():
        results = []
        for query_info in queries:
            query = query_info['query']
            params = query_info.get('params', [])
            options = query_info.get('options', {})
            
            result = await execute_query(connection, query, *params, **options)
            results.append(result)
        
        return results


async def startup_db():
    """Initialize database on startup"""
    await db_manager.create_pool()
    await db_manager.check_and_create_tables()

async def shutdown_db():
    """Close database connections on shutdown"""
    await db_manager.close_pool()
