#!/usr/bin/env python3
"""
Database Activity Simulator for Real-time Search Testing
Simulates database changes to trigger WebSocket events
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.websocket.connection_manager import SearchUpdateEvent, EventType, EntityType, connection_manager
from datetime import datetime

async def simulate_user_updates():
    """Simulate user creation and updates"""
    print("🧑 Simulating user updates...")
    
    # Simulate new user
    user_event = SearchUpdateEvent(
        event_type=EventType.NEW_RESULT,
        entity_type=EntityType.USER,
        entity_id="user_123",
        data={
            "id": "user_123",
            "username": "john_doe",
            "full_name": "John Doe",
            "bio": "Community organizer interested in local politics",
            "updated_at": datetime.utcnow().isoformat()
        },
        affected_queries=["john", "doe", "politics", "community", "organizer"],
        timestamp=datetime.utcnow(),
        relevance_score=0.85,
        metadata={"table": "users", "simulation": True}
    )
    
    await connection_manager.broadcast_search_update(user_event)
    print("✅ Broadcasted user creation event")
    
    await asyncio.sleep(2)
    
    # Simulate user update
    user_update_event = SearchUpdateEvent(
        event_type=EventType.UPDATED_RESULT,
        entity_type=EntityType.USER,
        entity_id="user_123",
        data={
            "id": "user_123",
            "username": "john_doe",
            "full_name": "John Doe",
            "bio": "Experienced community organizer and political activist",
            "updated_at": datetime.utcnow().isoformat()
        },
        affected_queries=["john", "doe", "politics", "community", "activist"],
        timestamp=datetime.utcnow(),
        relevance_score=0.90,
        metadata={"table": "users", "simulation": True}
    )
    
    await connection_manager.broadcast_search_update(user_update_event)
    print("✅ Broadcasted user update event")

async def simulate_post_updates():
    """Simulate post creation"""
    print("📝 Simulating post updates...")
    
    # Simulate new post
    post_event = SearchUpdateEvent(
        event_type=EventType.NEW_RESULT,
        entity_type=EntityType.POST,
        entity_id="post_456",
        data={
            "id": "post_456",
            "title": "Community Meeting on Local Politics",
            "content": "Join us for an important community discussion about upcoming local elections and policy changes...",
            "author_id": "user_123",
            "author_username": "john_doe",
            "author_name": "John Doe",
            "category": "politics",
            "updated_at": datetime.utcnow().isoformat()
        },
        affected_queries=["community", "politics", "meeting", "local", "elections"],
        timestamp=datetime.utcnow(),
        relevance_score=0.92,
        metadata={"table": "posts", "category": "politics", "simulation": True}
    )
    
    await connection_manager.broadcast_search_update(post_event)
    print("✅ Broadcasted post creation event")

async def simulate_representative_updates():
    """Simulate representative updates"""
    print("🏛️ Simulating representative updates...")
    
    # Simulate representative update
    rep_event = SearchUpdateEvent(
        event_type=EventType.UPDATED_RESULT,
        entity_type=EntityType.REPRESENTATIVE,
        entity_id="rep_789",
        data={
            "id": "rep_789",
            "full_name": "Jane Smith",
            "party": "Independent",
            "office": "City Council Member",
            "jurisdiction": "Springfield City",
            "updated_at": datetime.utcnow().isoformat()
        },
        affected_queries=["jane", "smith", "council", "springfield", "independent"],
        timestamp=datetime.utcnow(),
        relevance_score=0.88,
        metadata={"table": "representatives", "party": "Independent", "simulation": True}
    )
    
    await connection_manager.broadcast_search_update(rep_event)
    print("✅ Broadcasted representative update event")

async def simulate_engagement_updates():
    """Simulate engagement updates"""
    print("💖 Simulating engagement updates...")
    
    # Simulate post likes
    engagement_event = SearchUpdateEvent(
        event_type=EventType.ENGAGEMENT_UPDATE,
        entity_type=EntityType.POST,
        entity_id="post_456",
        data={
            "metric_type": "likes",
            "value": 15,
            "entity_id": "post_456"
        },
        affected_queries=["community", "politics", "meeting"],
        timestamp=datetime.utcnow(),
        relevance_score=0.7,
        metadata={"metric": "likes", "engagement": True, "simulation": True}
    )
    
    await connection_manager.broadcast_search_update(engagement_event)
    print("✅ Broadcasted engagement update event")
    
    await asyncio.sleep(1)
    
    # Simulate user followers
    user_engagement_event = SearchUpdateEvent(
        event_type=EventType.ENGAGEMENT_UPDATE,
        entity_type=EntityType.USER,
        entity_id="user_123",
        data={
            "metric_type": "followers",
            "value": 25,
            "entity_id": "user_123"
        },
        affected_queries=["john", "doe", "politics"],
        timestamp=datetime.utcnow(),
        relevance_score=0.6,
        metadata={"metric": "followers", "engagement": True, "simulation": True}
    )
    
    await connection_manager.broadcast_search_update(user_engagement_event)
    print("✅ Broadcasted user engagement update event")

async def simulate_trending_updates():
    """Simulate trending search updates"""
    print("📈 Simulating trending updates...")
    
    trending_event = SearchUpdateEvent(
        event_type=EventType.SEARCH_TRENDING,
        entity_type=EntityType.USER,  # This could be any entity type
        entity_id="trending_query",
        data={
            "trending_queries": ["politics", "community", "elections"],
            "popularity_scores": [0.95, 0.88, 0.82]
        },
        affected_queries=["politics", "community", "elections", "trending"],
        timestamp=datetime.utcnow(),
        relevance_score=0.9,
        metadata={"trending": True, "simulation": True}
    )
    
    await connection_manager.broadcast_search_update(trending_event)
    print("✅ Broadcasted trending update event")

async def run_simulation():
    """Run complete simulation of database activity"""
    print("🎬 Starting Real-time Search Simulation")
    print("=" * 50)
    
    # Get current connection stats
    stats = connection_manager.get_connection_stats()
    print(f"📊 Current connections: {stats['total_connections']}")
    print(f"📊 Current subscriptions: {stats['total_subscriptions']}")
    
    if stats['total_connections'] == 0:
        print("⚠️  No active WebSocket connections. Start the test client first!")
        return
    
    print("\n🚀 Starting simulation events...")
    
    # Run simulations with delays
    simulations = [
        simulate_user_updates,
        simulate_post_updates,
        simulate_representative_updates,
        simulate_engagement_updates,
        simulate_trending_updates
    ]
    
    for i, simulation in enumerate(simulations):
        print(f"\n--- Simulation {i+1}/{len(simulations)} ---")
        await simulation()
        await asyncio.sleep(3)  # Wait between simulations
    
    print("\n✨ Simulation complete!")
    print("📊 Check your WebSocket client for real-time updates!")

if __name__ == "__main__":
    try:
        asyncio.run(run_simulation())
    except KeyboardInterrupt:
        print("\n👋 Simulation interrupted by user")
    except Exception as e:
        print(f"\n❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
