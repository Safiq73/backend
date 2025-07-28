from typing import List, Dict, Any, Optional
import random
import math
from app.services.post_service import PostService
from app.services.news_service import news_service
from app.schemas import PaginatedResponse
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger('app.mixed_content_service')


class MixedContentService:
    """Service for mixing posts and news content with configurable ratios"""
    
    def __init__(self):
        self.post_service = PostService()
        self.news_service = news_service
        
    async def get_mixed_content(
        self,
        page: int,
        size: int,
        user_id: Optional[str] = None,
        post_type: Optional[str] = None,
        sort_by: str = "timestamp",
        order: str = "desc"
    ) -> PaginatedResponse:
        """
        Get mixed content (posts + news) with configurable ratios
        
        Args:
            page: Page number
            size: Items per page
            user_id: Current user ID for personalization
            post_type: Filter by post type
            sort_by: Sort field
            order: Sort order
            
        Returns:
            PaginatedResponse with mixed content
        """
        
        # Calculate content distribution
        content_distribution = self._calculate_content_distribution(size)
        max_posts = content_distribution["max_posts"]
        max_news = content_distribution["max_news"]
        
        logger.info(
            f"Mixed content request | Page: {page}, Size: {size} | "
            f"Max posts: {max_posts}, Max news: {max_news} | "
            f"Posts ratio: {settings.posts_ratio}"
        )
        
        # Check if we should skip DB query for posts
        posts_skip = (page - 1) * max_posts
        should_fetch_posts = await self._should_fetch_posts(
            posts_skip, max_posts, post_type, user_id
        )
        
        # Fetch posts from database
        posts = []
        if should_fetch_posts and max_posts > 0:
            try:
                posts = await self.post_service.get_posts(
                    skip=posts_skip,
                    limit=max_posts,
                    post_type=post_type,
                    current_user_id=user_id
                )
                logger.info(f"Fetched {len(posts)} posts from database")
            except Exception as e:
                logger.error(f"Error fetching posts: {e}")
                posts = []
        
        # Calculate actual news count needed
        actual_posts_count = len(posts)
        actual_news_count = size - actual_posts_count
        
        # Ensure we don't exceed reasonable limits
        actual_news_count = min(actual_news_count, 100)  # NewsAPI limit
        
        logger.info(f"Actual distribution | Posts: {actual_posts_count}, News: {actual_news_count}")
        
        # Fetch news articles
        news_articles = []

        if actual_news_count > 0:
            try:
                # Calculate news page - spread news across pages
                news_page = max(1, (page - 1) // 2 + 1)  # Spread news pagination
                
                # news_articles = await self.news_service.fetch_news(
                #     count=actual_news_count,
                #     country=settings.newsapi_country,
                #     category=self._map_category_to_news(category),
                #     page=news_page
                # )
                
                # Ensure we have a list of articles, this is to handle cases where no articles are returned
                news_articles = []
                
                
                logger.info(f"Fetched {len(news_articles)} news articles")
            except Exception as e:
                logger.error(f"Error fetching news: {e}")
                news_articles = []
        
        # Combine and shuffle content
        mixed_items = self._combine_and_shuffle(posts, news_articles)
        
        # Limit to requested size
        mixed_items = mixed_items[:size]
        
        # Calculate pagination info
        has_more = await self._calculate_has_more(
            page, size, max_posts, actual_posts_count, len(news_articles)
        )
        
        total_estimate = size * page + (size if has_more else 0)
        
        result = PaginatedResponse(
            items=mixed_items,
            total=total_estimate,
            page=page,
            size=size,
            has_more=has_more
        )
        
        logger.info(
            f"Mixed content response | Items: {len(mixed_items)} | "
            f"Posts: {actual_posts_count} | News: {len(news_articles)} | "
            f"Has more: {has_more}"
        )
        
        return result
    
    def _calculate_content_distribution(self, size: int) -> Dict[str, int]:
        """Calculate how many posts vs news to fetch"""
        posts_ratio = settings.posts_ratio
        
        # Calculate max posts based on ratio
        max_posts = math.floor(size * posts_ratio)
        
        # Apply min/max constraints
        max_posts = max(settings.min_posts_per_page, max_posts)
        max_posts = min(settings.max_posts_per_page, max_posts)
        max_posts = min(size, max_posts)  # Can't exceed total size
        
        # Remaining slots for news
        max_news = size - max_posts
        
        return {
            "max_posts": max_posts,
            "max_news": max_news
        }
    
    async def _should_fetch_posts(
        self, 
        skip: int, 
        limit: int, 
        post_type: Optional[str], 
        user_id: Optional[str]
    ) -> bool:
        """
        Determine if we should fetch posts from DB
        Returns False if we know there are no posts for this page range
        """
        if limit == 0:
            return False
            
        try:
            # Quick check: get just 1 post to see if any exist for this page range
            test_posts = await self.post_service.get_posts(
                skip=skip,
                limit=1,
                post_type=post_type,
                current_user_id=user_id
            )
            return len(test_posts) > 0
        except Exception as e:
            logger.error(f"Error checking if posts exist: {e}")
            return True  # Default to fetching to be safe
    
    def _map_category_to_news(self, category: Optional[str]) -> Optional[str]:
        """Map internal categories to NewsAPI categories"""
        if not category:
            return None
            
        category_mapping = {
            "Technology": "technology",
            "Healthcare": "health",
            "Economy": "business",
            "Sports": "sports",
            "Entertainment": "entertainment",
            "Education": "general",
            "Infrastructure": "general",
            "Environment": "science",
            "Politics": "general",
            "Safety": "general"
        }
        
        return category_mapping.get(category, "general")
    
    def _combine_and_shuffle(
        self, 
        posts: List[Dict[str, Any]], 
        news_articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Combine posts and news, then randomly shuffle"""
        
        # Add source field to posts
        for post in posts:
            post["source"] = "post"
        
        # News articles already have source="news" from news_service
        
        # Combine all items
        combined_items = posts + news_articles
        
        # Randomly shuffle to mix posts and news
        random.shuffle(combined_items)
        
        return combined_items
    
    async def _calculate_has_more(
        self,
        page: int,
        size: int,
        max_posts_per_page: int,
        actual_posts_count: int,
        actual_news_count: int
    ) -> bool:
        """
        Calculate if there are more items available for pagination
        """
        
        # If we got the full requested size, there might be more content
        total_items_returned = actual_posts_count + actual_news_count
        if total_items_returned >= size:
            return True
        
        # If we didn't get the full requested size, check if there's more content available
        
        # Check if there are more posts available
        posts_have_more = False
        try:
            # Check if there are more posts beyond what we've already fetched
            next_posts = await self.post_service.get_posts(
                skip=page * max_posts_per_page,
                limit=1,
                current_user_id=None
            )
            posts_have_more = len(next_posts) > 0
        except:
            pass
        
        # Check if there are more news articles available
        # For NewsAPI, we can assume more pages exist if we got some articles
        # and we're not on a very high page number (NewsAPI has limits)
        news_have_more = actual_news_count > 0 and page < 10  # Reasonable limit
        
        # We have more content if either posts or news have more content
        has_more = posts_have_more or news_have_more
        
        return has_more


# Create singleton instance
mixed_content_service = MixedContentService()
