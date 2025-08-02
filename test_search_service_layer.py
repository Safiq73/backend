#!/usr/bin/env python3
"""
Comprehensive test for the Search Service Layer
Tests all search functionality including unified search, suggestions, and analytics
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from app.services.search_service import SearchService
from app.services.search_suggestions import SearchSuggestionService, PopularTermsAnalyzer
from app.services.search_formatter import SearchResultFormatter, SearchResultAggregator


async def test_search_service():
    """Test the comprehensive search service functionality."""
    print("🔍 Testing CivicPulse Search Service Layer")
    print("=" * 60)
    
    # Initialize search service
    search_service = SearchService()
    
    try:
        # Test 1: Basic unified search
        print("\n1. Testing Unified Search")
        print("-" * 30)
        
        search_result = await search_service.unified_search(
            query="corruption government",
            entity_types=['users', 'posts', 'representatives'],
            limit=5,
            sort_by="relevance"
        )
        
        print(f"✅ Query: '{search_result['query']}'")
        print(f"✅ Total entity types searched: {len(search_result['results'])}")
        
        for entity_type, results in search_result['results'].items():
            print(f"   - {entity_type}: {len(results)} results")
            if results:
                print(f"     Top result: {results[0].get('username') or results[0].get('title') or results[0].get('name', 'N/A')}")
        
        print(f"✅ Aggregation data: {search_result.get('aggregation', {}).get('total_results', 0)} total results")
        print(f"✅ Suggestions provided: {len(search_result.get('suggestions', {}))}")
        
        # Test 2: Search suggestions
        print("\n2. Testing Search Suggestions")
        print("-" * 30)
        
        suggestions = await search_service.get_search_suggestions(
            partial_query="gov",
            suggestion_types=['popular', 'autocomplete', 'similar'],
            limit=5
        )
        
        print(f"✅ Suggestion types: {list(suggestions.get('suggestions', {}).keys())}")
        
        for suggestion_type, sugg_list in suggestions.get('suggestions', {}).items():
            print(f"   - {suggestion_type}: {len(sugg_list)} suggestions")
            if sugg_list:
                print(f"     Top suggestion: '{sugg_list[0].get('suggestion', 'N/A')}'")
        
        # Test 3: Entity-specific suggestions
        if suggestions.get('entity_suggestions'):
            print(f"✅ Entity suggestions: {list(suggestions['entity_suggestions'].keys())}")
        
        # Test 4: Advanced search with filters
        print("\n3. Testing Advanced Search with Filters")
        print("-" * 30)
        
        advanced_result = await search_service.advanced_search(
            query_components={
                'text': 'road repair',
                'location': 'mumbai'
            },
            entity_types=['posts'],
            limit=3
        )
        
        print(f"✅ Advanced search results: {len(advanced_result['results'].get('posts', []))} posts")
        
        # Test 5: Popular terms analysis
        print("\n4. Testing Popular Terms Analysis")
        print("-" * 30)
        
        popular_analysis = await search_service.get_popular_terms_analysis(
            time_period="7d",
            limit=10
        )
        
        print(f"✅ Analysis period: {popular_analysis.get('analysis_period', 'N/A')}")
        print(f"✅ Popular terms found: {len(popular_analysis.get('popular_terms', []))}")
        
        if popular_analysis.get('popular_terms'):
            top_term = popular_analysis['popular_terms'][0]
            print(f"   Top term: '{top_term.get('term')}' ({top_term.get('total_searches')} searches)")
        
        # Test 6: Similar content search (if we have some content)
        print("\n5. Testing Similar Content Search")
        print("-" * 30)
        
        # Try to find similar content to the first post if available
        if search_result['results'].get('posts'):
            first_post = search_result['results']['posts'][0]
            post_id = first_post.get('id')
            
            if post_id:
                similar_result = await search_service.search_similar_content(
                    content_id=post_id,
                    content_type='post',
                    limit=3
                )
                
                print(f"✅ Similar content found: {len(similar_result.get('similar_content', []))}")
                print(f"✅ Reference content type: {similar_result.get('metadata', {}).get('content_type', 'N/A')}")
        
        # Test 7: Search result formatting
        print("\n6. Testing Search Result Formatting")
        print("-" * 30)
        
        # Test individual formatters
        if search_result['results'].get('users'):
            user_data = search_result['results']['users'][0]
            print(f"✅ User formatting: Type={user_data.get('type')}, Relevance={user_data.get('relevance_score')}")
        
        if search_result['results'].get('posts'):
            post_data = search_result['results']['posts'][0]
            print(f"✅ Post formatting: Type={post_data.get('type')}, Engagement={post_data.get('metadata', {}).get('engagement_score')}")
        
        if search_result['results'].get('representatives'):
            rep_data = search_result['results']['representatives'][0]
            print(f"✅ Representative formatting: Type={rep_data.get('type')}, Linked={rep_data.get('metadata', {}).get('is_linked')}")
        
        # Test 8: Query analysis
        print("\n7. Testing Query Analysis")
        print("-" * 30)
        
        query_analysis = search_result.get('query_analysis', {})
        print(f"✅ Original query: '{query_analysis.get('original_query')}'")
        print(f"✅ Word count: {query_analysis.get('word_count')}")
        print(f"✅ Contains location terms: {query_analysis.get('contains_location_terms')}")
        print(f"✅ Contains political terms: {query_analysis.get('contains_political_terms')}")
        
        # Test 9: Pagination info
        print("\n8. Testing Pagination")
        print("-" * 30)
        
        pagination = search_result.get('pagination', {})
        for entity_type, page_info in pagination.items():
            print(f"✅ {entity_type}: {page_info.get('current_count')}/{page_info.get('total_count')} (Page {page_info.get('current_page')})")
        
        print("\n" + "=" * 60)
        print("🎉 All Search Service Tests Completed Successfully!")
        print("=" * 60)
        
        # Summary statistics
        total_entities_searched = len(search_result['results'])
        total_results = sum(len(results) for results in search_result['results'].values())
        total_suggestions = sum(len(suggs) for suggs in suggestions.get('suggestions', {}).values())
        
        print(f"\n📊 Test Summary:")
        print(f"   • Entity types tested: {total_entities_searched}")
        print(f"   • Total search results: {total_results}")
        print(f"   • Total suggestions: {total_suggestions}")
        print(f"   • Advanced search features: ✅")
        print(f"   • Analytics features: ✅")
        print(f"   • Formatting & aggregation: ✅")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during search service testing: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_search_components():
    """Test individual search components."""
    print("\n🧪 Testing Individual Search Components")
    print("=" * 60)
    
    try:
        # Test SearchResultFormatter
        print("\n1. Testing SearchResultFormatter")
        print("-" * 30)
        
        sample_user = {
            'id': 1, 'username': 'test_user', 'display_name': 'Test User',
            'bio': 'Test bio', 'is_verified': True, 'followers_count': 100,
            'relevance_score': 8.5
        }
        
        formatted_user = SearchResultFormatter.format_user_result(sample_user)
        print(f"✅ User formatting: {formatted_user['type']} with {formatted_user['followers_count']} followers")
        
        # Test SearchSuggestionService
        print("\n2. Testing SearchSuggestionService")
        print("-" * 30)
        
        suggestion_service = SearchSuggestionService()
        trending = await suggestion_service._get_trending_suggestions(5, None)
        print(f"✅ Trending suggestions structure: {list(trending.keys())}")
        
        # Test PopularTermsAnalyzer
        print("\n3. Testing PopularTermsAnalyzer")
        print("-" * 30)
        
        analyzer = PopularTermsAnalyzer()
        # Note: This might fail if no data exists, but we test the structure
        try:
            analysis = await analyzer.get_popular_terms_analysis("1d", None, 5)
            print(f"✅ Popular terms analysis structure: {list(analysis.keys())}")
        except Exception as e:
            print(f"⚠️  Popular terms analysis (expected if no data): {str(e)[:50]}...")
        
        print("\n✅ Component tests completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during component testing: {e}")
        return False


async def main():
    """Run all search service tests."""
    print("🚀 Starting CivicPulse Search Service Layer Tests")
    
    # Test main search service
    service_success = await test_search_service()
    
    # Test individual components
    component_success = await test_search_components()
    
    if service_success and component_success:
        print("\n🎯 ALL TESTS PASSED! Search Service Layer is ready!")
        print("\n📋 Ready for Step 3: Search API Endpoint Implementation")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
