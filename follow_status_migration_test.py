#!/usr/bin/env python3
"""
Migration script to help transition from separate follow status API calls
to the new integrated follow status in posts API.

This script demonstrates the difference and helps validate the new functionality.
"""
import asyncio
import aiohttp
import json
import time
from typing import List, Dict, Any, Optional

API_BASE_URL = "http://localhost:8000/api/v1"

class FollowStatusMigrationTester:
    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    async def old_approach_multiple_calls(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Simulate the old approach with multiple API calls"""
        print("🔄 Testing OLD approach (multiple API calls)...")
        start_time = time.time()
        
        # Step 1: Get posts
        async with session.get(f"{API_BASE_URL}/posts?page=1&size=5", headers=self.headers) as response:
            if response.status != 200:
                raise Exception(f"Failed to get posts: {response.status}")
            posts_data = await response.json()
        
        posts = posts_data.get('items', [])
        total_calls = 1  # Initial posts call
        
        # Step 2: For each post, get follow status (N additional calls)
        for post in posts:
            author_id = post.get('author', {}).get('id')
            if author_id:
                try:
                    async with session.get(
                        f"{API_BASE_URL}/users/{author_id}/follow-status",
                        headers=self.headers
                    ) as follow_response:
                        if follow_response.status == 200:
                            follow_data = await follow_response.json()
                            post['follow_status'] = follow_data.get('data', {}).get('is_following', False)
                        else:
                            post['follow_status'] = None
                        total_calls += 1
                except Exception as e:
                    print(f"⚠️  Failed to get follow status for {author_id}: {e}")
                    post['follow_status'] = None
        
        end_time = time.time()
        
        result = {
            'method': 'old_multiple_calls',
            'total_api_calls': total_calls,
            'execution_time_ms': round((end_time - start_time) * 1000, 2),
            'posts_count': len(posts),
            'posts_with_follow_status': len([p for p in posts if 'follow_status' in p]),
            'sample_post': posts[0] if posts else None
        }
        
        print(f"   📊 API Calls: {total_calls}")
        print(f"   ⏱️  Time: {result['execution_time_ms']}ms")
        print(f"   📝 Posts: {len(posts)}")
        
        return result
    
    async def new_approach_single_call(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test the new integrated approach with single API call"""
        print("✨ Testing NEW approach (single API call)...")
        start_time = time.time()
        
        # Single API call with follow status included
        async with session.get(
            f"{API_BASE_URL}/posts?page=1&size=5&include_follow_status=true",
            headers=self.headers
        ) as response:
            if response.status != 200:
                raise Exception(f"Failed to get posts with follow status: {response.status}")
            posts_data = await response.json()
        
        end_time = time.time()
        posts = posts_data.get('items', [])
        
        result = {
            'method': 'new_single_call',
            'total_api_calls': 1,
            'execution_time_ms': round((end_time - start_time) * 1000, 2),
            'posts_count': len(posts),
            'posts_with_follow_status': len([p for p in posts if 'follow_status' in p]),
            'sample_post': posts[0] if posts else None
        }
        
        print(f"   📊 API Calls: 1")
        print(f"   ⏱️  Time: {result['execution_time_ms']}ms")
        print(f"   📝 Posts: {len(posts)}")
        
        return result
    
    async def test_individual_post_follow_status(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test follow status on individual post endpoint"""
        print("🎯 Testing individual post with follow status...")
        
        # First get a post ID
        async with session.get(f"{API_BASE_URL}/posts?page=1&size=1", headers=self.headers) as response:
            if response.status != 200:
                return {'error': 'Failed to get post for individual test'}
            data = await response.json()
            posts = data.get('items', [])
            if not posts:
                return {'error': 'No posts available for individual test'}
        
        post_id = posts[0]['id']
        
        # Test individual post with follow status
        start_time = time.time()
        async with session.get(
            f"{API_BASE_URL}/posts/{post_id}?include_follow_status=true",
            headers=self.headers
        ) as response:
            if response.status != 200:
                return {'error': f'Failed to get individual post: {response.status}'}
            post_data = await response.json()
        
        end_time = time.time()
        
        result = {
            'method': 'individual_post_with_follow_status',
            'post_id': post_id,
            'execution_time_ms': round((end_time - start_time) * 1000, 2),
            'has_follow_status': 'follow_status' in post_data.get('data', {}),
            'follow_status_value': post_data.get('data', {}).get('follow_status')
        }
        
        print(f"   📝 Post ID: {post_id}")
        print(f"   ⏱️  Time: {result['execution_time_ms']}ms")
        print(f"   ✅ Has follow status: {result['has_follow_status']}")
        
        return result
    
    async def compare_response_consistency(self, old_result: Dict, new_result: Dict) -> Dict[str, Any]:
        """Compare the consistency between old and new approaches"""
        print("🔍 Comparing response consistency...")
        
        old_post = old_result.get('sample_post', {})
        new_post = new_result.get('sample_post', {})
        
        if not old_post or not new_post:
            return {'error': 'No posts to compare'}
        
        # Compare basic post fields
        consistency_check = {
            'same_post_id': old_post.get('id') == new_post.get('id'),
            'same_title': old_post.get('title') == new_post.get('title'),
            'same_author': old_post.get('author', {}).get('id') == new_post.get('author', {}).get('id'),
            'both_have_follow_status': 'follow_status' in old_post and 'follow_status' in new_post,
            'same_follow_status': old_post.get('follow_status') == new_post.get('follow_status')
        }
        
        all_consistent = all(consistency_check.values())
        
        print(f"   ✅ Same post ID: {consistency_check['same_post_id']}")
        print(f"   ✅ Same title: {consistency_check['same_title']}")
        print(f"   ✅ Same author: {consistency_check['same_author']}")
        print(f"   ✅ Both have follow status: {consistency_check['both_have_follow_status']}")
        print(f"   ✅ Same follow status: {consistency_check['same_follow_status']}")
        print(f"   🎯 Overall consistent: {all_consistent}")
        
        return {
            'consistency_check': consistency_check,
            'overall_consistent': all_consistent,
            'old_follow_status': old_post.get('follow_status'),
            'new_follow_status': new_post.get('follow_status')
        }
    
    async def run_full_migration_test(self) -> Dict[str, Any]:
        """Run the complete migration test"""
        print("🚀 Starting Follow Status API Migration Test")
        print("=" * 60)
        
        async with aiohttp.ClientSession() as session:
            results = {}
            
            try:
                # Test old approach
                results['old_approach'] = await self.old_approach_multiple_calls(session)
                
                # Test new approach
                results['new_approach'] = await self.new_approach_single_call(session)
                
                # Test individual post
                results['individual_post'] = await self.test_individual_post_follow_status(session)
                
                # Compare consistency
                results['consistency'] = await self.compare_response_consistency(
                    results['old_approach'], 
                    results['new_approach']
                )
                
                # Calculate performance improvement
                old_time = results['old_approach']['execution_time_ms']
                new_time = results['new_approach']['execution_time_ms']
                old_calls = results['old_approach']['total_api_calls']
                new_calls = results['new_approach']['total_api_calls']
                
                improvement = {
                    'time_saved_ms': old_time - new_time,
                    'time_improvement_percent': round(((old_time - new_time) / old_time) * 100, 1) if old_time > 0 else 0,
                    'api_calls_reduced': old_calls - new_calls,
                    'api_calls_reduction_percent': round(((old_calls - new_calls) / old_calls) * 100, 1) if old_calls > 0 else 0
                }
                
                results['performance_improvement'] = improvement
                
                print("\n" + "=" * 60)
                print("📈 PERFORMANCE IMPROVEMENT SUMMARY")
                print("=" * 60)
                print(f"⏱️  Time saved: {improvement['time_saved_ms']}ms ({improvement['time_improvement_percent']}% faster)")
                print(f"📞 API calls reduced: {improvement['api_calls_reduced']} calls ({improvement['api_calls_reduction_percent']}% fewer)")
                print(f"🎯 Consistency: {'✅ PASSED' if results['consistency']['overall_consistent'] else '❌ FAILED'}")
                
            except Exception as e:
                print(f"❌ Test failed: {e}")
                results['error'] = str(e)
        
        return results


async def main():
    """Main function to run the migration test"""
    print("📋 Follow Status API Migration Tester")
    print("This script compares the old multiple-call approach with the new integrated approach")
    print()
    
    # You need to provide a valid JWT token for testing
    auth_token = input("🔑 Enter your JWT auth token (or press Enter to use placeholder): ").strip()
    
    if not auth_token:
        auth_token = "YOUR_JWT_TOKEN_HERE"
        print("⚠️  Using placeholder token - update this with a real token for actual testing")
    
    print(f"🌐 Testing against: {API_BASE_URL}")
    print()
    
    tester = FollowStatusMigrationTester(auth_token)
    
    try:
        results = await tester.run_full_migration_test()
        
        # Save results to file
        with open('follow_status_migration_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: follow_status_migration_results.json")
        
        print("\n" + "=" * 60)
        print("🎉 MIGRATION TEST COMPLETED!")
        print("=" * 60)
        print("✅ The new integrated follow status API is working correctly")
        print("🚀 You can now update your frontend to use the new approach")
        print("📝 See INTEGRATED_FOLLOW_STATUS_GUIDE.md for implementation details")
        
    except Exception as e:
        print(f"❌ Migration test failed: {e}")
        print("🔧 Please check your API server is running and token is valid")


if __name__ == "__main__":
    print("🧪 Follow Status API Migration Test")
    print("Make sure your backend server is running on localhost:8000")
    print()
    
    # Uncomment the line below to run the actual test
    # asyncio.run(main())
    
    print("To run this test:")
    print("1. Start your backend server")
    print("2. Get a valid JWT token")
    print("3. Uncomment the asyncio.run(main()) line")
    print("4. Run: python3 follow_status_migration_test.py")
