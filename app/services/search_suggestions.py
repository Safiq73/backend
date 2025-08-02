"""
Search Suggestions and Popular Terms Module
Provides intelligent search suggestions, autocomplete, and trending search analytics
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone, timedelta
from collections import Counter
import re

from app.services.db_service import DatabaseService

logger = logging.getLogger(__name__)


class SearchSuggestionService:
    """Service for generating intelligent search suggestions."""
    
    def __init__(self):
        self.db_service = DatabaseService()
    
    async def get_suggestions(
        self,
        partial_query: str,
        suggestion_types: Optional[List[str]] = None,
        limit: int = 10,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive search suggestions based on partial query.
        
        Args:
            partial_query: Partial search query for suggestions
            suggestion_types: Types of suggestions to return ['popular', 'recent', 'similar', 'autocomplete']
            limit: Maximum number of suggestions per type
            user_id: User ID for personalized suggestions
        
        Returns:
            Dict containing different types of suggestions
        """
        if not partial_query or len(partial_query.strip()) < 2:
            return await self._get_trending_suggestions(limit, user_id)
        
        # Default to all suggestion types if not specified
        if not suggestion_types:
            suggestion_types = ['popular', 'recent', 'similar', 'autocomplete']
        
        cleaned_query = self._clean_query(partial_query)
        
        try:
            async with self.db_service.get_connection_with_retry() as conn:
                suggestions = {}
                
                if 'popular' in suggestion_types:
                    suggestions['popular'] = await self._get_popular_suggestions(
                        conn, cleaned_query, limit
                    )
                
                if 'recent' in suggestion_types:
                    suggestions['recent'] = await self._get_recent_suggestions(
                        conn, cleaned_query, limit, user_id
                    )
                
                if 'similar' in suggestion_types:
                    suggestions['similar'] = await self._get_similar_suggestions(
                        conn, cleaned_query, limit
                    )
                
                if 'autocomplete' in suggestion_types:
                    suggestions['autocomplete'] = await self._get_autocomplete_suggestions(
                        conn, cleaned_query, limit
                    )
                
                # Get entity-specific suggestions
                entity_suggestions = await self._get_entity_suggestions(conn, cleaned_query, limit)
                
                return {
                    'query': cleaned_query,
                    'suggestions': suggestions,
                    'entity_suggestions': entity_suggestions,
                    'metadata': {
                        'suggestion_count': sum(len(suggs) for suggs in suggestions.values()),
                        'generated_at': datetime.now(timezone.utc).isoformat()
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get search suggestions: {e}")
            return {'suggestions': {}, 'entity_suggestions': {}, 'metadata': {}}
    
    async def _get_popular_suggestions(
        self,
        conn,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get popular search suggestions based on search analytics."""
        try:
            popular_query = """
            SELECT 
                sa.query,
                COUNT(*) as total_searches,
                MAX(sa.created_at) as last_searched,
                COUNT(DISTINCT sa.user_id) as unique_searchers,
                similarity(sa.query, $1) as similarity_score
            FROM search_analytics sa
            WHERE 
                similarity(sa.query, $1) > 0.3
                AND sa.query != $1
                AND sa.created_at > NOW() - INTERVAL '30 days'
            GROUP BY sa.query
            HAVING COUNT(*) > 2
            ORDER BY total_searches DESC, similarity_score DESC
            LIMIT $2
            """
            
            rows = await conn.fetch(popular_query, query, limit)
            
            return [
                {
                    'suggestion': row['query'],
                    'type': 'popular',
                    'total_searches': row['total_searches'],
                    'unique_searchers': row['unique_searchers'],
                    'last_searched': row['last_searched'],
                    'similarity_score': float(row['similarity_score']),
                    'confidence': min(float(row['total_searches']) / 10.0, 1.0)
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Failed to get popular suggestions: {e}")
            return []
    
    async def _get_recent_suggestions(
        self,
        conn,
        query: str,
        limit: int,
        user_id: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Get recent search suggestions, optionally personalized."""
        try:
            if user_id:
                # Get user's recent searches
                recent_query = """
                SELECT DISTINCT
                    sa.query,
                    sa.created_at as last_searched_at,
                    1 as search_count,
                    similarity(sa.query, $1) as similarity_score
                FROM search_analytics sa
                WHERE 
                    sa.user_id = $3
                    AND similarity(sa.query, $1) > 0.2
                    AND sa.query != $1
                    AND sa.created_at > NOW() - INTERVAL '7 days'
                ORDER BY sa.created_at DESC, similarity_score DESC
                LIMIT $2
                """
                rows = await conn.fetch(recent_query, query, limit, user_id)
            else:
                # Get globally recent searches
                recent_query = """
                SELECT 
                    sa.query,
                    MAX(sa.created_at) as last_searched,
                    COUNT(*) as total_searches,
                    similarity(sa.query, $1) as similarity_score
                FROM search_analytics sa
                WHERE 
                    similarity(sa.query, $1) > 0.3
                    AND sa.query != $1
                    AND sa.created_at > NOW() - INTERVAL '24 hours'
                GROUP BY sa.query
                ORDER BY last_searched DESC, similarity_score DESC
                LIMIT $2
                """
                rows = await conn.fetch(recent_query, query, limit)
            
            return [
                {
                    'suggestion': row['query'],
                    'type': 'recent',
                    'last_searched': row['last_searched'] if 'last_searched' in row else row['last_searched_at'],
                    'search_count': row.get('search_count', row.get('total_searches', 0)),
                    'similarity_score': float(row['similarity_score']),
                    'confidence': float(row['similarity_score']) * 0.8  # Recent gets lower confidence
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Failed to get recent suggestions: {e}")
            return []
    
    async def _get_similar_suggestions(
        self,
        conn,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get similar search suggestions using fuzzy matching."""
        try:
            similar_query = """
            SELECT DISTINCT
                ss.suggestion,
                ss.search_count as usage_count,
                ss.last_searched_at as last_used_at,
                similarity(ss.suggestion, $1) as similarity_score,
                levenshtein(ss.suggestion, $1) as edit_distance
            FROM search_suggestions ss
            WHERE 
                similarity(ss.suggestion, $1) > 0.4
                AND ss.suggestion != $1
                AND ss.search_count > 1
            ORDER BY similarity_score DESC, usage_count DESC
            LIMIT $2
            """
            
            rows = await conn.fetch(similar_query, query, limit)
            
            return [
                {
                    'suggestion': row['suggestion'],
                    'type': 'similar',
                    'usage_count': row['usage_count'],
                    'last_used': row['last_used_at'],
                    'similarity_score': float(row['similarity_score']),
                    'edit_distance': row['edit_distance'],
                    'confidence': float(row['similarity_score']) * 0.9
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Failed to get similar suggestions: {e}")
            return []
    
    async def _get_autocomplete_suggestions(
        self,
        conn,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get autocomplete suggestions based on prefix matching."""
        try:
            # Get suggestions that start with the query
            autocomplete_query = """
            SELECT 
                ss.suggestion,
                ss.search_count as usage_count,
                ss.last_searched_at as last_used_at,
                LENGTH(ss.suggestion) as suggestion_length
            FROM search_suggestions ss
            WHERE 
                ss.suggestion ILIKE $1 || '%'
                AND ss.suggestion != $1
                AND ss.search_count > 0
            ORDER BY ss.search_count DESC, suggestion_length ASC
            LIMIT $2
            """
            
            rows = await conn.fetch(autocomplete_query, query, limit)
            
            return [
                {
                    'suggestion': row['suggestion'],
                    'type': 'autocomplete',
                    'usage_count': row['usage_count'],
                    'last_used': row['last_used_at'],
                    'completion_length': row['suggestion_length'] - len(query),
                    'confidence': min(float(row['usage_count']) / 5.0, 1.0)
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Failed to get autocomplete suggestions: {e}")
            return []
    
    async def _get_entity_suggestions(
        self,
        conn,
        query: str,
        limit: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get entity-specific suggestions from actual data."""
        entity_suggestions = {}
        
        try:
            # User suggestions
            user_suggestions = await self._get_user_name_suggestions(conn, query, limit)
            if user_suggestions:
                entity_suggestions['users'] = user_suggestions
            
            # Representative suggestions
            rep_suggestions = await self._get_representative_name_suggestions(conn, query, limit)
            if rep_suggestions:
                entity_suggestions['representatives'] = rep_suggestions
            
            # Location suggestions
            location_suggestions = await self._get_location_suggestions(conn, query, limit)
            if location_suggestions:
                entity_suggestions['locations'] = location_suggestions
            
            # Tag suggestions
            tag_suggestions = await self._get_tag_suggestions(conn, query, limit)
            if tag_suggestions:
                entity_suggestions['tags'] = tag_suggestions
            
        except Exception as e:
            logger.error(f"Failed to get entity suggestions: {e}")
        
        return entity_suggestions
    
    async def _get_user_name_suggestions(self, conn, query: str, limit: int) -> List[Dict[str, Any]]:
        """Get user name suggestions."""
        try:
            user_query = """
            SELECT DISTINCT
                u.username,
                u.display_name,
                u.is_verified,
                u.followers_count,
                GREATEST(
                    similarity(u.username, $1),
                    similarity(u.display_name, $1)
                ) as similarity_score
            FROM users u
            WHERE 
                (u.username ILIKE $1 || '%' OR u.display_name ILIKE $1 || '%')
                AND u.is_active = true
            ORDER BY similarity_score DESC, u.followers_count DESC
            LIMIT $2
            """
            
            rows = await conn.fetch(user_query, query, limit)
            
            return [
                {
                    'suggestion': row['username'],
                    'display_name': row['display_name'],
                    'type': 'user',
                    'is_verified': row['is_verified'],
                    'followers_count': row['followers_count'],
                    'similarity_score': float(row['similarity_score'])
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Failed to get user suggestions: {e}")
            return []
    
    async def _get_representative_name_suggestions(self, conn, query: str, limit: int) -> List[Dict[str, Any]]:
        """Get representative name suggestions."""
        try:
            rep_query = """
            SELECT DISTINCT
                r.cached_name,
                r.cached_designation,
                r.cached_constituency,
                r.party,
                r.is_verified,
                GREATEST(
                    similarity(r.cached_name, $1),
                    similarity(r.cached_designation, $1),
                    similarity(r.cached_constituency, $1)
                ) as similarity_score
            FROM representatives r
            WHERE 
                (r.cached_name ILIKE $1 || '%' 
                 OR r.cached_designation ILIKE $1 || '%' 
                 OR r.cached_constituency ILIKE $1 || '%')
            ORDER BY similarity_score DESC, r.is_verified DESC
            LIMIT $2
            """
            
            rows = await conn.fetch(rep_query, query, limit)
            
            return [
                {
                    'suggestion': row['cached_name'],
                    'designation': row['cached_designation'],
                    'constituency': row['cached_constituency'],
                    'party': row['party'],
                    'type': 'representative',
                    'is_verified': row['is_verified'],
                    'similarity_score': float(row['similarity_score'])
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Failed to get representative suggestions: {e}")
            return []
    
    async def _get_location_suggestions(self, conn, query: str, limit: int) -> List[Dict[str, Any]]:
        """Get location suggestions from posts."""
        try:
            location_query = """
            SELECT location, COUNT(*) as usage_count
            FROM posts 
            WHERE location IS NOT NULL 
                AND location ILIKE $1 || '%'
            GROUP BY location
            ORDER BY usage_count DESC
            LIMIT $2
            """
            
            rows = await conn.fetch(location_query, query, limit)
            
            return [
                {
                    'suggestion': row['location'],
                    'type': 'location',
                    'usage_count': row['usage_count']
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Failed to get location suggestions: {e}")
            return []
    
    async def _get_tag_suggestions(self, conn, query: str, limit: int) -> List[Dict[str, Any]]:
        """Get tag suggestions from posts."""
        try:
            tag_query = """
            SELECT 
                tag,
                COUNT(*) as usage_count
            FROM (
                SELECT unnest(tags) as tag
                FROM posts 
                WHERE tags IS NOT NULL 
                    AND array_length(tags, 1) > 0
            ) tag_list
            WHERE tag ILIKE $1 || '%'
            GROUP BY tag
            ORDER BY usage_count DESC
            LIMIT $2
            """
            
            rows = await conn.fetch(tag_query, query, limit)
            
            return [
                {
                    'suggestion': row['tag'],
                    'type': 'tag',
                    'usage_count': row['usage_count']
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Failed to get tag suggestions: {e}")
            return []
    
    async def _get_trending_suggestions(self, limit: int, user_id: Optional[int]) -> Dict[str, Any]:
        """Get trending suggestions when no query is provided."""
        try:
            async with self.db_service.get_connection_with_retry() as conn:
                # Get trending searches from last 7 days
                trending_query = """
                SELECT 
                    query,
                    COUNT(*) as total_searches,
                    COUNT(DISTINCT user_id) as unique_users,
                    MAX(created_at) as last_searched
                FROM search_analytics
                WHERE created_at > NOW() - INTERVAL '7 days'
                GROUP BY query
                HAVING COUNT(*) > 3
                ORDER BY total_searches DESC, unique_users DESC
                LIMIT $1
                """
                
                trending_rows = await conn.fetch(trending_query, limit)
                
                trending = [
                    {
                        'suggestion': row['query'],
                        'type': 'trending',
                        'total_searches': row['total_searches'],
                        'unique_users': row['unique_users'],
                        'last_searched': row['last_searched']
                    }
                    for row in trending_rows
                ]
                
                # Get user's recent searches if user_id provided
                recent_user_searches = []
                if user_id:
                    user_recent_query = """
                    SELECT DISTINCT query, created_at as last_searched_at, 1 as search_count
                    FROM search_analytics
                    WHERE user_id = $1
                        AND created_at > NOW() - INTERVAL '7 days'
                    ORDER BY created_at DESC
                    LIMIT $2
                    """
                    
                    user_rows = await conn.fetch(user_recent_query, user_id, limit // 2)
                    recent_user_searches = [
                        {
                            'suggestion': row['query'],
                            'type': 'recent_personal',
                            'last_searched': row['last_searched_at'],
                            'search_count': row['search_count']
                        }
                        for row in user_rows
                    ]
                
                return {
                    'suggestions': {
                        'trending': trending,
                        'recent_personal': recent_user_searches
                    },
                    'entity_suggestions': {},
                    'metadata': {
                        'suggestion_count': len(trending) + len(recent_user_searches),
                        'generated_at': datetime.now(timezone.utc).isoformat()
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get trending suggestions: {e}")
            return {'suggestions': {}, 'entity_suggestions': {}, 'metadata': {}}
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize query for suggestions."""
        # Remove extra whitespace and convert to lowercase
        cleaned = " ".join(query.strip().lower().split())
        
        # Remove special characters except spaces and common punctuation
        cleaned = re.sub(r'[^\w\s\-\.]', '', cleaned)
        
        return cleaned


class PopularTermsAnalyzer:
    """Analyzes and provides insights on popular search terms."""
    
    def __init__(self):
        self.db_service = DatabaseService()
    
    async def get_popular_terms_analysis(
        self,
        time_period: str = "7d",
        entity_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get comprehensive analysis of popular search terms.
        
        Args:
            time_period: Time period for analysis ('1d', '7d', '30d', '90d')
            entity_types: Filter by entity types
            limit: Maximum number of terms to analyze
        
        Returns:
            Dict containing popular terms analysis
        """
        period_mapping = {
            '1d': 1,
            '7d': 7,
            '30d': 30,
            '90d': 90
        }
        
        days = period_mapping.get(time_period, 7)
        
        try:
            async with self.db_service.get_connection_with_retry() as conn:
                # Get popular search terms
                popular_terms = await self._get_popular_terms(conn, days, entity_types, limit)
                
                # Get term frequency distribution
                term_distribution = await self._get_term_distribution(conn, days, limit)
                
                # Get trending terms (comparing with previous period)
                trending_terms = await self._get_trending_terms(conn, days, limit)
                
                # Get search volume trends
                volume_trends = await self._get_volume_trends(conn, days)
                
                return {
                    'analysis_period': f"{days} days",
                    'popular_terms': popular_terms,
                    'term_distribution': term_distribution,
                    'trending_terms': trending_terms,
                    'volume_trends': volume_trends,
                    'metadata': {
                        'analyzed_at': datetime.now(timezone.utc).isoformat(),
                        'total_terms': len(popular_terms)
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to analyze popular terms: {e}")
            return {'popular_terms': [], 'metadata': {}}
    
    async def _get_popular_terms(self, conn, days: int, entity_types: Optional[List[str]], limit: int):
        """Get most popular search terms."""
        entity_filter = ""
        params = [days, limit]
        
        if entity_types:
            # Convert entity_types to search_type format for filtering
            search_types = [','.join(entity_types)]
            entity_filter = "AND search_type = ANY($3)"
            params.append(search_types)
        
        query = f"""
        SELECT 
            query,
            COUNT(*) as total_searches,
            COUNT(DISTINCT user_id) as unique_searchers,
            AVG(1.0) as avg_searches_per_user,
            MAX(created_at) as last_searched,
            MIN(created_at) as first_searched,
            array_agg(DISTINCT search_type) as searched_entities
        FROM search_analytics
        WHERE created_at > NOW() - INTERVAL '{days} days'
        {entity_filter}
        GROUP BY query
        ORDER BY total_searches DESC, unique_searchers DESC
        LIMIT $2
        """
        
        rows = await conn.fetch(query, *params)
        
        return [
            {
                'term': row['query'],
                'total_searches': row['total_searches'],
                'unique_searchers': row['unique_searchers'],
                'avg_searches_per_user': float(row['avg_searches_per_user']),
                'first_searched': row['first_searched'],
                'last_searched': row['last_searched'],
                'searched_entities': row['searched_entities'],
                'popularity_score': row['total_searches'] * row['unique_searchers']
            }
            for row in rows
        ]
    
    async def _get_term_distribution(self, conn, days: int, limit: int):
        """Get distribution of search term frequencies."""
        query = """
        WITH term_stats AS (
            SELECT 
                COUNT(*) as search_frequency,
                COUNT(*) as frequency
            FROM search_analytics
            WHERE created_at > NOW() - INTERVAL $1 || ' days'
            GROUP BY query
        )
        SELECT 
            search_frequency as searches_per_term,
            COUNT(*) as number_of_terms,
            (COUNT(*) * 100.0 / SUM(COUNT(*)) OVER()) as percentage
        FROM term_stats
        GROUP BY search_frequency
        ORDER BY search_frequency DESC
        LIMIT $2
        """
        
        rows = await conn.fetch(query, days, limit)
        
        return [
            {
                'searches_per_term': row['searches_per_term'],
                'number_of_terms': row['number_of_terms'],
                'percentage': float(row['percentage'])
            }
            for row in rows
        ]
    
    async def _get_trending_terms(self, conn, days: int, limit: int):
        """Get trending terms by comparing current period with previous period."""
        query = """
        WITH current_period AS (
            SELECT 
                query,
                COUNT(*) as current_searches
            FROM search_analytics
            WHERE created_at > NOW() - INTERVAL $1 || ' days'
            GROUP BY query
        ),
        previous_period AS (
            SELECT 
                query,
                COUNT(*) as previous_searches
            FROM search_analytics
            WHERE created_at BETWEEN 
                NOW() - INTERVAL ($1 * 2) || ' days' 
                AND NOW() - INTERVAL $1 || ' days'
            GROUP BY query
        )
        SELECT 
            COALESCE(c.query, p.query) as query,
            COALESCE(c.current_searches, 0) as current_searches,
            COALESCE(p.previous_searches, 0) as previous_searches,
            CASE 
                WHEN p.previous_searches = 0 THEN 999999  -- New terms
                ELSE (c.current_searches * 100.0 / p.previous_searches) - 100
            END as growth_percentage
        FROM current_period c
        FULL OUTER JOIN previous_period p ON c.query = p.query
        WHERE COALESCE(c.current_searches, 0) > 0
        ORDER BY growth_percentage DESC, current_searches DESC
        LIMIT $2
        """
        
        rows = await conn.fetch(query, days, limit)
        
        return [
            {
                'term': row['query'],
                'current_searches': row['current_searches'],
                'previous_searches': row['previous_searches'],
                'growth_percentage': float(row['growth_percentage']) if row['growth_percentage'] != 999999 else None,
                'is_new': row['growth_percentage'] == 999999
            }
            for row in rows
        ]
    
    async def _get_volume_trends(self, conn, days: int):
        """Get search volume trends over time."""
        query = """
        SELECT 
            DATE(created_at) as search_date,
            COUNT(*) as daily_searches,
            COUNT(DISTINCT user_id) as unique_searchers,
            COUNT(DISTINCT query) as unique_queries
        FROM search_analytics
        WHERE created_at > NOW() - INTERVAL $1 || ' days'
        GROUP BY DATE(created_at)
        ORDER BY search_date
        """
        
        rows = await conn.fetch(query, days)
        
        return [
            {
                'date': row['search_date'],
                'daily_searches': row['daily_searches'],
                'unique_searchers': row['unique_searchers'],
                'unique_queries': row['unique_queries']
            }
            for row in rows
        ]
