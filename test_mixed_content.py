"""
Test script to verify mixed content functionality
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.mixed_content_service import mixed_content_service
from app.services.news_service import news_service
from app.core.config import settings

async def test_news_service():
    """Test the news service"""
    print("Testing News Service...")
    print(f"NewsAPI Key configured: {'Yes' if settings.newsapi_key else 'No'}")
    
    try:
        news_articles = await news_service.fetch_news(count=5, country="in")
        print(f"Fetched {len(news_articles)} news articles")
        
        if news_articles:
            print("\nSample news article:")
            article = news_articles[0]
            print(f"Title: {article.get('title')}")
            print(f"Source: {article.get('source')}")
            print(f"Category: {article.get('category')}")
            print(f"External URL: {article.get('external_url')}")
        
    except Exception as e:
        print(f"Error testing news service: {e}")

async def test_mixed_content():
    """Test the mixed content service"""
    print("\nTesting Mixed Content Service...")
    print(f"Posts ratio: {settings.posts_ratio}")
    print(f"Min posts per page: {settings.min_posts_per_page}")
    print(f"Max posts per page: {settings.max_posts_per_page}")
    
    try:
        result = await mixed_content_service.get_mixed_content(
            page=1,
            size=10,
            user_id=None
        )
        
        print(f"Mixed content result:")
        print(f"- Total items: {len(result.items)}")
        print(f"- Page: {result.page}")
        print(f"- Size: {result.size}")
        print(f"- Has more: {result.has_more}")
        
        # Count posts vs news
        posts_count = sum(1 for item in result.items if item.get('source') == 'post')
        news_count = sum(1 for item in result.items if item.get('source') == 'news')
        
        print(f"- Posts: {posts_count}")
        print(f"- News: {news_count}")
        
        if result.items:
            print("\nSample items:")
            for i, item in enumerate(result.items[:3]):
                print(f"{i+1}. [{item.get('source', 'unknown')}] {item.get('title', 'No title')}")
        
    except Exception as e:
        print(f"Error testing mixed content service: {e}")

async def main():
    """Main test function"""
    print("=== CivicPulse Mixed Content Test ===")
    
    await test_news_service()
    await test_mixed_content()
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(main())
