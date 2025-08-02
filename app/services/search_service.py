"""
Search Service for CivicPulse Platform
Provides unified search functionality across users, posts, and representatives
with full-text search, fuzzy matching, and relevance scoring.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from fastapi import HTTPException

from app.services.db_service import DatabaseService
from app.services.search_formatter import SearchResultFormatter, SearchResultAggregator, SearchPaginator, SearchHighlighter
from app.services.search_suggestions import SearchSuggestionService, PopularTermsAnalyzer

logger = logging.getLogger(__name__)


class SearchService:
    """
    Core search service providing unified search across all entities.
    Supports full-text search, fuzzy matching, filtering, and analytics.
    """
    
    def __init__(self):
        self.db_service = DatabaseService()
        self.suggestion_service = SearchSuggestionService()
        self.popular_terms_analyzer = PopularTermsAnalyzer()
    
    async def unified_search(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "relevance",
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Perform unified search across users, posts, and representatives.
        
        Args:
            query: Search query string
            entity_types: List of entity types to search ['users', 'posts', 'representatives']
            limit: Maximum results per entity type
            offset: Pagination offset
            filters: Additional filters (location, tags, verified, etc.)
            sort_by: Sort criteria ('relevance', 'recent', 'popular')
            user_id: ID of requesting user for personalization
        
        Returns:
            Dict containing search results, metadata, and suggestions
        """
        if not query or len(query.strip()) < 2:
            raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
        
        # Default to all entity types if not specified
        if not entity_types:
            entity_types = ['users', 'posts', 'representatives']
        
        # Clean and prepare search query
        cleaned_query = self._clean_search_query(query)
        search_terms = self._extract_search_terms(cleaned_query)
        
        # Log search analytics
        await self._log_search_analytics(cleaned_query, entity_types, user_id)
        
        try:
            async with self.db_service.get_connection_with_retry() as conn:
                # Execute searches in parallel for better performance
                search_tasks = []
                
                if 'users' in entity_types:
                    search_tasks.append(self._search_users(conn, search_terms, limit, offset, filters, sort_by))
                
                if 'posts' in entity_types:
                    search_tasks.append(self._search_posts(conn, search_terms, limit, offset, filters, sort_by))
                
                if 'representatives' in entity_types:
                    search_tasks.append(self._search_representatives(conn, search_terms, limit, offset, filters, sort_by))
                
                # Execute all searches concurrently
                search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
                
                # Process results
                results = {}
                entity_index = 0
                
                if 'users' in entity_types:
                    results['users'] = search_results[entity_index] if not isinstance(search_results[entity_index], Exception) else []
                    entity_index += 1
                
                if 'posts' in entity_types:
                    results['posts'] = search_results[entity_index] if not isinstance(search_results[entity_index], Exception) else []
                    entity_index += 1
                
                if 'representatives' in entity_types:
                    results['representatives'] = search_results[entity_index] if not isinstance(search_results[entity_index], Exception) else []
                    entity_index += 1
                
                # Get search suggestions
                suggestions = await self.suggestion_service.get_suggestions(
                    cleaned_query, 
                    suggestion_types=['popular', 'similar', 'autocomplete'],
                    limit=5,
                    user_id=user_id
                )
                
                # Format and aggregate results
                formatted_results = SearchResultFormatter.format_search_results(results)
                
                # Apply highlighting if requested
                if filters and filters.get('highlight', True):
                    formatted_results = SearchHighlighter.highlight_results(
                        formatted_results, search_terms
                    )
                
                # Aggregate results with metadata
                aggregated_data = SearchResultAggregator.aggregate_results(
                    formatted_results,
                    cleaned_query,
                    {
                        'entity_types': entity_types,
                        'limit': limit,
                        'offset': offset,
                        'sort_by': sort_by,
                        'search_time': datetime.now(timezone.utc).isoformat(),
                        'filters_applied': filters or {}
                    }
                )
                
                # Apply pagination
                paginated_data = SearchPaginator.paginate_results(
                    aggregated_data['results'],
                    limit,
                    offset
                )
                
                return {
                    'query': cleaned_query,
                    'results': paginated_data['results'],
                    'suggestions': suggestions.get('suggestions', {}),
                    'entity_suggestions': suggestions.get('entity_suggestions', {}),
                    'aggregation': aggregated_data['aggregation'],
                    'query_analysis': aggregated_data['query_analysis'],
                    'pagination': paginated_data['pagination'],
                    'metadata': aggregated_data['search_metadata']
                }
                
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            raise HTTPException(status_code=500, detail="Search service temporarily unavailable")
    
    async def _search_users(
        self,
        conn,
        search_terms: List[str],
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
        sort_by: str
    ) -> List[Dict[str, Any]]:
        """Search users with full-text and fuzzy matching."""
        
        # Build search query
        tsquery = " | ".join(f"'{term}':*" for term in search_terms)
        similarity_conditions = " OR ".join(f"username % '{term}' OR display_name % '{term}'" for term in search_terms)
        
        # Base query with relevance scoring
        base_query = """
        SELECT 
            u.id,
            u.username,
            u.display_name,
            u.bio,
            u.avatar_url,
            u.is_verified,
            u.followers_count,
            u.following_count,
            u.created_at,
            -- Relevance scoring
            CASE 
                WHEN u.search_vector @@ to_tsquery('english', $1) THEN
                    ts_rank(u.search_vector, to_tsquery('english', $1)) * 10
                ELSE 0
            END +
            CASE 
                WHEN {similarity_conditions} THEN
                    (similarity(u.username, $2) + similarity(u.display_name, $2)) * 5
                ELSE 0
            END +
            -- Boost verified users
            CASE WHEN u.is_verified THEN 2 ELSE 0 END +
            -- Boost by follower count (normalized)
            LOG(GREATEST(u.followers_count, 1)) * 0.1
            AS relevance_score
        FROM users u
        WHERE 
            u.is_active = true
            AND (
                u.search_vector @@ to_tsquery('english', $1)
                OR {similarity_conditions}
            )
        """.format(similarity_conditions=similarity_conditions)
        
        # Add filters
        filter_conditions = []
        params = [tsquery, search_terms[0] if search_terms else ""]
        param_count = 2
        
        if filters:
            if filters.get('verified'):
                filter_conditions.append("AND u.is_verified = true")
            
            if filters.get('min_followers'):
                param_count += 1
                filter_conditions.append(f"AND u.followers_count >= ${param_count}")
                params.append(filters['min_followers'])
        
        # Add filter conditions to query
        if filter_conditions:
            base_query += " " + " ".join(filter_conditions)
        
        # Add sorting
        if sort_by == "relevance":
            base_query += " ORDER BY relevance_score DESC, u.followers_count DESC"
        elif sort_by == "recent":
            base_query += " ORDER BY u.created_at DESC"
        elif sort_by == "popular":
            base_query += " ORDER BY u.followers_count DESC, relevance_score DESC"
        
        # Add pagination
        param_count += 1
        base_query += f" LIMIT ${param_count}"
        params.append(limit)
        
        param_count += 1
        base_query += f" OFFSET ${param_count}"
        params.append(offset)
        
        try:
            rows = await conn.fetch(base_query, *params)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"User search failed: {e}")
            return []
    
    async def _search_posts(
        self,
        conn,
        search_terms: List[str],
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
        sort_by: str
    ) -> List[Dict[str, Any]]:
        """Search posts with full-text and fuzzy matching."""
        
        # Build search query
        tsquery = " | ".join(f"'{term}':*" for term in search_terms)
        similarity_conditions = " OR ".join(
            f"title % '{term}' OR content % '{term}' OR location % '{term}'" 
            for term in search_terms
        )
        
        # Base query with relevance scoring
        base_query = """
        SELECT 
            p.id,
            p.title,
            p.content,
            p.post_type,
            p.status,
            p.location,
            p.tags,
            p.upvotes,
            p.downvotes,
            p.comment_count,
            p.created_at,
            p.last_activity_at,
            p.media_urls,
            p.assignee,
            u.username as author_username,
            u.display_name as author_display_name,
            u.avatar_url as author_avatar_url,
            u.is_verified as author_verified,
            -- Relevance scoring
            CASE 
                WHEN p.search_vector @@ to_tsquery('english', $1) THEN
                    ts_rank(p.search_vector, to_tsquery('english', $1)) * 10
                ELSE 0
            END +
            CASE 
                WHEN {similarity_conditions} THEN
                    (similarity(p.title, $2) * 3 + similarity(p.content, $2) * 2 + similarity(p.location, $2)) * 2
                ELSE 0
            END +
            -- Boost by engagement
            LOG(GREATEST(p.upvotes - p.downvotes + p.comment_count, 1)) * 0.5 +
            -- Recent activity boost
            CASE 
                WHEN p.last_activity_at > NOW() - INTERVAL '7 days' THEN 1
                WHEN p.last_activity_at > NOW() - INTERVAL '30 days' THEN 0.5
                ELSE 0
            END
            AS relevance_score
        FROM posts p
        JOIN users u ON p.user_id = u.id
        WHERE 
            p.status IN ('open', 'in_progress', 'resolved')
            AND (
                p.search_vector @@ to_tsquery('english', $1)
                OR {similarity_conditions}
            )
        """.format(similarity_conditions=similarity_conditions)
        
        # Add filters
        filter_conditions = []
        params = [tsquery, search_terms[0] if search_terms else ""]
        param_count = 2
        
        if filters:
            if filters.get('post_type'):
                param_count += 1
                filter_conditions.append(f"AND p.post_type = ${param_count}")
                params.append(filters['post_type'])
            
            if filters.get('status'):
                param_count += 1
                filter_conditions.append(f"AND p.status = ${param_count}")
                params.append(filters['status'])
            
            if filters.get('location'):
                param_count += 1
                filter_conditions.append(f"AND p.location ILIKE ${param_count}")
                params.append(f"%{filters['location']}%")
            
            if filters.get('tags'):
                param_count += 1
                filter_conditions.append(f"AND p.tags && ${param_count}")
                params.append(filters['tags'])
            
            if filters.get('min_upvotes'):
                param_count += 1
                filter_conditions.append(f"AND p.upvotes >= ${param_count}")
                params.append(filters['min_upvotes'])
        
        # Add filter conditions to query
        if filter_conditions:
            base_query += " " + " ".join(filter_conditions)
        
        # Add sorting
        if sort_by == "relevance":
            base_query += " ORDER BY relevance_score DESC, p.last_activity_at DESC"
        elif sort_by == "recent":
            base_query += " ORDER BY p.created_at DESC"
        elif sort_by == "popular":
            base_query += " ORDER BY (p.upvotes - p.downvotes + p.comment_count) DESC, relevance_score DESC"
        
        # Add pagination
        param_count += 1
        base_query += f" LIMIT ${param_count}"
        params.append(limit)
        
        param_count += 1
        base_query += f" OFFSET ${param_count}"
        params.append(offset)
        
        try:
            rows = await conn.fetch(base_query, *params)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Post search failed: {e}")
            return []
    
    async def _search_representatives(
        self,
        conn,
        search_terms: List[str],
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
        sort_by: str
    ) -> List[Dict[str, Any]]:
        """Search representatives with full-text and fuzzy matching."""
        
        # Build search query
        tsquery = " | ".join(f"'{term}':*" for term in search_terms)
        similarity_conditions = " OR ".join(
            f"cached_name % '{term}' OR cached_designation % '{term}' OR cached_constituency % '{term}' OR party % '{term}'" 
            for term in search_terms
        )
        
        # Base query with relevance scoring
        base_query = """
        SELECT 
            r.id,
            r.cached_name as name,
            r.cached_designation as designation,
            r.cached_constituency as constituency,
            r.party,
            r.is_verified,
            r.contact_email,
            r.avatar_url,
            r.user_id,
            r.created_at,
            u.username as linked_username,
            u.display_name as linked_display_name,
            -- Relevance scoring
            CASE 
                WHEN r.search_vector @@ to_tsquery('english', $1) THEN
                    ts_rank(r.search_vector, to_tsquery('english', $1)) * 10
                ELSE 0
            END +
            CASE 
                WHEN {similarity_conditions} THEN
                    (similarity(r.cached_name, $2) * 4 + 
                     similarity(r.cached_designation, $2) * 3 + 
                     similarity(r.cached_constituency, $2) * 2 +
                     similarity(r.party, $2)) * 2
                ELSE 0
            END +
            -- Boost verified representatives
            CASE WHEN r.is_verified THEN 3 ELSE 0 END +
            -- Boost linked representatives
            CASE WHEN r.user_id IS NOT NULL THEN 2 ELSE 0 END
            AS relevance_score
        FROM representatives r
        LEFT JOIN users u ON r.user_id = u.id
        WHERE 
            (
                r.search_vector @@ to_tsquery('english', $1)
                OR {similarity_conditions}
            )
        """.format(similarity_conditions=similarity_conditions)
        
        # Add filters
        filter_conditions = []
        params = [tsquery, search_terms[0] if search_terms else ""]
        param_count = 2
        
        if filters:
            if filters.get('verified'):
                filter_conditions.append("AND r.is_verified = true")
            
            if filters.get('party'):
                param_count += 1
                filter_conditions.append(f"AND r.party ILIKE ${param_count}")
                params.append(f"%{filters['party']}%")
            
            if filters.get('constituency'):
                param_count += 1
                filter_conditions.append(f"AND r.cached_constituency ILIKE ${param_count}")
                params.append(f"%{filters['constituency']}%")
            
            if filters.get('linked_only'):
                filter_conditions.append("AND r.user_id IS NOT NULL")
        
        # Add filter conditions to query
        if filter_conditions:
            base_query += " " + " ".join(filter_conditions)
        
        # Add sorting
        if sort_by == "relevance":
            base_query += " ORDER BY relevance_score DESC, r.is_verified DESC"
        elif sort_by == "recent":
            base_query += " ORDER BY r.created_at DESC"
        elif sort_by == "popular":
            base_query += " ORDER BY r.is_verified DESC, relevance_score DESC"
        
        # Add pagination
        param_count += 1
        base_query += f" LIMIT ${param_count}"
        params.append(limit)
        
        param_count += 1
        base_query += f" OFFSET ${param_count}"
        params.append(offset)
        
        try:
            rows = await conn.fetch(base_query, *params)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Representative search failed: {e}")
            return []
    
    async def _get_search_suggestions(
        self,
        conn,
        query: str
    ) -> List[str]:
        """Get search suggestions based on popular searches and query similarity."""
        try:
            # Get popular search terms similar to current query
            suggestions_query = """
            SELECT DISTINCT query
            FROM search_analytics
            WHERE similarity(query, $1) > 0.3
                AND query != $1
                AND search_count > 1
            ORDER BY search_count DESC, similarity(query, $1) DESC
            LIMIT 5
            """
            
            rows = await conn.fetch(suggestions_query, query)
            suggestions = [row['query'] for row in rows]
            
            # If we don't have enough suggestions, add some based on search terms
            if len(suggestions) < 3:
                # Get common search terms from suggestions table
                common_terms_query = """
                SELECT suggestion
                FROM search_suggestions
                WHERE suggestion ILIKE $1
                ORDER BY usage_count DESC
                LIMIT 3
                """
                
                term_rows = await conn.fetch(common_terms_query, f"%{query}%")
                for row in term_rows:
                    if row['suggestion'] not in suggestions:
                        suggestions.append(row['suggestion'])
            
            return suggestions[:5]
            
        except Exception as e:
            logger.error(f"Failed to get search suggestions: {e}")
            return []
    
    async def _log_search_analytics(
        self,
        query: str,
        entity_types: List[str],
        user_id: Optional[int]
    ):
        """Log search analytics for improving search experience."""
        try:
            async with self.db_service.get_connection_with_retry() as conn:
                # Convert entity_types list to a single search_type string
                search_type = ','.join(entity_types) if entity_types else 'all'
                
                # Insert search analytics (simpler approach for existing schema)
                analytics_query = """
                INSERT INTO search_analytics (query, search_type, user_id, result_count)
                VALUES ($1, $2, $3, 0)
                """
                
                await conn.execute(analytics_query, query, search_type, user_id)
                
                # Update search suggestions for individual terms
                terms = self._extract_search_terms(query)
                for term in terms:
                    if len(term) >= 3:  # Only store meaningful terms
                        suggestion_query = """
                        INSERT INTO search_suggestions (suggestion, category, search_count, last_searched_at)
                        VALUES ($1, 'recent', 1, NOW())
                        ON CONFLICT (suggestion)
                        DO UPDATE SET 
                            search_count = search_suggestions.search_count + 1,
                            last_searched_at = NOW()
                        """
                        await conn.execute(suggestion_query, term)
                        
        except Exception as e:
            logger.error(f"Failed to log search analytics: {e}")
            # Don't raise exception as this is not critical for search functionality
    
    def _clean_search_query(self, query: str) -> str:
        """Clean and normalize search query."""
        # Remove extra whitespace and convert to lowercase
        cleaned = " ".join(query.strip().lower().split())
        
        # Remove special characters that might interfere with search
        special_chars = ['(', ')', '[', ']', '{', '}', '&', '|', '!', '@', '#', '%', '^', '*']
        for char in special_chars:
            cleaned = cleaned.replace(char, ' ')
        
        # Remove extra spaces again
        cleaned = " ".join(cleaned.split())
        
        return cleaned
    
    def _extract_search_terms(self, query: str) -> List[str]:
        """Extract meaningful search terms from query."""
        # Split by whitespace and filter out short terms
        terms = [term.strip() for term in query.split() if len(term.strip()) >= 2]
        
        # Remove common stop words that don't add search value
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
        terms = [term for term in terms if term.lower() not in stop_words]
        
        return terms[:10]  # Limit to 10 terms for performance
    
    async def get_search_suggestions(
        self,
        partial_query: str,
        suggestion_types: Optional[List[str]] = None,
        limit: int = 10,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get search suggestions for autocomplete functionality."""
        return await self.suggestion_service.get_suggestions(
            partial_query, suggestion_types, limit, user_id
        )
    
    async def get_popular_terms_analysis(
        self,
        time_period: str = "7d",
        entity_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get popular search terms analysis."""
        return await self.popular_terms_analyzer.get_popular_terms_analysis(
            time_period, entity_types, limit
        )
    
    async def advanced_search(
        self,
        query_components: Dict[str, Any],
        entity_types: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "relevance",
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Perform advanced search with structured query components.
        
        Args:
            query_components: Dict with keys like 'title', 'content', 'author', 'location', etc.
            entity_types: List of entity types to search
            limit: Results limit per entity type
            offset: Pagination offset
            sort_by: Sort criteria
            user_id: User ID for personalization
        
        Returns:
            Advanced search results with detailed matching
        """
        # Build complex query from components
        query_parts = []
        filters = {}
        
        if query_components.get('text'):
            query_parts.append(query_components['text'])
        
        if query_components.get('author'):
            filters['author'] = query_components['author']
        
        if query_components.get('location'):
            filters['location'] = query_components['location']
        
        if query_components.get('tags'):
            filters['tags'] = query_components['tags']
        
        if query_components.get('date_range'):
            filters['date_range'] = query_components['date_range']
        
        # Combine query parts
        combined_query = " ".join(query_parts) if query_parts else ""
        
        # Use unified search with advanced filters
        return await self.unified_search(
            combined_query,
            entity_types,
            limit,
            offset,
            filters,
            sort_by,
            user_id
        )
    
    async def search_similar_content(
        self,
        content_id: int,
        content_type: str,
        limit: int = 10,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Find content similar to a given piece of content.
        
        Args:
            content_id: ID of the reference content
            content_type: Type of content ('post', 'user', 'representative')
            limit: Maximum similar items to return
            user_id: User ID for personalization
        
        Returns:
            Similar content results
        """
        try:
            async with self.db_service.get_connection_with_retry() as conn:
                # Get the reference content to extract features
                reference_content = await self._get_reference_content(
                    conn, content_id, content_type
                )
                
                if not reference_content:
                    return {'similar_content': [], 'metadata': {'error': 'Reference content not found'}}
                
                # Extract search terms from reference content
                search_terms = self._extract_similarity_terms(reference_content, content_type)
                
                # Perform similarity search
                similar_items = await self._find_similar_items(
                    conn, search_terms, content_type, content_id, limit
                )
                
                # Format results
                formatted_similar = self._format_similar_results(similar_items, content_type)
                
                return {
                    'reference_content': reference_content,
                    'similar_content': formatted_similar,
                    'metadata': {
                        'content_type': content_type,
                        'similarity_algorithm': 'vector_similarity',
                        'search_terms_used': len(search_terms),
                        'generated_at': datetime.now(timezone.utc).isoformat()
                    }
                }
                
        except Exception as e:
            logger.error(f"Similar content search failed: {e}")
            return {'similar_content': [], 'metadata': {'error': str(e)}}
    
    async def _get_reference_content(self, conn, content_id: int, content_type: str):
        """Get reference content for similarity search."""
        if content_type == 'post':
            query = """
            SELECT id, title, content, tags, location, post_type
            FROM posts WHERE id = $1
            """
        elif content_type == 'user':
            query = """
            SELECT id, username, display_name, bio, location
            FROM users WHERE id = $1
            """
        elif content_type == 'representative':
            query = """
            SELECT id, cached_name, cached_designation, cached_constituency, party
            FROM representatives WHERE id = $1
            """
        else:
            return None
        
        try:
            row = await conn.fetchrow(query, content_id)
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get reference content: {e}")
            return None
    
    def _extract_similarity_terms(self, content: Dict[str, Any], content_type: str) -> List[str]:
        """Extract key terms from content for similarity search."""
        terms = []
        
        if content_type == 'post':
            if content.get('title'):
                terms.extend(content['title'].split())
            if content.get('content'):
                # Extract key phrases from content (simplified)
                words = content['content'].split()
                terms.extend(words[:20])  # First 20 words
            if content.get('tags'):
                terms.extend(content['tags'])
        
        elif content_type == 'user':
            if content.get('display_name'):
                terms.extend(content['display_name'].split())
            if content.get('bio'):
                terms.extend(content['bio'].split()[:10])
        
        elif content_type == 'representative':
            if content.get('cached_name'):
                terms.extend(content['cached_name'].split())
            if content.get('cached_designation'):
                terms.extend(content['cached_designation'].split())
            if content.get('party'):
                terms.extend(content['party'].split())
        
        # Clean and filter terms
        cleaned_terms = []
        for term in terms:
            cleaned = self._clean_search_query(term)
            if len(cleaned) >= 3:
                cleaned_terms.append(cleaned)
        
        return list(set(cleaned_terms))[:10]  # Unique terms, max 10
    
    async def _find_similar_items(
        self, 
        conn, 
        search_terms: List[str], 
        content_type: str, 
        exclude_id: int, 
        limit: int
    ):
        """Find items similar to the reference content."""
        tsquery = " | ".join(f"'{term}':*" for term in search_terms)
        
        if content_type == 'post':
            query = """
            SELECT 
                id, title, content, post_type, tags, upvotes, created_at,
                ts_rank(search_vector, to_tsquery('english', $1)) as similarity_score
            FROM posts
            WHERE search_vector @@ to_tsquery('english', $1)
                AND id != $2
                AND status = 'active'
            ORDER BY similarity_score DESC
            LIMIT $3
            """
        elif content_type == 'user':
            query = """
            SELECT 
                id, username, display_name, bio, is_verified, followers_count,
                ts_rank(search_vector, to_tsquery('english', $1)) as similarity_score
            FROM users
            WHERE search_vector @@ to_tsquery('english', $1)
                AND id != $2
                AND is_active = true
            ORDER BY similarity_score DESC
            LIMIT $3
            """
        elif content_type == 'representative':
            query = """
            SELECT 
                id, cached_name, cached_designation, cached_constituency, party, is_verified,
                ts_rank(search_vector, to_tsquery('english', $1)) as similarity_score
            FROM representatives
            WHERE search_vector @@ to_tsquery('english', $1)
                AND id != $2
            ORDER BY similarity_score DESC
            LIMIT $3
            """
        else:
            return []
        
        try:
            rows = await conn.fetch(query, tsquery, exclude_id, limit)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Similar items search failed: {e}")
            return []
    
    def _format_similar_results(self, items: List[Dict], content_type: str) -> List[Dict]:
        """Format similar items results."""
        if content_type == 'post':
            return [SearchResultFormatter.format_post_result(item) for item in items]
        elif content_type == 'user':
            return [SearchResultFormatter.format_user_result(item) for item in items]
        elif content_type == 'representative':
            return [SearchResultFormatter.format_representative_result(item) for item in items]
        else:
            return items
