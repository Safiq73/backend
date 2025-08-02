"""
Test script for WebSocket Real-time Search functionality
Run this to test the WebSocket endpoints and database monitoring
"""

import asyncio
import json
import logging
from datetime import datetime
from app.websocket.connection_manager import connection_manager
from app.websocket.search_events import search_event_generator, SearchUpdateEvent, EventType, EntityType
from app.db.database import get_db
from sqlalchemy import text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_search_event_generation():
    """Test generating search events"""
    logger.info("Testing search event generation...")
    
    # Create a test event
    test_event = SearchUpdateEvent(
        event_type=EventType.NEW_RESULT,
        entity_type=EntityType.USER,
        entity_id="test-user-123",
        data={
            "id": "test-user-123",
            "username": "testuser",
            "full_name": "Test User",
            "bio": "This is a test user for WebSocket functionality"
        },
        affected_queries=["test", "user", "websocket"],
        timestamp=datetime.utcnow(),
        relevance_score=0.8,
        metadata={"source": "test_script"}
    )
    
    # Broadcast the event
    await connection_manager.broadcast_search_update(test_event)
    logger.info(f"Broadcasted test event: {test_event.event_type}")
    
    return test_event

async def test_database_monitoring():
    """Test database change monitoring"""
    logger.info("Testing database monitoring...")
    
    try:
        # Start monitoring
        monitoring_task = asyncio.create_task(
            search_event_generator.start_monitoring()
        )
        
        logger.info("Database monitoring started")
        
        # Let it run for a few seconds
        await asyncio.sleep(10)
        
        # Stop monitoring
        await search_event_generator.stop_monitoring()
        logger.info("Database monitoring stopped")
        
        # Cancel the task
        monitoring_task.cancel()
        
    except Exception as e:
        logger.error(f"Error in database monitoring test: {e}")

async def test_connection_stats():
    """Test connection statistics"""
    logger.info("Testing connection statistics...")
    
    stats = connection_manager.get_connection_stats()
    logger.info(f"Connection Stats: {json.dumps(stats, indent=2)}")
    
    return stats

async def create_test_data():
    """Create some test data in the database"""
    logger.info("Creating test data...")
    
    try:
        async for db in get_db():
            # Insert a test user
            user_query = text("""
                INSERT INTO users (username, email, full_name, bio, password_hash, is_active)
                VALUES (:username, :email, :full_name, :bio, :password_hash, :is_active)
                ON CONFLICT (username) DO UPDATE SET
                    updated_at = CURRENT_TIMESTAMP,
                    bio = EXCLUDED.bio
                RETURNING id, username, full_name
            """)
            
            result = await db.execute(user_query, {
                "username": f"websocket_test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "email": f"test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}@example.com",
                "full_name": "WebSocket Test User",
                "bio": "This user was created to test real-time WebSocket search functionality",
                "password_hash": "dummy_hash",
                "is_active": True
            })
            
            user = result.fetchone()
            await db.commit()
            
            if user:
                logger.info(f"Created test user: {user.username} (ID: {user.id})")
                return user
            
            break
            
    except Exception as e:
        logger.error(f"Error creating test data: {e}")
        return None

async def simulate_search_activity():
    """Simulate search activity for testing"""
    logger.info("Simulating search activity...")
    
    # Create some test events
    events = [
        SearchUpdateEvent(
            event_type=EventType.NEW_RESULT,
            entity_type=EntityType.POST,
            entity_id="post-001",
            data={"title": "New Community Initiative", "content": "A new post about community initiatives"},
            affected_queries=["community", "initiative", "new"],
            timestamp=datetime.utcnow(),
            relevance_score=0.9
        ),
        SearchUpdateEvent(
            event_type=EventType.UPDATED_RESULT,
            entity_type=EntityType.REPRESENTATIVE,
            entity_id="rep-001",
            data={"full_name": "John Doe", "party": "Independent", "office": "Mayor"},
            affected_queries=["john", "doe", "mayor", "independent"],
            timestamp=datetime.utcnow(),
            relevance_score=0.7
        ),
        SearchUpdateEvent(
            event_type=EventType.ENGAGEMENT_UPDATE,
            entity_type=EntityType.POST,
            entity_id="post-002",
            data={"metric_type": "likes", "value": 25},
            affected_queries=["popular", "trending"],
            timestamp=datetime.utcnow(),
            relevance_score=0.6
        )
    ]
    
    # Broadcast events with delays
    for i, event in enumerate(events):
        await asyncio.sleep(2)  # 2-second delay between events
        await connection_manager.broadcast_search_update(event)
        logger.info(f"Broadcasted event {i+1}/{len(events)}: {event.event_type}")

async def test_websocket_performance():
    """Test WebSocket performance with multiple events"""
    logger.info("Testing WebSocket performance...")
    
    start_time = datetime.utcnow()
    
    # Generate many events quickly
    tasks = []
    for i in range(50):
        event = SearchUpdateEvent(
            event_type=EventType.NEW_RESULT,
            entity_type=EntityType.USER,
            entity_id=f"perf-test-{i}",
            data={"username": f"user{i}", "full_name": f"Performance Test User {i}"},
            affected_queries=[f"user{i}", "performance", "test"],
            timestamp=datetime.utcnow(),
            relevance_score=0.5
        )
        
        task = connection_manager.broadcast_search_update(event)
        tasks.append(task)
    
    # Wait for all events to be processed
    await asyncio.gather(*tasks)
    
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    logger.info(f"Performance test completed: 50 events in {duration:.2f} seconds")
    logger.info(f"Rate: {50/duration:.2f} events/second")

async def main():
    """Main test function"""
    logger.info("Starting WebSocket Real-time Search Tests")
    logger.info("=" * 60)
    
    try:
        # Test 1: Connection Statistics
        logger.info("\n1. Testing Connection Statistics")
        await test_connection_stats()
        
        # Test 2: Search Event Generation
        logger.info("\n2. Testing Search Event Generation")
        await test_search_event_generation()
        
        # Test 3: Create Test Data
        logger.info("\n3. Creating Test Data")
        test_user = await create_test_data()
        
        # Test 4: Simulate Search Activity
        logger.info("\n4. Simulating Search Activity")
        await simulate_search_activity()
        
        # Test 5: Performance Test
        logger.info("\n5. Testing Performance")
        await test_websocket_performance()
        
        # Test 6: Database Monitoring (short test)
        logger.info("\n6. Testing Database Monitoring")
        await test_database_monitoring()
        
        # Final statistics
        logger.info("\n7. Final Statistics")
        final_stats = await test_connection_stats()
        
        logger.info("\n" + "=" * 60)
        logger.info("WebSocket Real-time Search Tests Completed Successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        raise

if __name__ == "__main__":
    # Run the tests
    asyncio.run(main())
