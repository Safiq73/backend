"""
Simple test to debug NewsAPI issue
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import settings

async def test_basic_newsapi():
    """Test basic NewsAPI connectivity"""
    print("=== Basic NewsAPI Test ===")
    print(f"API Key: {settings.newsapi_key[:10]}..." if settings.newsapi_key else "No API key")
    print(f"Country: {settings.newsapi_country}")
    
    import httpx
    
    try:
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            "country": settings.newsapi_country,
            "apiKey": settings.newsapi_key,
            "pageSize": 5,
            "page": 1
        }
        
        print(f"URL: {url}")
        print(f"Params: {params}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"API Status: {data.get('status')}")
                print(f"Total Results: {data.get('totalResults', 0)}")
                articles = data.get('articles', [])
                print(f"Articles Count: {len(articles)}")
                
                if articles:
                    print("\nFirst article:")
                    article = articles[0]
                    print(f"Title: {article.get('title')}")
                    print(f"Description: {article.get('description')}")
                    print(f"Source: {article.get('source', {}).get('name')}")
            else:
                print(f"Error Response: {response.text}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_basic_newsapi())
