"""
Representative service layer - Production implementation using raw SQL
"""
import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from fastapi import HTTPException
from app.services.db_service import DatabaseService
from app.db.database import db_manager

logger = logging.getLogger(__name__)

class RepresentativeService:
    """Service for representative-related operations using raw SQL"""
    
    def __init__(self):
        self.db_service = DatabaseService()
    
    async def get_available_representatives(
        self, 
        user_location: Optional[Dict[str, float]] = None,
        page: int = 1,
        limit: int = 20,
        search_query: Optional[str] = None,
        title_filter: Optional[str] = None,
        jurisdiction_name: Optional[str] = None,
        jurisdiction_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get available representatives with filtering and pagination"""
        # Calculate offset for pagination
        offset = (page - 1) * limit
        
        # Build WHERE clause dynamically
        where_conditions = ["r.user_id IS NULL"]  # Only show unclaimed representative accounts
        params = []
        param_count = 0
        
        if search_query:
            param_count += 1
            where_conditions.append(f"""(
                LOWER(t.title_name) LIKE LOWER(${param_count}) OR 
                LOWER(j.name) LIKE LOWER(${param_count}) OR
                LOWER(t.abbreviation) LIKE LOWER(${param_count})
            )""")
            params.append(f"%{search_query}%")
        
        if title_filter:
            param_count += 1
            where_conditions.append(f"LOWER(t.title_name) = LOWER(${param_count})")
            params.append(title_filter)
            
        if jurisdiction_name:
            param_count += 1
            where_conditions.append(f"LOWER(j.name) = LOWER(${param_count})")
            params.append(jurisdiction_name)
            
        if jurisdiction_level:
            param_count += 1
            where_conditions.append(f"j.level_name = ${param_count}")
            params.append(jurisdiction_level)
        
        where_clause = " AND ".join(where_conditions)
        
        # Count total records for pagination
        count_query = f"""
            SELECT COUNT(*) as total
            FROM representatives r
            JOIN jurisdictions j ON r.jurisdiction_id = j.id
            JOIN titles t ON r.title_id = t.id
            WHERE {where_clause}
        """
        
        # Main query with pagination
        query = f"""
            SELECT r.id, r.jurisdiction_id, r.title_id, r.user_id,
                   j.name as jurisdiction_name, j.level_name as jurisdiction_level,
                   t.title_name, t.abbreviation, t.level_rank, t.description,
                   r.created_at, r.updated_at
            FROM representatives r
            JOIN jurisdictions j ON r.jurisdiction_id = j.id
            JOIN titles t ON r.title_id = t.id
            WHERE {where_clause}
            ORDER BY j.level_rank ASC, t.level_rank ASC, t.title_name ASC
            LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        """
        
        params.extend([limit, offset])
        
        async with db_manager.get_connection() as conn:
            # Get total count
            total_row = await conn.fetchrow(count_query, *params[:-2])  # Exclude limit and offset
            total = total_row['total']
            
            # Get paginated results
            rows = await conn.fetch(query, *params)
            representatives = [dict(row) for row in rows]
            
        # Calculate pagination metadata
        total_pages = (total + limit - 1) // limit  # Ceiling division
        has_next = page < total_pages
        has_prev = page > 1
        
        result = {
            "representatives": representatives,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }
            
        logger.info(f"Retrieved {len(representatives)} of {total} available representatives (page {page})")
        return result
            
        # Remove generic Exception catch - let FastAPI handle unexpected errors
    
    async def get_representative_by_id(self, rep_id: UUID) -> Optional[Dict[str, Any]]:
        """Get representative by ID with full details"""
        query = """
            SELECT r.id, r.jurisdiction_id, r.title_id, r.user_id,
                   j.name as jurisdiction_name, j.level_name as jurisdiction_level,
                   t.title_name, t.abbreviation, t.level_rank, t.description,
                   r.created_at, r.updated_at
            FROM representatives r
            JOIN jurisdictions j ON r.jurisdiction_id = j.id
            JOIN titles t ON r.title_id = t.id
            WHERE r.id = $1
        """
        
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, rep_id)
            
        if not row:
            return None
            
        return dict(row)
        
        # Remove generic Exception catch - let FastAPI handle unexpected errors
    
    async def get_user_linked_representative(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get the representative account linked to a user with enhanced details"""
        query = """
            SELECT u.rep_accounts[1] as linked_rep_id
            FROM users u
            WHERE u.id = $1 AND u.rep_accounts IS NOT NULL AND array_length(u.rep_accounts, 1) > 0
        """

        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, user_id)
            
        if not row or not row['linked_rep_id']:
            return None
            
        # Get full representative details with title and jurisdiction info
        return await self.get_representative_with_details(row['linked_rep_id'])
    
    async def get_representative_with_details(self, rep_id: UUID) -> Optional[Dict[str, Any]]:
        """Get representative with complete title and jurisdiction information"""
        query = """
            SELECT 
                r.id as rep_id,
                r.user_id,
                r.created_at as rep_created_at,
                r.updated_at as rep_updated_at,
                -- Title information
                t.id as title_id,
                t.title_name,
                t.abbreviation,
                t.level_rank as title_level_rank,
                t.title_type,
                t.description as title_description,
                t.level as title_level,
                t.is_elected,
                t.term_length,
                t.status as title_status,
                t.created_at as title_created_at,
                t.updated_at as title_updated_at,
                -- Jurisdiction information
                j.id as jurisdiction_id,
                j.name as jurisdiction_name,
                j.level_name as jurisdiction_level_name,
                j.level_rank as jurisdiction_level_rank,
                j.parent_id as parent_jurisdiction_id
            FROM representatives r
            JOIN titles t ON r.title_id = t.id
            JOIN jurisdictions j ON r.jurisdiction_id = j.id
            WHERE r.id = $1
        """
        
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, rep_id)
            
        if not row:
            return None
            
        return {
            "id": row["rep_id"],
            "user_id": row["user_id"],
            "created_at": row["rep_created_at"],
            "updated_at": row["rep_updated_at"],
            "title_info": {
                "id": row["title_id"],
                "title_name": row["title_name"],
                "abbreviation": row["abbreviation"],
                "level_rank": row["title_level_rank"],
                "title_type": row["title_type"],
                "description": row["title_description"],
                "level": row["title_level"],
                "is_elected": row["is_elected"],
                "term_length": row["term_length"],
                "status": row["title_status"],
                "created_at": row["title_created_at"],
                "updated_at": row["title_updated_at"]
            },
            "jurisdiction_info": {
                "id": row["jurisdiction_id"],
                "name": row["jurisdiction_name"],
                "level_name": row["jurisdiction_level_name"],
                "level_rank": row["jurisdiction_level_rank"],
                "parent_jurisdiction_id": row["parent_jurisdiction_id"]
            }
        }
    
    async def get_user_rep_accounts(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get all representative accounts linked to a user"""
        query = """
            SELECT unnest(rep_accounts) as rep_id
            FROM users
            WHERE id = $1 AND rep_accounts IS NOT NULL
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, user_id)
        
        logger.info(f"Found {len(rows)} representative account IDs for user {user_id}")
        
        rep_accounts = []
        for row in rows:
            logger.info(f"Processing representative ID: {row['rep_id']}")
            rep_details = await self.get_representative_with_details(row['rep_id'])
            if rep_details:
                rep_accounts.append(rep_details)
                logger.info(f"Added representative details for ID: {row['rep_id']}")
            else:
                logger.warning(f"No details found for representative ID: {row['rep_id']}")
        
        logger.info(f"Returning {len(rep_accounts)} representative accounts for user {user_id}")
        return rep_accounts
    
    async def link_user_to_representative(self, user_id: UUID, rep_id: UUID) -> Dict[str, Any]:
        """Link a user account to a representative account"""
        async with db_manager.get_connection() as conn:
            async with conn.transaction():
                # Try to claim the representative account directly
                # This will fail if the rep is already claimed or doesn't exist
                updated_rows = await conn.execute("""
                    UPDATE representatives 
                    SET user_id = $1, updated_at = NOW() 
                    WHERE id = $2 AND user_id IS NULL
                """, user_id, rep_id)
                
                if updated_rows == "UPDATE 0":
                    raise HTTPException(
                        status_code=400, 
                        detail="Representative account not found or already claimed by another user"
                    )
                
                # Update user's rep_accounts by appending to existing array
                await conn.execute("""
                    UPDATE users 
                    SET rep_accounts = COALESCE(rep_accounts, ARRAY[]::UUID[]) || ARRAY[$2::UUID], 
                        updated_at = NOW()
                    WHERE id = $1
                """, user_id, rep_id)
        # Use existing service to get updated user information
        from app.services.user_service import UserService
        user_service = UserService()
        user_data = await user_service.get_user_by_id(user_id)
        
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found after linking")
        
        logger.info(f"Successfully linked user {user_id} to representative {rep_id}")
        return user_data
          
    
    async def unlink_user_from_representative(self, user_id: UUID) -> bool:
        """Unlink a user from their representative account"""
        # Get current linked representative
        current_rep = await self.get_user_linked_representative(user_id)
        if not current_rep:
            return True  # Already unlinked
        
        rep_id = UUID(current_rep['id'])
        
        async with db_manager.get_connection() as conn:
            async with conn.transaction():
                # Remove user_id from representatives table
                await conn.execute("""
                    UPDATE representatives 
                    SET user_id = NULL, updated_at = NOW() 
                    WHERE id = $1
                """, rep_id)
                
                # Clear the user's rep_accounts column
                await conn.execute("""
                    UPDATE users 
                    SET rep_accounts = NULL, updated_at = NOW()
                    WHERE id = $1
                """, user_id)
        
        logger.info(f"Successfully unlinked user {user_id} from representative {rep_id}")
        return True
        
        # Remove generic Exception catch - let FastAPI handle unexpected errors
    
    async def update_user_representative(self, user_id: UUID, new_rep_id: UUID) -> Dict[str, Any]:
        """Update user's linked representative (unlink from old, link to new)"""
        # First unlink from current representative
        await self.unlink_user_from_representative(user_id)
        
        # Then link to new representative
        return await self.link_user_to_representative(user_id, new_rep_id)
        
        # Remove generic Exception catch - let FastAPI handle unexpected errors

    async def get_available_titles(self) -> List[Dict[str, Any]]:
        """Get all available titles that have representatives"""
        query = """
            SELECT DISTINCT 
                t.id,
                t.title_name,
                t.abbreviation,
                t.level,
                COUNT(r.id) as available_count
            FROM titles t
            INNER JOIN representatives r ON r.title_id = t.id
            WHERE r.user_id IS NULL  -- Only unclaimed representative accounts
            GROUP BY t.id, t.title_name, t.abbreviation, t.level
            ORDER BY t.title_name
        """
        
        async with db_manager.get_connection() as conn:
            result = await conn.fetch(query)
            
            titles = []
            for row in result:
                titles.append({
                    "id": str(row["id"]),
                    "title_name": row["title_name"],
                    "abbreviation": row["abbreviation"],
                    "level": row["level"],
                    "available_count": row["available_count"]
                })
            
            logger.info(f"Retrieved {len(titles)} available titles")
            return titles
            
        # Remove generic Exception catch - let FastAPI handle unexpected errors

    async def get_jurisdiction_suggestions(
        self, 
        title_id: str, 
        query: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get jurisdiction suggestions based on title and search query"""
        search_query = """
            SELECT DISTINCT 
                j.id,
                j.name,
                j.level_name as level,
                COUNT(r.id) as available_count
            FROM jurisdictions j
            INNER JOIN representatives r ON r.jurisdiction_id = j.id
            WHERE r.title_id = $1
              AND r.user_id IS NULL  -- Only unclaimed representative accounts
              AND LOWER(j.name) LIKE LOWER($2)
            GROUP BY j.id, j.name, j.level_name
            ORDER BY j.name
            LIMIT $3
        """
        
        async with db_manager.get_connection() as conn:
            result = await conn.fetch(
                search_query, 
                UUID(title_id), 
                f"%{query}%", 
                limit
            )
            
            jurisdictions = []
            for row in result:
                jurisdictions.append({
                    "id": str(row["id"]),
                    "name": row["name"],
                    "level": row["level"],
                    "abbreviation": None,  # No abbreviation column in jurisdictions table
                    "available_count": row["available_count"]
                })
            
            logger.info(f"Retrieved {len(jurisdictions)} jurisdiction suggestions for title {title_id} with query '{query}'")
            return jurisdictions
            
        # Remove generic Exception catch - let FastAPI handle unexpected errors

    async def get_representatives_by_title_and_jurisdiction(
        self, 
        title_id: str, 
        jurisdiction_id: str
    ) -> List[Dict[str, Any]]:
        """Get available representatives for specific title and jurisdiction"""
        query = """
            SELECT 
                r.id,
                t.title_name,
                t.abbreviation as title_abbreviation,
                j.name as jurisdiction_name,
                j.level_name as jurisdiction_level
            FROM representatives r
            INNER JOIN titles t ON r.title_id = t.id
            INNER JOIN jurisdictions j ON r.jurisdiction_id = j.id
            WHERE r.title_id = $1
              AND r.jurisdiction_id = $2
              AND r.user_id IS NULL  -- Only unclaimed representative accounts
            ORDER BY r.id
        """
        
        async with db_manager.get_connection() as conn:
            result = await conn.fetch(query, UUID(title_id), UUID(jurisdiction_id))
            
            representatives = []
            for row in result:
                representatives.append({
                    "id": str(row["id"]),
                    "description": None,  # No description column in database
                    "title_name": row["title_name"],
                    "title_abbreviation": row["title_abbreviation"],
                    "jurisdiction_name": row["jurisdiction_name"],
                    "jurisdiction_level": row["jurisdiction_level"],
                    "jurisdiction_abbreviation": None  # No abbreviation column in jurisdictions table
                })
            
            logger.info(f"Retrieved {len(representatives)} representatives for title {title_id} and jurisdiction {jurisdiction_id}")
            return representatives
            
        # Remove generic Exception catch - let FastAPI handle unexpected errors
