"""
Advanced Analytics Service
Provides comprehensive analytics and insights for the CivicPulse platform
"""

import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, asdict

from app.db.database import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class SearchTrend:
    """Search trend data"""
    query: str
    count: int
    growth_rate: float
    time_period: str
    category: str

@dataclass
class UserBehaviorMetrics:
    """User behavior analytics"""
    total_searches: int
    unique_users: int
    average_session_length_seconds: float
    bounce_rate: float
    popular_entity_types: Dict[str, int]
    peak_search_hours: List[int]

@dataclass
class PlatformMetrics:
    """Overall platform metrics"""
    total_users: int
    active_users_24h: int
    active_users_7d: int
    total_posts: int
    total_comments: int
    total_searches: int
    engagement_rate: float
    response_time_avg_ms: float

@dataclass
class ContentAnalytics:
    """Content performance analytics"""
    trending_posts: List[Dict[str, Any]]
    trending_topics: List[Dict[str, str]]
    popular_areas: List[Dict[str, Any]]
    engagement_leaders: List[Dict[str, Any]]

class AdvancedAnalyticsService:
    """Advanced analytics service for CivicPulse platform"""

    def __init__(self):
        self.cache_ttl = 300  # 5 minutes cache
        self._cache = {}
        self._cache_timestamps = {}

    async def get_comprehensive_dashboard_analytics(
        self, 
        time_period: str = "7d",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive analytics for dashboard"""
        try:
            cache_key = f"dashboard_analytics_{time_period}_{user_id}"
            
            # Check cache
            if self._is_cached(cache_key):
                return self._cache[cache_key]

            # Calculate time range
            end_time = datetime.utcnow()
            if time_period == "1d":
                start_time = end_time - timedelta(days=1)
            elif time_period == "7d":
                start_time = end_time - timedelta(days=7)
            elif time_period == "30d":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(days=7)

            # Gather all analytics
            platform_metrics = await self._get_platform_metrics(start_time, end_time)
            search_analytics = await self._get_search_analytics(start_time, end_time)
            user_behavior = await self._get_user_behavior_metrics(start_time, end_time)
            content_analytics = await self._get_content_analytics(start_time, end_time)
            trend_analysis = await self._get_trend_analysis(start_time, end_time)
            
            result = {
                "time_period": time_period,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "platform_metrics": platform_metrics,
                "search_analytics": search_analytics,
                "user_behavior": user_behavior,
                "content_analytics": content_analytics,
                "trend_analysis": trend_analysis,
                "real_time_stats": await self._get_real_time_stats()
            }

            # Cache result
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = datetime.utcnow()

            return result

        except Exception as e:
            logger.error(f"Failed to get comprehensive analytics: {e}")
            raise

    async def _get_platform_metrics(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> PlatformMetrics:
        """Get overall platform metrics"""
        try:
            async with get_db() as conn:
                # Total users
                total_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
                
                # Active users in different periods
                active_24h = await conn.fetchval("""
                    SELECT COUNT(DISTINCT user_id) 
                    FROM search_analytics 
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                """)
                
                active_7d = await conn.fetchval("""
                    SELECT COUNT(DISTINCT user_id) 
                    FROM search_analytics 
                    WHERE created_at >= NOW() - INTERVAL '7 days'
                """)

                # Content metrics
                total_posts = await conn.fetchval("SELECT COUNT(*) FROM posts")
                total_comments = await conn.fetchval("SELECT COUNT(*) FROM comments")
                total_searches = await conn.fetchval("""
                    SELECT COUNT(*) FROM search_analytics 
                    WHERE created_at BETWEEN $1 AND $2
                """, start_time, end_time)

                # Engagement rate (posts with comments / total posts)
                engagement_rate = await conn.fetchval("""
                    SELECT 
                        CASE 
                            WHEN COUNT(*) > 0 
                            THEN ROUND((COUNT(CASE WHEN comment_count > 0 THEN 1 END)::float / COUNT(*)::float) * 100, 2)
                            ELSE 0 
                        END
                    FROM posts
                    WHERE created_at BETWEEN $1 AND $2
                """, start_time, end_time) or 0

                # Average response time
                avg_response_time = await conn.fetchval("""
                    SELECT AVG(search_time_ms) 
                    FROM search_analytics 
                    WHERE created_at BETWEEN $1 AND $2 AND search_time_ms IS NOT NULL
                """, start_time, end_time) or 0

                return PlatformMetrics(
                    total_users=total_users or 0,
                    active_users_24h=active_24h or 0,
                    active_users_7d=active_7d or 0,
                    total_posts=total_posts or 0,
                    total_comments=total_comments or 0,
                    total_searches=total_searches or 0,
                    engagement_rate=float(engagement_rate),
                    response_time_avg_ms=float(avg_response_time)
                )

        except Exception as e:
            logger.error(f"Failed to get platform metrics: {e}")
            raise

    async def _get_search_analytics(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get detailed search analytics"""
        try:
            async with get_db() as conn:
                # Popular search terms
                popular_queries = await conn.fetch("""
                    SELECT 
                        query,
                        COUNT(*) as search_count,
                        COUNT(DISTINCT user_id) as unique_users,
                        AVG(result_count) as avg_results,
                        MAX(created_at) as last_searched
                    FROM search_analytics 
                    WHERE created_at BETWEEN $1 AND $2
                    GROUP BY query 
                    ORDER BY search_count DESC 
                    LIMIT 20
                """, start_time, end_time)

                # Search trends by hour
                search_trends = await conn.fetch("""
                    SELECT 
                        DATE_TRUNC('hour', created_at) as hour,
                        COUNT(*) as search_count,
                        COUNT(DISTINCT user_id) as unique_users,
                        AVG(search_time_ms) as avg_response_time
                    FROM search_analytics 
                    WHERE created_at BETWEEN $1 AND $2
                    GROUP BY DATE_TRUNC('hour', created_at)
                    ORDER BY hour
                """, start_time, end_time)

                # Search by entity type
                entity_breakdown = await conn.fetch("""
                    SELECT 
                        search_type,
                        COUNT(*) as count,
                        COUNT(DISTINCT user_id) as unique_users
                    FROM search_analytics 
                    WHERE created_at BETWEEN $1 AND $2 AND search_type IS NOT NULL
                    GROUP BY search_type 
                    ORDER BY count DESC
                """, start_time, end_time)

                # Zero result searches
                zero_results = await conn.fetch("""
                    SELECT 
                        query,
                        COUNT(*) as count
                    FROM search_analytics 
                    WHERE created_at BETWEEN $1 AND $2 AND result_count = 0
                    GROUP BY query 
                    ORDER BY count DESC 
                    LIMIT 10
                """, start_time, end_time)

                return {
                    "popular_queries": [dict(row) for row in popular_queries],
                    "search_trends": [dict(row) for row in search_trends],
                    "entity_breakdown": [dict(row) for row in entity_breakdown],
                    "zero_result_queries": [dict(row) for row in zero_results],
                    "total_searches": len(popular_queries)
                }

        except Exception as e:
            logger.error(f"Failed to get search analytics: {e}")
            raise

    async def _get_user_behavior_metrics(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> UserBehaviorMetrics:
        """Get user behavior analytics"""
        try:
            async with get_db() as conn:
                # Basic search metrics
                search_metrics = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_searches,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(DISTINCT DATE_TRUNC('day', created_at)) as active_days
                    FROM search_analytics 
                    WHERE created_at BETWEEN $1 AND $2
                """, start_time, end_time)

                # Peak search hours
                peak_hours = await conn.fetch("""
                    SELECT 
                        EXTRACT(HOUR FROM created_at) as hour,
                        COUNT(*) as search_count
                    FROM search_analytics 
                    WHERE created_at BETWEEN $1 AND $2
                    GROUP BY EXTRACT(HOUR FROM created_at)
                    ORDER BY search_count DESC
                    LIMIT 5
                """, start_time, end_time)

                # Entity type preferences
                entity_preferences = await conn.fetch("""
                    SELECT 
                        search_type,
                        COUNT(*) as count
                    FROM search_analytics 
                    WHERE created_at BETWEEN $1 AND $2 AND search_type IS NOT NULL
                    GROUP BY search_type
                """, start_time, end_time)

                # Calculate bounce rate (searches with 0 results)
                total_searches = search_metrics['total_searches'] if search_metrics else 0
                zero_result_searches = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM search_analytics 
                    WHERE created_at BETWEEN $1 AND $2 AND result_count = 0
                """, start_time, end_time) or 0

                bounce_rate = (zero_result_searches / total_searches * 100) if total_searches > 0 else 0

                return UserBehaviorMetrics(
                    total_searches=total_searches,
                    unique_users=search_metrics['unique_users'] if search_metrics else 0,
                    average_session_length_seconds=0,  # TODO: Implement session tracking
                    bounce_rate=bounce_rate,
                    popular_entity_types={row['search_type']: row['count'] for row in entity_preferences},
                    peak_search_hours=[int(row['hour']) for row in peak_hours]
                )

        except Exception as e:
            logger.error(f"Failed to get user behavior metrics: {e}")
            raise

    async def _get_content_analytics(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> ContentAnalytics:
        """Get content performance analytics"""
        try:
            async with get_db() as conn:
                # Trending posts (most commented/voted in time period)
                trending_posts = await conn.fetch("""
                    SELECT 
                        p.id,
                        p.title,
                        p.area,
                        p.category,
                        p.upvotes,
                        p.comment_count,
                        p.view_count,
                        u.username as author,
                        p.created_at
                    FROM posts p
                    JOIN users u ON p.user_id = u.id
                    WHERE p.created_at BETWEEN $1 AND $2
                    ORDER BY (p.upvotes + p.comment_count * 2) DESC
                    LIMIT 10
                """, start_time, end_time)

                # Popular areas/locations
                popular_areas = await conn.fetch("""
                    SELECT 
                        area,
                        COUNT(*) as post_count,
                        SUM(upvotes) as total_upvotes,
                        SUM(comment_count) as total_comments
                    FROM posts 
                    WHERE created_at BETWEEN $1 AND $2 AND area IS NOT NULL
                    GROUP BY area 
                    ORDER BY post_count DESC 
                    LIMIT 10
                """, start_time, end_time)

                # Engagement leaders (most active users)
                engagement_leaders = await conn.fetch("""
                    SELECT 
                        u.username,
                        u.display_name,
                        COUNT(p.id) as posts_count,
                        SUM(p.upvotes) as total_upvotes,
                        COUNT(c.id) as comments_count
                    FROM users u
                    LEFT JOIN posts p ON u.id = p.user_id AND p.created_at BETWEEN $1 AND $2
                    LEFT JOIN comments c ON u.id = c.user_id AND c.created_at BETWEEN $1 AND $2
                    WHERE u.is_active = TRUE
                    GROUP BY u.id, u.username, u.display_name
                    HAVING COUNT(p.id) > 0 OR COUNT(c.id) > 0
                    ORDER BY (COUNT(p.id) + COUNT(c.id)) DESC
                    LIMIT 10
                """, start_time, end_time)

                # Trending topics from post titles and search queries
                trending_topics = await conn.fetch("""
                    WITH topic_words AS (
                        SELECT LOWER(unnest(string_to_array(title, ' '))) as word
                        FROM posts 
                        WHERE created_at BETWEEN $1 AND $2
                        UNION ALL
                        SELECT LOWER(unnest(string_to_array(query, ' '))) as word
                        FROM search_analytics 
                        WHERE created_at BETWEEN $1 AND $2
                    )
                    SELECT 
                        word as topic,
                        COUNT(*) as frequency
                    FROM topic_words
                    WHERE LENGTH(word) > 3  -- Filter out short words
                    GROUP BY word 
                    ORDER BY frequency DESC 
                    LIMIT 20
                """, start_time, end_time)

                return ContentAnalytics(
                    trending_posts=[dict(row) for row in trending_posts],
                    trending_topics=[{"topic": row['topic'], "frequency": str(row['frequency'])} for row in trending_topics],
                    popular_areas=[dict(row) for row in popular_areas],
                    engagement_leaders=[dict(row) for row in engagement_leaders]
                )

        except Exception as e:
            logger.error(f"Failed to get content analytics: {e}")
            raise

    async def _get_trend_analysis(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get trend analysis"""
        try:
            async with get_db() as conn:
                # Growth trends
                growth_data = await conn.fetch("""
                    SELECT 
                        DATE_TRUNC('day', created_at) as date,
                        COUNT(DISTINCT CASE WHEN created_at BETWEEN $1 AND $2 THEN user_id END) as new_users,
                        COUNT(CASE WHEN created_at BETWEEN $1 AND $2 THEN id END) as new_posts
                    FROM users u
                    FULL OUTER JOIN posts p ON DATE_TRUNC('day', u.created_at) = DATE_TRUNC('day', p.created_at)
                    WHERE u.created_at BETWEEN $1 AND $2 OR p.created_at BETWEEN $1 AND $2
                    GROUP BY DATE_TRUNC('day', COALESCE(u.created_at, p.created_at))
                    ORDER BY date
                """, start_time, end_time)

                # Search volume trends
                search_volume_trends = await conn.fetch("""
                    SELECT 
                        DATE_TRUNC('day', created_at) as date,
                        COUNT(*) as search_volume,
                        COUNT(DISTINCT user_id) as unique_searchers
                    FROM search_analytics 
                    WHERE created_at BETWEEN $1 AND $2
                    GROUP BY DATE_TRUNC('day', created_at)
                    ORDER BY date
                """, start_time, end_time)

                return {
                    "growth_trends": [dict(row) for row in growth_data],
                    "search_volume_trends": [dict(row) for row in search_volume_trends]
                }

        except Exception as e:
            logger.error(f"Failed to get trend analysis: {e}")
            raise

    async def _get_real_time_stats(self) -> Dict[str, Any]:
        """Get real-time platform statistics"""
        try:
            async with get_db() as conn:
                # Active connections from WebSocket manager
                # This would integrate with the WebSocket connection manager from Step 5
                now = datetime.utcnow()
                last_hour = now - timedelta(hours=1)

                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(DISTINCT user_id) as active_users_last_hour,
                        COUNT(*) as searches_last_hour,
                        AVG(search_time_ms) as avg_response_time_last_hour
                    FROM search_analytics 
                    WHERE created_at >= $1
                """, last_hour)

                # Recent activity
                recent_posts = await conn.fetchval("""
                    SELECT COUNT(*) FROM posts WHERE created_at >= $1
                """, last_hour)

                recent_comments = await conn.fetchval("""
                    SELECT COUNT(*) FROM comments WHERE created_at >= $1
                """, last_hour)

                return {
                    "active_users_last_hour": stats['active_users_last_hour'] if stats else 0,
                    "searches_last_hour": stats['searches_last_hour'] if stats else 0,
                    "avg_response_time_last_hour": float(stats['avg_response_time_last_hour'] or 0),
                    "recent_posts": recent_posts or 0,
                    "recent_comments": recent_comments or 0,
                    "timestamp": now.isoformat()
                }

        except Exception as e:
            logger.error(f"Failed to get real-time stats: {e}")
            raise

    async def get_search_insights(
        self, 
        time_period: str = "7d",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get detailed search insights and patterns"""
        try:
            end_time = datetime.utcnow()
            if time_period == "1d":
                start_time = end_time - timedelta(days=1)
            elif time_period == "7d":
                start_time = end_time - timedelta(days=7)
            elif time_period == "30d":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(days=7)

            async with get_db() as conn:
                # Search patterns by day of week
                weekly_patterns = await conn.fetch("""
                    SELECT 
                        EXTRACT(DOW FROM created_at) as day_of_week,
                        COUNT(*) as search_count,
                        AVG(result_count) as avg_results
                    FROM search_analytics 
                    WHERE created_at BETWEEN $1 AND $2
                    GROUP BY EXTRACT(DOW FROM created_at)
                    ORDER BY day_of_week
                """, start_time, end_time)

                # Query length analysis
                query_analysis = await conn.fetch("""
                    SELECT 
                        CASE 
                            WHEN LENGTH(query) <= 5 THEN 'short'
                            WHEN LENGTH(query) <= 15 THEN 'medium'
                            ELSE 'long'
                        END as query_length,
                        COUNT(*) as count,
                        AVG(result_count) as avg_results
                    FROM search_analytics 
                    WHERE created_at BETWEEN $1 AND $2
                    GROUP BY 
                        CASE 
                            WHEN LENGTH(query) <= 5 THEN 'short'
                            WHEN LENGTH(query) <= 15 THEN 'medium'
                            ELSE 'long'
                        END
                """, start_time, end_time)

                # Most improved search terms (queries with increasing success)
                improving_queries = await conn.fetch("""
                    WITH query_performance AS (
                        SELECT 
                            query,
                            DATE_TRUNC('day', created_at) as date,
                            AVG(result_count) as avg_results
                        FROM search_analytics 
                        WHERE created_at BETWEEN $1 AND $2
                        GROUP BY query, DATE_TRUNC('day', created_at)
                        HAVING COUNT(*) >= 2
                    )
                    SELECT 
                        query,
                        CORR(EXTRACT(EPOCH FROM date), avg_results) as improvement_trend
                    FROM query_performance
                    GROUP BY query
                    HAVING CORR(EXTRACT(EPOCH FROM date), avg_results) > 0.5
                    ORDER BY improvement_trend DESC
                    LIMIT 10
                """, start_time, end_time)

                return {
                    "weekly_patterns": [dict(row) for row in weekly_patterns],
                    "query_analysis": [dict(row) for row in query_analysis],
                    "improving_queries": [dict(row) for row in improving_queries],
                    "time_period": time_period,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat()
                }

        except Exception as e:
            logger.error(f"Failed to get search insights: {e}")
            raise

    def _is_cached(self, cache_key: str) -> bool:
        """Check if data is cached and still valid"""
        if cache_key not in self._cache:
            return False
        
        timestamp = self._cache_timestamps.get(cache_key)
        if not timestamp:
            return False
        
        return (datetime.utcnow() - timestamp).total_seconds() < self.cache_ttl

    async def clear_cache(self):
        """Clear analytics cache"""
        self._cache.clear()
        self._cache_timestamps.clear()

# Global analytics service instance
analytics_service = AdvancedAnalyticsService()
