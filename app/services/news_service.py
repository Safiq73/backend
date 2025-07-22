import httpx
import asyncio
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging_config import get_logger
import random
from datetime import datetime

logger = get_logger('app.news_service')


class NewsService:
    """Service for fetching external news from NewsAPI"""
    
    def __init__(self):
        self.api_key = settings.newsapi_key
        self.base_url = "https://newsapi.org/v2"
        
    async def fetch_news(
        self, 
        count: int, 
        country: str = "in",
        category: Optional[str] = None,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Fetch news articles from NewsAPI
        
        Args:
            count: Number of articles to fetch
            country: Country code (default: "in" for India)
            category: News category (business, entertainment, general, health, science, sports, technology)
            page: Page number for pagination
            
        Returns:
            List of news articles formatted as posts
        """
        if not self.api_key:
            logger.warning("NewsAPI key not configured, returning empty news list")
            return []
            
        try:
            # Calculate page size - fetch a bit more to account for filtering
            page_size = min(count + 5, 100)  # NewsAPI max is 100
            
            url = f"{self.base_url}/top-headlines"
            params = {
                "country": country,
                "apiKey": self.api_key,
                "pageSize": page_size,
                "page": page
            }
            
            if category:
                params["category"] = category
                
            logger.info(f"Fetching news from NewsAPI | Count: {count} | Country: {country} | Category: {category}")
            logger.info(f"Request URL: {url}")
            logger.info(f"Request params: {params}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                logger.info(f"Response status: {response.status_code}")
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"API response status: {data.get('status')}")
                logger.info(f"Total results: {data.get('totalResults', 0)}")
                
                if data.get("status") != "ok":
                    logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                    return []
                
                articles = data.get("articles", [])
                logger.info(f"Raw articles count: {len(articles)}")
                
                # Transform news articles to match post format
                news_posts = []
                valid_count = 0
                invalid_count = 0
                
                for i, article in enumerate(articles):  # Process all available articles
                    if self._is_valid_article(article):
                        if len(news_posts) < count:  # Only add if we need more
                            news_post = self._transform_article_to_post(article)
                            news_posts.append(news_post)
                            valid_count += 1
                            logger.debug(f"Article {i+1}: {article.get('title', 'No title')}")
                        else:
                            break  # We have enough articles
                    else:
                        invalid_count += 1
                        logger.debug(f"Article {i+1} filtered out: {article.get('title', 'No title')}")
                
                logger.info(f"Article validation | Valid: {valid_count} | Invalid: {invalid_count} | Requested: {count}")
                logger.info(f"Successfully fetched {len(news_posts)} news articles")
                return news_posts
                
        except httpx.RequestError as e:
            logger.error(f"Network error fetching news: {e}")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching news: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching news: {e}")
            return []
    
    def _is_valid_article(self, article: Dict[str, Any]) -> bool:
        """Check if article has required fields and content"""
        return (
            article.get("title") and 
            article.get("description") and
            article.get("title") != "[Removed]" and
            article.get("description") != "[Removed]"
        )
    
    def _transform_article_to_post(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a news article to match the post structure"""
        
        # Generate a unique ID for the news article
        article_url = article.get('url', '')
        article_title = article.get('title', '')
        article_id = f"news_{abs(hash(article_url + article_title)) % 1000000}"
        
        # Extract and clean content
        title = article.get("title", "").strip()
        description = article.get("description", "").strip()
        content = description
        
        # Add source information to content
        source_info = article.get("source", {})
        source_name = source_info.get("name", "Unknown Source")
        
        if article.get("url"):
            content += f"\n\nRead the full article: {article.get('url')}"
        
        # Handle media - use urlToImage from NewsAPI
        media_urls = []
        if article.get("urlToImage"):
            media_urls.append(article.get("urlToImage"))
        
        # Parse publish date
        published_at = article.get("publishedAt")
        created_at = None
        updated_at = None
        
        if published_at:
            try:
                # Parse ISO format datetime
                dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                created_at = dt.isoformat()
                updated_at = dt.isoformat()
            except:
                # Fallback to current time if parsing fails
                now = datetime.utcnow()
                created_at = now.isoformat()
                updated_at = now.isoformat()
        else:
            now = datetime.utcnow()
            created_at = now.isoformat()
            updated_at = now.isoformat()
        
        # Create the post structure
        news_post = {
            "id": article_id,
            "title": title,
            "content": content,
            "post_type": "news",
            "area": self._extract_location(article),
            "category": self._categorize_article(article),
            "status": "published",
            "media_urls": media_urls,
            "tags": [],
            "created_at": created_at,
            "updated_at": updated_at,
            "author": {
                "id": "newsapi",
                "username": "newsapi",
                "display_name": source_name,
                "avatar_url": None
            },
            "upvotes": random.randint(10, 100),  # Mock engagement data - higher for news
            "downvotes": random.randint(0, 10),
            "comment_count": random.randint(5, 50),  # Higher comment counts for news
            "user_vote": None,
            "is_saved": False,
            "source": "news",  # This is the key field to distinguish news from posts
            "external_url": article.get("url"),
            "source_name": source_name,
            # Add original NewsAPI fields for richer content
            "description": description,
            "published_at": published_at,
            "url_to_image": article.get("urlToImage"),
            "news_source_id": source_info.get("id"),
            "author_name": article.get("author")
        }
        
        return news_post
    
    def _extract_location(self, article: Dict[str, Any]) -> str:
        """Extract location information from article if available"""
        # Simple location extraction - could be enhanced with NLP
        content = f"{article.get('title', '')} {article.get('description', '')}".lower()
        
        # Common Indian cities/states (can be expanded)
        locations = [
            "mumbai", "delhi", "bangalore", "chennai", "kolkata", "hyderabad",
            "pune", "ahmedabad", "surat", "jaipur", "lucknow", "kanpur",
            "nagpur", "indore", "thane", "bhopal", "visakhapatnam", "pimpri",
            "patna", "vadodara", "ghaziabad", "ludhiana", "agra", "nashik",
            "faridabad", "meerut", "rajkot", "kalyan", "vasai", "varanasi",
            "kerala", "karnataka", "maharashtra", "tamil nadu", "gujarat",
            "rajasthan", "west bengal", "madhya pradesh", "uttar pradesh"
        ]
        
        for location in locations:
            if location in content:
                return location.title()
        
        return "India"  # Default location
    
    def _categorize_article(self, article: Dict[str, Any]) -> str:
        """Categorize article based on content"""
        content = f"{article.get('title', '')} {article.get('description', '')}".lower()
        
        # Define categories and keywords
        categories = {
            "Infrastructure": ["road", "bridge", "transport", "metro", "railway", "airport", "construction"],
            "Healthcare": ["health", "hospital", "medical", "doctor", "medicine", "vaccine", "treatment"],
            "Education": ["school", "college", "university", "education", "student", "teacher", "exam"],
            "Environment": ["environment", "pollution", "climate", "green", "waste", "water", "air"],
            "Technology": ["technology", "digital", "app", "software", "internet", "cyber", "ai"],
            "Politics": ["government", "minister", "election", "policy", "parliament", "politics"],
            "Economy": ["economy", "business", "market", "finance", "bank", "money", "trade"],
            "Safety": ["police", "crime", "security", "safety", "fire", "accident", "emergency"]
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in content:
                    return category
        
        return "General"  # Default category


# Create a singleton instance
news_service = NewsService()
