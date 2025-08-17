"""
Recommendation Engine - Phase 3
Candidate generation and heuristic ranking system
"""

import asyncpg
import random
import time
from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime, timedelta
import logging
import math
from dataclasses import dataclass
from uuid import UUID

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CandidatePost:
    """Represents a candidate post with ranking features"""
    id: UUID
    title: str
    content: str
    author_id: UUID
    author_username: str
    created_at: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location: Optional[str] = None  # Changed from category
    tags: Optional[List[str]] = None  # Changed from area
    
    # Ranking features
    quality_score: float = 0.0
    engagement_rate: float = 0.0
    recency_decay: float = 1.0
    personal_affinity: float = 0.0
    social_proximity: float = 0.0
    locality_match: float = 0.0
    
    # Metadata
    candidate_source: str = "unknown"
    ranking_reasons: List[str] = None
    
    def __post_init__(self):
        if self.ranking_reasons is None:
            self.ranking_reasons = []


class RecommendationEngine:
    """Main recommendation engine for generating personalized feeds"""
    
    def __init__(self, db_connection: asyncpg.Connection):
        self.db = db_connection
        
    async def generate_feed(
        self,
        user_id: str,
        limit: int = 20,
        user_latitude: Optional[float] = None,
        user_longitude: Optional[float] = None,
        surface: str = "main_feed"
    ) -> List[CandidatePost]:
        """
        Generate personalized feed using multiple candidate sources and heuristic ranking
        """
        start_time = time.time()
        
        # Get user preferences for personalization
        user_preferences = await self._get_user_preferences(user_id)
        
        # Generate candidates from multiple sources
        candidates = []
        
        if settings.recs_enable_social:
            social_candidates = await self._generate_social_candidates(user_id, limit)
            candidates.extend(social_candidates)
            
        if settings.recs_enable_trending:
            trending_candidates = await self._generate_trending_candidates(limit)
            candidates.extend(trending_candidates)
            
        if settings.recs_enable_locality and user_latitude and user_longitude:
            locality_candidates = await self._generate_locality_candidates(
                user_latitude, user_longitude, limit
            )
            candidates.extend(locality_candidates)
            
        if settings.recs_enable_recency:
            recency_candidates = await self._generate_recency_candidates(limit)
            candidates.extend(recency_candidates)
        
        # Remove duplicates (keep first occurrence)
        seen_ids = set()
        unique_candidates = []
        for candidate in candidates:
            if candidate.id not in seen_ids:
                seen_ids.add(candidate.id)
                unique_candidates.append(candidate)
        
        # Apply heuristic ranking
        ranked_candidates = await self._rank_candidates(
            unique_candidates, user_id, user_preferences, user_latitude, user_longitude
        )
        
        # Apply diversity and safety filters
        filtered_candidates = self._apply_diversity_filters(ranked_candidates, user_id)
        
        # Apply exploration/exploitation balance
        final_candidates = self._apply_exploration(filtered_candidates, limit)
        
        processing_time = time.time() - start_time
        logger.info(
            f"Generated feed: user={user_id}, candidates={len(candidates)}, "
            f"unique={len(unique_candidates)}, ranked={len(ranked_candidates)}, "
            f"final={len(final_candidates)}, time={processing_time:.3f}s"
        )
        
        return final_candidates[:limit]
    
    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user topic and author affinities for personalization"""
        
        # Get topic affinities
        topic_affinities = await self.db.fetch("""
            SELECT t.name, uta.score
            FROM user_topic_affinity uta
            JOIN topics t ON uta.topic_id = t.id
            WHERE uta.user_id = $1
            ORDER BY uta.score DESC
        """, user_id)
        
        # Get author affinities (people user engages with)
        author_affinities = await self.db.fetch("""
            SELECT author_id, score, is_following
            FROM user_author_affinity
            WHERE user_id = $1
            ORDER BY score DESC
        """, user_id)
        
        return {
            "topic_affinities": {row['name']: float(row['score']) for row in topic_affinities},
            "author_affinities": {str(row['author_id']): {
                "score": float(row['score']),
                "is_following": row['is_following']
            } for row in author_affinities}
        }
    
    async def _generate_social_candidates(self, user_id: str, limit: int) -> List[CandidatePost]:
        """Generate candidates from followed authors and high-affinity authors"""
        
        query = """
            SELECT DISTINCT
                p.id, p.title, p.content, p.user_id as author_id, p.created_at,
                p.latitude, p.longitude, p.location, p.tags,
                u.username as author_username,
                COALESCE(pq.quality_score, 0.1) as quality_score,
                COALESCE(pq.engagement_rate, 0.0) as engagement_rate,
                COALESCE(pq.recency_decay, 1.0) as recency_decay,
                uaa.score as author_affinity_score
            FROM posts p
            JOIN users u ON p.user_id = u.id
            LEFT JOIN post_quality pq ON p.id = pq.post_id
            JOIN user_author_affinity uaa ON p.user_id = uaa.author_id
            WHERE uaa.user_id = $1
            AND p.created_at >= NOW() - INTERVAL '7 days'
            AND (uaa.is_following = true OR uaa.score > 0.5)
            ORDER BY uaa.score DESC, p.created_at DESC
            LIMIT $2
        """
        
        rows = await self.db.fetch(query, user_id, limit * 2)  # Get more for diversity
        
        candidates = []
        for row in rows:
            candidate = CandidatePost(
                id=row['id'],
                title=row['title'],
                content=row['content'],
                author_id=row['author_id'],
                author_username=row['author_username'],
                created_at=row['created_at'],
                latitude=row['latitude'],
                longitude=row['longitude'],
                location=row['location'],
                tags=row['tags'],
                quality_score=float(row['quality_score']),
                engagement_rate=float(row['engagement_rate']),
                recency_decay=float(row['recency_decay']),
                social_proximity=float(row['author_affinity_score']) if row['author_affinity_score'] else 0.0,
                candidate_source="social"
            )
            candidate.ranking_reasons.append("followed_author" if row['author_affinity_score'] else "high_affinity_author")
            candidates.append(candidate)
        
        return candidates
    
    async def _generate_trending_candidates(self, limit: int) -> List[CandidatePost]:
        """Generate candidates from trending posts materialized view"""
        
        query = """
            SELECT 
                post_id as id, title, content, author_id, post_created_at as created_at,
                quality_score, engagement_rate, recency_decay,
                u.username as author_username
            FROM trending_posts tp
            JOIN users u ON tp.author_id = u.id
            ORDER BY quality_score DESC
            LIMIT $1
        """
        
        try:
            rows = await self.db.fetch(query, limit * 2)
        except asyncpg.PostgresError as e:
            logger.warning(f"Could not fetch from trending_posts: {e}")
            return []
        
        candidates = []
        for row in rows:
            candidate = CandidatePost(
                id=row['id'],
                title=row['title'],
                content=row['content'],
                author_id=row['author_id'],
                author_username=row['author_username'],
                created_at=row['created_at'],
                quality_score=float(row['quality_score']),
                engagement_rate=float(row['engagement_rate']),
                recency_decay=float(row['recency_decay']),
                candidate_source="trending"
            )
            candidate.ranking_reasons.append("trending")
            candidates.append(candidate)
        
        return candidates
    
    async def _generate_locality_candidates(
        self, user_lat: float, user_lon: float, limit: int
    ) -> List[CandidatePost]:
        """Generate candidates from geographically nearby posts"""
        
        # Use PostGIS for geographic queries within configured radius
        query = """
            SELECT 
                p.id, p.title, p.content, p.user_id as author_id, p.created_at,
                p.latitude, p.longitude, p.location, p.tags,
                u.username as author_username,
                COALESCE(pq.quality_score, 0.1) as quality_score,
                COALESCE(pq.engagement_rate, 0.0) as engagement_rate,
                COALESCE(pq.recency_decay, 1.0) as recency_decay,
                ST_Distance(
                    ST_GeogFromText('POINT(' || $2 || ' ' || $1 || ')'),
                    ST_GeogFromText('POINT(' || p.longitude || ' ' || p.latitude || ')')
                ) as distance_meters
            FROM posts p
            JOIN users u ON p.user_id = u.id
            LEFT JOIN post_quality pq ON p.id = pq.post_id
            WHERE p.latitude IS NOT NULL AND p.longitude IS NOT NULL
            AND p.created_at >= NOW() - INTERVAL '14 days'
            AND ST_DWithin(
                ST_GeogFromText('POINT(' || $2 || ' ' || $1 || ')'),
                ST_GeogFromText('POINT(' || p.longitude || ' ' || p.latitude || ')'),
                $3
            )
            ORDER BY distance_meters ASC, pq.quality_score DESC NULLS LAST
            LIMIT $4
        """
        
        try:
            rows = await self.db.fetch(
                query, user_lat, user_lon, settings.max_search_radius_meters, limit * 2
            )
        except asyncpg.PostgresError as e:
            logger.warning(f"PostGIS locality query failed: {e}")
            return []
        
        candidates = []
        for row in rows:
            # Calculate locality match score (closer = higher score)
            distance_km = row['distance_meters'] / 1000.0
            locality_score = max(0.0, 1.0 - (distance_km / (settings.max_search_radius_meters / 1000.0)))
            
            candidate = CandidatePost(
                id=row['id'],
                title=row['title'],
                content=row['content'],
                author_id=row['author_id'],
                author_username=row['author_username'],
                created_at=row['created_at'],
                latitude=row['latitude'],
                longitude=row['longitude'],
                location=row['location'],
                tags=row['tags'],
                quality_score=float(row['quality_score']),
                engagement_rate=float(row['engagement_rate']),
                recency_decay=float(row['recency_decay']),
                locality_match=locality_score,
                candidate_source="locality"
            )
            candidate.ranking_reasons.append(f"nearby_{distance_km:.1f}km")
            candidates.append(candidate)
        
        return candidates
    
    async def _generate_recency_candidates(self, limit: int) -> List[CandidatePost]:
        """Generate candidates from recent posts (fallback)"""
        
        query = """
            SELECT 
                p.id, p.title, p.content, p.user_id as author_id, p.created_at,
                p.latitude, p.longitude, p.location, p.tags,
                u.username as author_username,
                COALESCE(pq.quality_score, 0.1) as quality_score,
                COALESCE(pq.engagement_rate, 0.0) as engagement_rate,
                COALESCE(pq.recency_decay, 1.0) as recency_decay
            FROM posts p
            JOIN users u ON p.user_id = u.id
            LEFT JOIN post_quality pq ON p.id = pq.post_id
            WHERE p.created_at >= NOW() - INTERVAL '30 days'
            ORDER BY p.created_at DESC, pq.quality_score DESC NULLS LAST
            LIMIT $1
        """
        
        rows = await self.db.fetch(query, limit * 2)
        
        candidates = []
        for row in rows:
            candidate = CandidatePost(
                id=row['id'],
                title=row['title'],
                content=row['content'],
                author_id=row['author_id'],
                author_username=row['author_username'],
                created_at=row['created_at'],
                latitude=row['latitude'],
                longitude=row['longitude'],
                location=row['location'],
                tags=row['tags'],
                quality_score=float(row['quality_score']),
                engagement_rate=float(row['engagement_rate']),
                recency_decay=float(row['recency_decay']),
                candidate_source="recency"
            )
            candidate.ranking_reasons.append("recent")
            candidates.append(candidate)
        
        return candidates
    
    async def _rank_candidates(
        self,
        candidates: List[CandidatePost],
        user_id: str,
        user_preferences: Dict[str, Any],
        user_latitude: Optional[float] = None,
        user_longitude: Optional[float] = None
    ) -> List[CandidatePost]:
        """Apply heuristic ranking using weighted features"""
        
        # Calculate personal affinity scores for candidates
        for candidate in candidates:
            # Author affinity
            author_key = str(candidate.author_id)
            if author_key in user_preferences["author_affinities"]:
                candidate.personal_affinity = user_preferences["author_affinities"][author_key]["score"]
            
            # Topic affinity (simplified - using location and tags)
            topic_affinity = 0.0
            if candidate.location:
                # Simple keyword matching with topics
                location_lower = candidate.location.lower()
                for topic_name, score in user_preferences["topic_affinities"].items():
                    if topic_name.lower() in location_lower:
                        topic_affinity = max(topic_affinity, score)
            
            # Check tags as well
            if candidate.tags:
                for tag in candidate.tags:
                    tag_lower = tag.lower() if tag else ""
                    for topic_name, score in user_preferences["topic_affinities"].items():
                        if topic_name.lower() in tag_lower:
                            topic_affinity = max(topic_affinity, score)
            
            candidate.personal_affinity = max(candidate.personal_affinity, topic_affinity * 0.8)
        
        # Calculate final ranking scores
        for candidate in candidates:
            score = (
                settings.recs_weight_personal_affinity * candidate.personal_affinity +
                settings.recs_weight_engagement_rate * candidate.engagement_rate +
                settings.recs_weight_recency_decay * candidate.recency_decay +
                settings.recs_weight_social_proximity * candidate.social_proximity +
                settings.recs_weight_locality_match * candidate.locality_match
            )
            
            # Add quality baseline
            score += candidate.quality_score * 0.1
            
            # Store score for sorting (abuse one of the existing fields)
            candidate.quality_score = score
        
        # Sort by final score
        candidates.sort(key=lambda c: c.quality_score, reverse=True)
        
        return candidates
    
    def _apply_diversity_filters(self, candidates: List[CandidatePost], user_id: str) -> List[CandidatePost]:
        """Apply diversity caps (max per author/topic) and overexposure filtering"""
        
        author_counts = {}
        topic_counts = {}
        filtered = []
        
        for candidate in candidates:
            # Check author diversity
            author_id = str(candidate.author_id)
            author_count = author_counts.get(author_id, 0)
            if author_count >= settings.recs_diversity_max_per_author:
                continue
            
            # Check topic diversity (simplified - use location as topic)
            topic = candidate.location or "general"
            topic_count = topic_counts.get(topic, 0)
            if topic_count >= settings.recs_diversity_max_per_topic:
                continue
            
            # TODO: Check overexposure (requires checking recent impressions)
            # This would query interactions table for recent impressions of this post
            
            # Add to filtered list and update counts
            filtered.append(candidate)
            author_counts[author_id] = author_count + 1
            topic_counts[topic] = topic_count + 1
        
        return filtered
    
    def _apply_exploration(self, candidates: List[CandidatePost], limit: int) -> List[CandidatePost]:
        """Apply exploration vs exploitation balance"""
        
        if not candidates or settings.recs_exploration_rate <= 0:
            return candidates
        
        # Calculate exploration slots
        exploration_slots = int(limit * settings.recs_exploration_rate)
        exploitation_slots = limit - exploration_slots
        
        # Split candidates into exploitation (top scored) and exploration (random from rest)
        exploitation_candidates = candidates[:exploitation_slots]
        
        if len(candidates) > exploitation_slots:
            exploration_pool = candidates[exploitation_slots:]
            exploration_candidates = random.sample(
                exploration_pool, 
                min(exploration_slots, len(exploration_pool))
            )
        else:
            exploration_candidates = []
        
        # Merge and shuffle to avoid obvious patterns
        final_candidates = exploitation_candidates + exploration_candidates
        random.shuffle(final_candidates)
        
        return final_candidates
