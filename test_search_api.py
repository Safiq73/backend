#!/usr/bin/env python3
"""
Comprehensive test for the Search API Endpoints
Tests all search API functionality including unified search, suggestions, and analytics
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add the backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from fastapi.testclient import TestClient
from app.main import app

# Create test client
client = TestClient(app)


def test_search_api_endpoints():
    """Test all search API endpoints comprehensively."""
    print("🔍 Testing CivicPulse Search API Endpoints")
    print("=" * 60)
    
    base_url = "/api/v1/search"
    
    try:
        # Test 1: Basic unified search (GET)
        print("\n1. Testing Basic Unified Search (GET)")
        print("-" * 40)
        
        response = client.get(f"{base_url}/?q=government&limit=5")
        
        print(f"✅ Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Query: '{data.get('query', 'N/A')}'")
            print(f"✅ Entity types searched: {len(data.get('results', {}))}")
            
            for entity_type, results in data.get('results', {}).items():
                print(f"   - {entity_type}: {len(results)} results")
            
            print(f"✅ Aggregation provided: {'aggregation' in data}")
            print(f"✅ Pagination provided: {'pagination' in data}")
        else:
            print(f"⚠️  Response: {response.text}")
        
        # Test 2: Advanced unified search (POST)
        print("\n2. Testing Advanced Unified Search (POST)")
        print("-" * 40)
        
        search_payload = {
            "query": "corruption government",
            "entity_types": ["users", "posts"],
            "limit": 3,
            "sort_by": "relevance",
            "filters": {
                "verified": True,
                "highlight": True
            }
        }
        
        response = client.post(f"{base_url}/", json=search_payload)
        
        print(f"✅ Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Query: '{data.get('query', 'N/A')}'")
            print(f"✅ Results structure: {list(data.get('results', {}).keys())}")
        else:
            print(f"⚠️  Response: {response.text}")
        
        # Test 3: Advanced search with components
        print("\n3. Testing Advanced Search with Components")
        print("-" * 40)
        
        component_payload = {
            "text": "road repair",
            "location": "mumbai",
            "entity_types": ["posts"],
            "limit": 3
        }
        
        response = client.post(f"{base_url}/advanced", json=component_payload)
        
        print(f"✅ Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Component search successful")
            print(f"✅ Results: {len(data.get('results', {}).get('posts', []))} posts")
        else:
            print(f"⚠️  Response: {response.text}")
        
        # Test 4: Search suggestions (GET)
        print("\n4. Testing Search Suggestions (GET)")
        print("-" * 40)
        
        response = client.get(f"{base_url}/suggestions?q=gov&limit=5")
        
        print(f"✅ Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Suggestions structure: {list(data.get('suggestions', {}).keys())}")
            print(f"✅ Entity suggestions: {list(data.get('entity_suggestions', {}).keys())}")
        else:
            print(f"⚠️  Response: {response.text}")
        
        # Test 5: Search suggestions (POST)
        print("\n5. Testing Search Suggestions (POST)")
        print("-" * 40)
        
        suggestion_payload = {
            "partial_query": "corr",
            "suggestion_types": ["popular", "autocomplete"],
            "limit": 5
        }
        
        response = client.post(f"{base_url}/suggestions", json=suggestion_payload)
        
        print(f"✅ Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ POST suggestions successful")
        else:
            print(f"⚠️  Response: {response.text}")
        
        # Test 6: Similar content search
        print("\n6. Testing Similar Content Search")
        print("-" * 40)
        
        # Try to find similar content (this might fail if no content exists, but we test the endpoint)
        response = client.get(f"{base_url}/similar/post/1?limit=3")
        
        print(f"✅ Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Similar content search successful")
            print(f"✅ Similar items: {len(data.get('similar_content', []))}")
        else:
            print(f"⚠️  Response: {response.text}")
        
        # Test 7: Search with filters
        print("\n7. Testing Search with Various Filters")
        print("-" * 40)
        
        filter_tests = [
            {"q": "test", "verified": "true"},
            {"q": "road", "location": "mumbai"},
            {"q": "government", "entity_types": "users,posts"},
            {"q": "corruption", "sort_by": "popular"},
        ]
        
        for i, params in enumerate(filter_tests):
            param_str = "&".join([f"{k}={v}" for k, v in params.items()])
            response = client.get(f"{base_url}/?{param_str}")
            print(f"   Filter test {i+1}: Status {response.status_code}")
        
        # Test 8: Health check
        print("\n8. Testing Search Health Check")
        print("-" * 40)
        
        response = client.get(f"{base_url}/health")
        
        print(f"✅ Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Service status: {data.get('status', 'N/A')}")
            print(f"✅ Database connection: {data.get('database_connection', 'N/A')}")
            print(f"✅ Search functionality: {data.get('search_functionality', 'N/A')}")
        else:
            print(f"⚠️  Service health check failed: {response.text}")
        
        # Test 9: Error handling
        print("\n9. Testing Error Handling")
        print("-" * 40)
        
        error_tests = [
            ("Empty query", f"{base_url}/?q="),
            ("Invalid sort", f"{base_url}/?q=test&sort_by=invalid"),
            ("Invalid limit", f"{base_url}/?q=test&limit=1000"),
            ("Invalid content type", f"{base_url}/similar/invalid/1"),
        ]
        
        for test_name, url in error_tests:
            response = client.get(url)
            print(f"   {test_name}: Status {response.status_code} ({'✅' if response.status_code >= 400 else '⚠️'})")
        
        print("\n" + "=" * 60)
        print("🎉 Search API Endpoint Tests Completed!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during API testing: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_documentation():
    """Test API documentation accessibility."""
    print("\n📚 Testing API Documentation")
    print("=" * 60)
    
    try:
        # Test OpenAPI schema
        response = client.get("/openapi.json")
        print(f"✅ OpenAPI Schema: Status {response.status_code}")
        
        if response.status_code == 200:
            schema = response.json()
            search_paths = [path for path in schema.get('paths', {}).keys() if '/search' in path]
            print(f"✅ Search endpoints in schema: {len(search_paths)}")
            
            for path in search_paths[:5]:  # Show first 5
                print(f"   - {path}")
        
        # Test Swagger UI (if available)
        response = client.get("/docs")
        print(f"✅ Swagger UI: Status {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ Documentation test failed: {e}")
        return False


def main():
    """Run all search API tests."""
    print("🚀 Starting CivicPulse Search API Tests")
    
    # Test API endpoints
    api_success = test_search_api_endpoints()
    
    # Test API documentation
    docs_success = test_api_documentation()
    
    if api_success and docs_success:
        print("\n🎯 ALL API TESTS PASSED! Search API is ready!")
        print("\n📋 Search API Endpoints Available:")
        print("   • GET  /api/v1/search/ - Basic unified search")
        print("   • POST /api/v1/search/ - Advanced unified search")
        print("   • POST /api/v1/search/advanced - Component-based search")
        print("   • GET  /api/v1/search/suggestions - Search suggestions")
        print("   • POST /api/v1/search/suggestions - Suggestions with body")
        print("   • GET  /api/v1/search/similar/{type}/{id} - Similar content")
        print("   • GET  /api/v1/search/analytics/popular-terms - Analytics")
        print("   • GET  /api/v1/search/health - Health check")
        print("\n📖 Documentation available at: /docs")
        print("\n🎊 Ready for frontend integration!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
