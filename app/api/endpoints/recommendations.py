"""
Recommendations API endpoints
Handles feed generation and event tracking for the recommendation system
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
import asyncpg
from typing import List, Optional, Dict, Any
import random
import time
from datetime import datetime, timedelta
import logging
from uuid import UUID

from app.core.config import settings
from app.db.database import get_db
from app.schemas.recommendations import (
    EventCreate, EventResponse, FeedRequest, FeedResponse, 
    PostRecommendation, RecommendationMetadata
)
from app.services.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/events", response_model=EventResponse)
async def log_interaction_event(
    event: EventCreate,
    request: Request,
    db: asyncpg.Connection = Depends(get_db),
    user_id: str = "a6bafa72-ab86-4d0b-b901-06e9364b67d3"  # Temporary: use real user UUID since auth is disabled
):
    """
    Log user interaction events for the recommendation system.
    
    Events include: impression, click, like, comment, share, save, hide, follow_author
    """
    if not settings.enable_recommendations:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendations service is disabled"
        )
    
    try:
        # Get user IP and user agent for basic context
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Sample impressions to reduce volume
        if event.event_type == "impression":
            if random.random() > settings.recs_sample_impressions_rate:
                return EventResponse(
                    success=True,
                    message="Event sampled out",
                    event_id=None
                )
        
        # Validate post exists (simplified check)
        post_query = """
            SELECT id, user_id as author_id, created_at 
            FROM posts 
            WHERE id = $1
        """
        result = await db.fetchrow(post_query, event.post_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        post_id, author_id, post_created_at = result['id'], result['author_id'], result['created_at']
        
        # Determine event weight based on type
        event_weights = {
            "impression": 0.1,
            "click": 1.0,
            "like": 1.2,
            "comment": 1.5,
            "share": 1.8,
            "save": 1.6,
            "hide": -2.0,
            "follow_author": 2.0
        }
        
        weight = event_weights.get(event.event_type, 1.0)
        
        # Detect device type from user agent (basic detection)
        device_type = "desktop"
        if user_agent and any(mobile in user_agent.lower() for mobile in ["mobile", "android", "iphone"]):
            device_type = "mobile"
        elif user_agent and "tablet" in user_agent.lower():
            device_type = "tablet"
        
        # Insert interaction event
        insert_query = """
            INSERT INTO interactions (
                user_id, post_id, event_type, weight, surface, 
                session_id, device_type, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """
        
        event_id = await db.fetchval(insert_query,
            user_id,
            event.post_id,
            event.event_type,
            weight,
            event.surface or "main_feed",
            event.session_id,
            device_type,
            event.client_timestamp or datetime.utcnow()
        )
        
        logger.info(
            f"Logged interaction: user={user_id}, post={event.post_id}, "
            f"event={event.event_type}, weight={weight}, device={device_type}"
        )
        
        return EventResponse(
            success=True,
            message="Event logged successfully",
            event_id=event_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging interaction event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to log interaction event"
        )


@router.get("/feed", response_model=FeedResponse)
async def get_personalized_feed(
    limit: int = 20,
    cursor: Optional[str] = None,
    surface: str = "main_feed",
    include_metadata: bool = False,
    user_latitude: Optional[float] = None,
    user_longitude: Optional[float] = None,
    db: asyncpg.Connection = Depends(get_db),
    user_id: str = "a6bafa72-ab86-4d0b-b901-06e9364b67d3"  # Temporary: use real user UUID since auth is disabled
):
    """
    Get personalized feed recommendations for the current user.
    
    Returns a ranked list of posts based on user preferences, 
    social connections, trending content, and locality.
    """
    if not settings.enable_recommendations:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendations service is disabled"
        )
    
    start_time = time.time()
    
    try:
        # Initialize recommendation engine
        engine = RecommendationEngine(db)
        
        # Generate personalized candidates
        candidates = await engine.generate_feed(
            user_id=user_id,
            limit=limit + 5,  # Get a few extra for pagination
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            surface=surface
        )
        
        # Convert candidates to response format
        posts = []
        for candidate in candidates[:limit]:  # Take only requested limit
            post_data = {
                "id": candidate.id,
                "title": candidate.title,
                "content": candidate.content,
                "author_id": candidate.author_id,
                "created_at": candidate.created_at,
                "author_username": candidate.author_username,
                "quality_score": candidate.quality_score
            }
            
            metadata = None
            if include_metadata:
                # Calculate final ranking features for display
                ranking_features = {
                    "personal_affinity": candidate.personal_affinity,
                    "engagement_rate": candidate.engagement_rate,
                    "recency_decay": candidate.recency_decay,
                    "social_proximity": candidate.social_proximity,
                    "locality_match": candidate.locality_match
                }
                
                metadata = RecommendationMetadata(
                    score=candidate.quality_score,
                    reasons=candidate.ranking_reasons,
                    candidate_source=candidate.candidate_source,
                    ranking_features=ranking_features
                )
            
            posts.append(PostRecommendation(
                **post_data,
                metadata=metadata
            ))
        
        # Check if we have more posts for pagination
        has_more = len(candidates) > limit
        
        # Generate next cursor (simple timestamp-based for now)
        next_cursor = None
        if has_more and posts:
            next_cursor = posts[-1].created_at.isoformat()
        
        processing_time = time.time() - start_time
        
        logger.info(
            f"Generated personalized feed: user={user_id}, posts={len(posts)}, "
            f"time={processing_time:.3f}s, surface={surface}, sources={len(set(c.candidate_source for c in candidates))}"
        )
        
        return FeedResponse(
            posts=posts,
            next_cursor=next_cursor,
            has_more=has_more,
            total_count=len(posts),
            processing_time_ms=int(processing_time * 1000),
            surface=surface
        )
        
    except Exception as e:
        logger.error(f"Error generating personalized feed: {str(e)}", exc_info=True)
        
        # Fallback to simple recency-based feed
        logger.info("Falling back to simple recency feed")
        return await _fallback_recency_feed(db, user_id, limit, surface, include_metadata)


async def _fallback_recency_feed(
    db: asyncpg.Connection,
    user_id: str,
    limit: int,
    surface: str,
    include_metadata: bool
) -> FeedResponse:
    """Fallback to simple recency-based feed if personalization fails"""
    
    query = """
        SELECT 
            p.id,
            p.title,
            p.content,
            p.user_id as author_id,
            p.created_at,
            u.username as author_username,
            COALESCE(pq.quality_score, 0.1) as quality_score
        FROM posts p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN post_quality pq ON p.id = pq.post_id
        WHERE p.created_at >= NOW() - INTERVAL '30 days'
        ORDER BY p.created_at DESC, pq.quality_score DESC NULLS LAST
        LIMIT $1
    """
    
    results = await db.fetch(query, limit + 1)
    
    # Convert to response format
    posts = []
    has_more = len(results) > limit
    if has_more:
        results = results[:-1]  # Remove extra item used for pagination check
    
    for row in results:
        post_data = {
            "id": row['id'],
            "title": row['title'],
            "content": row['content'],
            "author_id": row['author_id'],
            "created_at": row['created_at'],
            "author_username": row['author_username'],
            "quality_score": float(row['quality_score']) if row['quality_score'] else 0.1
        }
        
        metadata = None
        if include_metadata:
            metadata = RecommendationMetadata(
                score=post_data["quality_score"],
                reasons=["recency"],
                candidate_source="recency_fallback",
                ranking_features={"recency_decay": 1.0}
            )
        
        posts.append(PostRecommendation(
            **post_data,
            metadata=metadata
        ))
    
    # Generate next cursor
    next_cursor = None
    if has_more and posts:
        next_cursor = posts[-1].created_at.isoformat()
    
    return FeedResponse(
        posts=posts,
        next_cursor=next_cursor,
        has_more=has_more,
        total_count=len(posts),
        processing_time_ms=50,  # Estimate for fallback
        surface=surface
    )


@router.get("/stats")
async def get_recommendation_stats(
    db: asyncpg.Connection = Depends(get_db),
    user_id: str = "a6bafa72-ab86-4d0b-b901-06e9364b67d3"  # Temporary: use real user UUID since auth is disabled
):
    """
    Get basic recommendation system statistics (for debugging/monitoring).
    """
    if not settings.enable_recommendations:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendations service is disabled"
        )
    
    try:
        # Basic stats queries
        stats = {}
        
        # Total interactions in last 24h
        result = await db.fetchval("""
            SELECT COUNT(*) FROM interactions 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)
        stats["total_interactions_24h"] = result or 0
        
        # Total posts with quality metrics updated in last 24h
        result = await db.fetchval("""
            SELECT COUNT(*) FROM post_quality 
            WHERE updated_at >= NOW() - INTERVAL '24 hours'
        """)
        stats["total_posts_with_quality"] = result or 0
        
        # User topic affinities
        result = await db.fetchval("""
            SELECT COUNT(*) FROM user_topic_affinity 
            WHERE user_id = $1
        """, user_id)
        stats["user_topic_affinities"] = result or 0
        
        # User author affinities
        result = await db.fetchval("""
            SELECT COUNT(*) FROM user_author_affinity 
            WHERE user_id = $1
        """, user_id)
        stats["user_author_affinities"] = result or 0
        
        # Get user's top topics
        top_topics = await db.fetch("""
            SELECT t.name, uta.score
            FROM user_topic_affinity uta
            JOIN topics t ON uta.topic_id = t.id
            WHERE uta.user_id = $1
            ORDER BY uta.score DESC
            LIMIT 5
        """, user_id)
        stats["top_topics"] = [{"topic": row['name'], "score": float(row['score'])} for row in top_topics]
        
        return {
            "success": True,
            "stats": stats,
            "user_id": user_id,
            "config": {
                "enable_recommendations": settings.enable_recommendations,
                "exploration_rate": settings.recs_exploration_rate,
                "cache_ttl": settings.recs_cache_ttl_seconds
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting recommendation stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recommendation statistics"
        )


# -------- Phase 2: Admin/maintenance endpoints to trigger batch jobs --------

@router.post("/admin/refresh-quality")
async def refresh_post_quality(db: asyncpg.Connection = Depends(get_db)):
    """Run the quality aggregation function now."""
    if not settings.enable_recommendations:
        raise HTTPException(status_code=503, detail="Recommendations service is disabled")
    try:
        await db.execute("SELECT update_post_quality_metrics();")
        return {"success": True, "message": "post_quality updated"}
    except Exception as e:
        logger.error(f"Error updating post quality: {e}")
        raise HTTPException(status_code=500, detail="Failed to update post quality")


@router.post("/admin/refresh-affinities")
async def refresh_affinities(db: asyncpg.Connection = Depends(get_db)):
    """Run the topic and author affinity aggregation now."""
    if not settings.enable_recommendations:
        raise HTTPException(status_code=503, detail="Recommendations service is disabled")
    try:
        # Topic affinities
        await db.execute("SELECT update_user_topic_affinities();")
        # Author affinities
        await db.execute("SELECT update_user_author_affinities();")
        return {"success": True, "message": "user affinities updated"}
    except Exception as e:
        logger.error(f"Error updating affinities: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user affinities")


@router.post("/admin/refresh-trending")
async def refresh_trending(db: asyncpg.Connection = Depends(get_db)):
    """Refresh the trending materialized view, if present."""
    if not settings.enable_recommendations:
        raise HTTPException(status_code=503, detail="Recommendations service is disabled")
    try:
        # Make sure the MV exists; refresh concurrently if possible
        await db.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY trending_posts;")
        return {"success": True, "message": "trending_posts refreshed"}
    except asyncpg.PostgresError as e:
        # Fall back or report not existing
        logger.warning(f"Could not refresh MV trending_posts: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh trending_posts")
