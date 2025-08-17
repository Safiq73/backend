"""
Real-time Search Event Generator
Monitors database changes and generates search update events
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.db.database import get_db
from app.websocket.connection_manager import (
    SearchUpdateEvent, 
    EventType, 
    EntityType, 
    connection_manager
)

logger = logging.getLogger(__name__)

class SearchEventGenerator:
    """Generates real-time search events from database changes"""
    
    def __init__(self):
        self.monitoring = False
        self.last_check = {}
        self.check_interval = 5  # seconds
        
    async def start_monitoring(self):
        """Start monitoring database changes"""
        if self.monitoring:
            return
            
        self.monitoring = True
        logger.info("Starting real-time search event monitoring")
        
        # Start monitoring tasks
        tasks = [
            asyncio.create_task(self._monitor_users()),
            asyncio.create_task(self._monitor_posts()),
            asyncio.create_task(self._monitor_representatives()),
            asyncio.create_task(self._monitor_engagement())
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop_monitoring(self):
        """Stop monitoring database changes"""
        self.monitoring = False
        logger.info("Stopped real-time search event monitoring")
    
    async def _monitor_users(self):
        """Monitor user table changes"""
        while self.monitoring:
            try:
                async for db in get_db():
                    # Check for new/updated users
                    last_check = self.last_check.get('users', datetime.min)
                    
                    query = text("""
                        SELECT id, username, full_name, bio, created_at, updated_at, is_active
                        FROM users 
                        WHERE (created_at > :last_check OR updated_at > :last_check)
                        AND is_active = true
                        ORDER BY updated_at DESC
                        LIMIT 50
                    """)
                    
                    result = await db.execute(query, {"last_check": last_check})
                    users = result.fetchall()
                    
                    for user in users:
                        await self._process_user_change(user, db)
                    
                    self.last_check['users'] = datetime.utcnow()
                    break
                    
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring users: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_posts(self):
        """Monitor post table changes"""
        while self.monitoring:
            try:
                async for db in get_db():
                    last_check = self.last_check.get('posts', datetime.min)
                    
                    query = text("""
                        SELECT p.id, p.content, p.title, p.created_at, p.updated_at, 
                               p.author_id, p.status, p.category,
                               u.username, u.full_name
                        FROM posts p
                        JOIN users u ON p.author_id = u.id
                        WHERE (p.created_at > :last_check OR p.updated_at > :last_check)
                        AND p.status = 'published'
                        ORDER BY p.updated_at DESC
                        LIMIT 50
                    """)
                    
                    result = await db.execute(query, {"last_check": last_check})
                    posts = result.fetchall()
                    
                    for post in posts:
                        await self._process_post_change(post, db)
                    
                    self.last_check['posts'] = datetime.utcnow()
                    break
                    
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring posts: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_representatives(self):
        """Monitor representative table changes"""
        while self.monitoring:
            try:
                async for db in get_db():
                    last_check = self.last_check.get('representatives', datetime.min)
                    
                    query = text("""
                        SELECT r.id, r.full_name, r.party, r.office, r.jurisdiction_id,
                               r.created_at, r.updated_at, r.is_active,
                               j.name as jurisdiction_name
                        FROM representatives r
                        JOIN jurisdictions j ON r.jurisdiction_id = j.id
                        WHERE (r.created_at > :last_check OR r.updated_at > :last_check)
                        AND r.is_active = true
                        ORDER BY r.updated_at DESC
                        LIMIT 50
                    """)
                    
                    result = await db.execute(query, {"last_check": last_check})
                    representatives = result.fetchall()
                    
                    for rep in representatives:
                        await self._process_representative_change(rep, db)
                    
                    self.last_check['representatives'] = datetime.utcnow()
                    break
                    
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring representatives: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_engagement(self):
        """Monitor engagement metrics (likes, follows, etc.)"""
        while self.monitoring:
            try:
                async for db in get_db():
                    last_check = self.last_check.get('engagement', datetime.min)
                    
                    # Monitor post likes
                    query = text("""
                        SELECT post_id, COUNT(*) as like_count
                        FROM post_likes 
                        WHERE created_at > :last_check
                        GROUP BY post_id
                        HAVING COUNT(*) > 0
                    """)
                    
                    result = await db.execute(query, {"last_check": last_check})
                    post_likes = result.fetchall()
                    
                    for like_data in post_likes:
                        await self._process_engagement_change(
                            entity_type=EntityType.POST,
                            entity_id=str(like_data.post_id),
                            metric_type="likes",
                            value=like_data.like_count,
                            db=db
                        )
                    
                    # Monitor user follows
                    query = text("""
                        SELECT followed_id, COUNT(*) as follower_count
                        FROM user_follows 
                        WHERE created_at > :last_check
                        GROUP BY followed_id
                        HAVING COUNT(*) > 0
                    """)
                    
                    result = await db.execute(query, {"last_check": last_check})
                    user_follows = result.fetchall()
                    
                    for follow_data in user_follows:
                        await self._process_engagement_change(
                            entity_type=EntityType.USER,
                            entity_id=str(follow_data.followed_id),
                            metric_type="followers",
                            value=follow_data.follower_count,
                            db=db
                        )
                    
                    self.last_check['engagement'] = datetime.utcnow()
                    break
                    
                await asyncio.sleep(self.check_interval * 2)  # Check less frequently
                
            except Exception as e:
                logger.error(f"Error monitoring engagement: {e}")
                await asyncio.sleep(10)
    
    async def _process_user_change(self, user_row, db: AsyncSession):
        """Process a user change and generate search events"""
        user_data = {
            "id": str(user_row.id),
            "username": user_row.username,
            "full_name": user_row.full_name,
            "bio": user_row.bio,
            "updated_at": user_row.updated_at.isoformat() if user_row.updated_at else None
        }
        
        # Determine event type
        event_type = EventType.NEW_RESULT if user_row.created_at == user_row.updated_at else EventType.UPDATED_RESULT
        
        # Generate affected queries
        affected_queries = await self._generate_user_affected_queries(user_data)
        
        # Calculate relevance score
        relevance_score = await self._calculate_user_relevance(user_data, db)
        
        event = SearchUpdateEvent(
            event_type=event_type,
            entity_type=EntityType.USER,
            entity_id=str(user_row.id),
            data=user_data,
            affected_queries=affected_queries,
            timestamp=datetime.utcnow(),
            relevance_score=relevance_score,
            metadata={"table": "users"}
        )
        
        await connection_manager.broadcast_search_update(event)
        logger.debug(f"Generated user event: {event_type} for user {user_row.id}")
    
    async def _process_post_change(self, post_row, db: AsyncSession):
        """Process a post change and generate search events"""
        post_data = {
            "id": str(post_row.id),
            "title": post_row.title,
            "content": post_row.content[:500] + "..." if len(post_row.content) > 500 else post_row.content,
            "author_id": str(post_row.author_id),
            "author_username": post_row.username,
            "author_name": post_row.full_name,
            "category": post_row.category,
            "updated_at": post_row.updated_at.isoformat() if post_row.updated_at else None
        }
        
        event_type = EventType.NEW_RESULT if post_row.created_at == post_row.updated_at else EventType.UPDATED_RESULT
        
        affected_queries = await self._generate_post_affected_queries(post_data)
        relevance_score = await self._calculate_post_relevance(post_data, db)
        
        event = SearchUpdateEvent(
            event_type=event_type,
            entity_type=EntityType.POST,
            entity_id=str(post_row.id),
            data=post_data,
            affected_queries=affected_queries,
            timestamp=datetime.utcnow(),
            relevance_score=relevance_score,
            metadata={"table": "posts", "category": post_row.category}
        )
        
        await connection_manager.broadcast_search_update(event)
        logger.debug(f"Generated post event: {event_type} for post {post_row.id}")
    
    async def _process_representative_change(self, rep_row, db: AsyncSession):
        """Process a representative change and generate search events"""
        rep_data = {
            "id": str(rep_row.id),
            "full_name": rep_row.full_name,
            "party": rep_row.party,
            "office": rep_row.office,
            "jurisdiction": rep_row.jurisdiction_name,
            "updated_at": rep_row.updated_at.isoformat() if rep_row.updated_at else None
        }
        
        event_type = EventType.NEW_RESULT if rep_row.created_at == rep_row.updated_at else EventType.UPDATED_RESULT
        
        affected_queries = await self._generate_representative_affected_queries(rep_data)
        relevance_score = await self._calculate_representative_relevance(rep_data, db)
        
        event = SearchUpdateEvent(
            event_type=event_type,
            entity_type=EntityType.REPRESENTATIVE,
            entity_id=str(rep_row.id),
            data=rep_data,
            affected_queries=affected_queries,
            timestamp=datetime.utcnow(),
            relevance_score=relevance_score,
            metadata={"table": "representatives", "party": rep_row.party}
        )
        
        await connection_manager.broadcast_search_update(event)
        logger.debug(f"Generated representative event: {event_type} for rep {rep_row.id}")
    
    async def _process_engagement_change(
        self, 
        entity_type: EntityType, 
        entity_id: str, 
        metric_type: str, 
        value: int, 
        db: AsyncSession
    ):
        """Process an engagement change and generate update events"""
        event_data = {
            "metric_type": metric_type,
            "value": value,
            "entity_id": entity_id
        }
        
        # Get entity data for affected queries
        affected_queries = []
        if entity_type == EntityType.POST:
            affected_queries = await self._get_post_queries_for_engagement(entity_id, db)
        elif entity_type == EntityType.USER:
            affected_queries = await self._get_user_queries_for_engagement(entity_id, db)
        
        event = SearchUpdateEvent(
            event_type=EventType.ENGAGEMENT_UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            data=event_data,
            affected_queries=affected_queries,
            timestamp=datetime.utcnow(),
            relevance_score=min(value / 10.0, 1.0),  # Normalize engagement score
            metadata={"metric": metric_type, "engagement": True}
        )
        
        await connection_manager.broadcast_search_update(event)
        logger.debug(f"Generated engagement event: {metric_type}={value} for {entity_type}:{entity_id}")
    
    async def _generate_user_affected_queries(self, user_data: Dict[str, Any]) -> List[str]:
        """Generate list of search queries affected by user changes"""
        queries = []
        
        # Add username-based queries
        if user_data.get('username'):
            username = user_data['username'].lower()
            queries.extend([
                username,
                f"@{username}",
                username[:3] if len(username) >= 3 else username,
                username[:5] if len(username) >= 5 else username
            ])
        
        # Add name-based queries
        if user_data.get('full_name'):
            full_name = user_data['full_name'].lower()
            queries.append(full_name)
            
            # Add individual name parts
            name_parts = full_name.split()
            for part in name_parts:
                if len(part) >= 2:
                    queries.append(part)
        
        # Add bio-based queries
        if user_data.get('bio'):
            bio_words = user_data['bio'].lower().split()
            for word in bio_words:
                if len(word) >= 4:  # Only meaningful words
                    queries.append(word)
        
        return list(set(queries))  # Remove duplicates
    
    async def _generate_post_affected_queries(self, post_data: Dict[str, Any]) -> List[str]:
        """Generate list of search queries affected by post changes"""
        queries = []
        
        # Add title-based queries
        if post_data.get('title'):
            title = post_data['title'].lower()
            queries.append(title)
            
            title_words = title.split()
            for word in title_words:
                if len(word) >= 3:
                    queries.append(word)
        
        # Add content-based queries
        if post_data.get('content'):
            content_words = post_data['content'].lower().split()
            # Take significant words
            for word in content_words[:20]:  # Limit to first 20 words
                if len(word) >= 4:
                    queries.append(word)
        
        # Add category-based queries
        if post_data.get('category'):
            queries.append(post_data['category'].lower())
        
        # Add author-based queries
        if post_data.get('author_username'):
            queries.append(post_data['author_username'].lower())
        
        return list(set(queries))
    
    async def _generate_representative_affected_queries(self, rep_data: Dict[str, Any]) -> List[str]:
        """Generate list of search queries affected by representative changes"""
        queries = []
        
        # Add name-based queries
        if rep_data.get('full_name'):
            full_name = rep_data['full_name'].lower()
            queries.append(full_name)
            
            name_parts = full_name.split()
            for part in name_parts:
                if len(part) >= 2:
                    queries.append(part)
        
        # Add party-based queries
        if rep_data.get('party'):
            queries.append(rep_data['party'].lower())
        
        # Add office-based queries
        if rep_data.get('office'):
            queries.append(rep_data['office'].lower())
        
        # Add jurisdiction-based queries
        if rep_data.get('jurisdiction'):
            queries.append(rep_data['jurisdiction'].lower())
        
        return list(set(queries))
    
    async def _calculate_user_relevance(self, user_data: Dict[str, Any], db: AsyncSession) -> float:
        """Calculate relevance score for a user"""
        base_score = 0.5
        
        # Boost for complete profiles
        if user_data.get('full_name'):
            base_score += 0.2
        if user_data.get('bio'):
            base_score += 0.1
        
        # Get follower count for popularity boost
        try:
            query = text("""
                SELECT COUNT(*) as follower_count 
                FROM user_follows 
                WHERE followed_id = :user_id
            """)
            result = await db.execute(query, {"user_id": user_data['id']})
            follower_count = result.scalar() or 0
            
            # Logarithmic scaling for follower boost
            if follower_count > 0:
                import math
                follower_boost = min(math.log10(follower_count + 1) / 4, 0.3)
                base_score += follower_boost
                
        except Exception as e:
            logger.error(f"Error calculating user relevance: {e}")
        
        return min(base_score, 1.0)
    
    async def _calculate_post_relevance(self, post_data: Dict[str, Any], db: AsyncSession) -> float:
        """Calculate relevance score for a post"""
        base_score = 0.4
        
        # Boost for content quality
        if post_data.get('title'):
            base_score += 0.2
        if post_data.get('content') and len(post_data['content']) > 100:
            base_score += 0.1
        
        # Get engagement metrics
        try:
            query = text("""
                SELECT COUNT(*) as like_count 
                FROM post_likes 
                WHERE post_id = :post_id
            """)
            result = await db.execute(query, {"post_id": post_data['id']})
            like_count = result.scalar() or 0
            
            # Engagement boost
            if like_count > 0:
                import math
                engagement_boost = min(math.log10(like_count + 1) / 3, 0.4)
                base_score += engagement_boost
                
        except Exception as e:
            logger.error(f"Error calculating post relevance: {e}")
        
        return min(base_score, 1.0)
    
    async def _calculate_representative_relevance(self, rep_data: Dict[str, Any], db: AsyncSession) -> float:
        """Calculate relevance score for a representative"""
        base_score = 0.6  # Representatives are generally important
        
        # Boost for higher offices
        office = rep_data.get('office', '').lower()
        if 'president' in office or 'governor' in office:
            base_score += 0.3
        elif 'senator' in office or 'congress' in office:
            base_score += 0.2
        elif 'mayor' in office or 'council' in office:
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    async def _get_post_queries_for_engagement(self, post_id: str, db: AsyncSession) -> List[str]:
        """Get queries that would be affected by post engagement changes"""
        try:
            query = text("""
                SELECT title, content, category 
                FROM posts 
                WHERE id = :post_id
            """)
            result = await db.execute(query, {"post_id": post_id})
            post = result.fetchone()
            
            if post:
                post_data = {
                    "title": post.title,
                    "content": post.content,
                    "category": post.category
                }
                return await self._generate_post_affected_queries(post_data)
        except Exception as e:
            logger.error(f"Error getting post queries: {e}")
        
        return []
    
    async def _get_user_queries_for_engagement(self, user_id: str, db: AsyncSession) -> List[str]:
        """Get queries that would be affected by user engagement changes"""
        try:
            query = text("""
                SELECT username, full_name, bio 
                FROM users 
                WHERE id = :user_id
            """)
            result = await db.execute(query, {"user_id": user_id})
            user = result.fetchone()
            
            if user:
                user_data = {
                    "username": user.username,
                    "full_name": user.full_name,
                    "bio": user.bio
                }
                return await self._generate_user_affected_queries(user_data)
        except Exception as e:
            logger.error(f"Error getting user queries: {e}")
        
        return []

# Global event generator instance
search_event_generator = SearchEventGenerator()
