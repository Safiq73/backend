#!/usr/bin/env python3
"""
WebSocket Test Client for Real-time Search
Tests WebSocket connectivity and real-time search updates
"""

import asyncio
import json
import websockets
from datetime import datetime

class WebSocketTestClient:
    def __init__(self, url="ws://localhost:8000/api/v1/ws/search"):
        self.url = url
        self.websocket = None
        
    async def connect(self):
        """Connect to WebSocket server"""
        try:
            print(f"🔗 Connecting to {self.url}...")
            self.websocket = await websockets.connect(self.url)
            print("✅ Connected successfully!")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def send_message(self, message):
        """Send message to WebSocket server"""
        if self.websocket:
            await self.websocket.send(json.dumps(message))
            print(f"📤 Sent: {message}")
    
    async def receive_message(self):
        """Receive message from WebSocket server"""
        if self.websocket:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                print(f"📥 Received: {data}")
                return data
            except Exception as e:
                print(f"❌ Error receiving message: {e}")
                return None
    
    async def subscribe_to_search(self, query, entity_types=None):
        """Subscribe to real-time search updates"""
        if entity_types is None:
            entity_types = ["user", "post", "representative"]
        
        subscription_id = f"test_sub_{datetime.now().timestamp()}"
        
        subscribe_message = {
            "type": "subscribe",
            "data": {
                "subscription_id": subscription_id,
                "query": query,
                "entity_types": entity_types,
                "filters": {}
            }
        }
        
        await self.send_message(subscribe_message)
        return subscription_id
    
    async def ping(self):
        """Send ping to server"""
        ping_message = {
            "type": "ping",
            "data": {}
        }
        await self.send_message(ping_message)
    
    async def get_stats(self):
        """Request connection statistics"""
        stats_message = {
            "type": "get_stats",
            "data": {}
        }
        await self.send_message(stats_message)
    
    async def listen_for_updates(self, duration=30):
        """Listen for real-time updates"""
        print(f"👂 Listening for updates for {duration} seconds...")
        
        start_time = asyncio.get_event_loop().time()
        update_count = 0
        
        while asyncio.get_event_loop().time() - start_time < duration:
            try:
                # Wait for message with timeout
                message = await asyncio.wait_for(
                    self.receive_message(), 
                    timeout=1.0
                )
                
                if message:
                    msg_type = message.get("type", "unknown")
                    if msg_type == "batch_update":
                        events = message.get("events", [])
                        update_count += len(events)
                        print(f"🎯 Received {len(events)} search updates!")
                        
                        for event in events:
                            print(f"   • {event['event_type']} - {event['entity_type']}:{event['entity_id']}")
                    
                    elif msg_type == "subscription_confirmed":
                        print(f"✅ Subscription confirmed: {message.get('subscription_id')}")
                    
                    elif msg_type == "connection_status":
                        print(f"🔗 Connection status: {message.get('status')}")
                    
                    elif msg_type == "pong":
                        print("🏓 Pong received!")
                    
                    elif msg_type == "stats":
                        stats = message.get("data", {})
                        print(f"📊 Stats: {stats['total_connections']} connections, {stats['total_subscriptions']} subscriptions")
                        
            except asyncio.TimeoutError:
                # Timeout is expected, continue listening
                continue
            except Exception as e:
                print(f"❌ Error while listening: {e}")
                break
        
        print(f"📈 Received {update_count} total updates during {duration}s listening period")
        return update_count
    
    async def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.websocket:
            await self.websocket.close()
            print("👋 Disconnected")

async def test_basic_connection():
    """Test basic WebSocket connection"""
    print("\n🧪 Testing Basic WebSocket Connection")
    print("=" * 50)
    
    client = WebSocketTestClient()
    
    # Test connection
    connected = await client.connect()
    if not connected:
        return False
    
    # Wait for connection status message
    await asyncio.sleep(1)
    await client.receive_message()
    
    # Test ping
    await client.ping()
    await asyncio.sleep(0.5)
    await client.receive_message()
    
    # Test stats
    await client.get_stats()
    await asyncio.sleep(0.5)
    await client.receive_message()
    
    await client.disconnect()
    return True

async def test_search_subscription():
    """Test search subscription functionality"""
    print("\n🔍 Testing Search Subscription")
    print("=" * 50)
    
    client = WebSocketTestClient()
    
    # Connect
    connected = await client.connect()
    if not connected:
        return False
    
    # Wait for connection confirmation
    await asyncio.sleep(1)
    await client.receive_message()
    
    # Subscribe to a search query
    subscription_id = await client.subscribe_to_search("john", ["user"])
    
    # Wait for subscription confirmation
    await asyncio.sleep(1)
    await client.receive_message()
    
    # Listen for updates
    update_count = await client.listen_for_updates(10)
    
    await client.disconnect()
    return update_count > 0

async def test_multiple_subscriptions():
    """Test multiple search subscriptions"""
    print("\n🔗 Testing Multiple Subscriptions")
    print("=" * 50)
    
    client = WebSocketTestClient()
    
    # Connect
    connected = await client.connect()
    if not connected:
        return False
    
    # Wait for connection confirmation
    await asyncio.sleep(1)
    await client.receive_message()
    
    # Subscribe to multiple queries
    queries = ["politics", "community", "update"]
    subscription_ids = []
    
    for query in queries:
        sub_id = await client.subscribe_to_search(query, ["user", "post", "representative"])
        subscription_ids.append(sub_id)
        await asyncio.sleep(0.5)
        await client.receive_message()  # Wait for confirmation
    
    print(f"✅ Created {len(subscription_ids)} subscriptions")
    
    # Listen for updates
    update_count = await client.listen_for_updates(15)
    
    await client.disconnect()
    return update_count > 0

async def main():
    """Run all WebSocket tests"""
    print("🚀 Starting WebSocket Real-time Search Tests")
    print("=" * 60)
    
    tests = [
        ("Basic Connection", test_basic_connection),
        ("Search Subscription", test_search_subscription),
        ("Multiple Subscriptions", test_multiple_subscriptions)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n🏃 Running: {test_name}")
            result = await test_func()
            results[test_name] = "✅ PASSED" if result else "❌ FAILED"
            print(f"Result: {results[test_name]}")
        except Exception as e:
            results[test_name] = f"❌ ERROR: {e}"
            print(f"Result: {results[test_name]}")
        
        # Wait between tests
        await asyncio.sleep(2)
    
    # Print summary
    print("\n" + "=" * 60)
    print("🏁 TEST SUMMARY")
    print("=" * 60)
    
    for test_name, result in results.items():
        print(f"{test_name:.<30} {result}")
    
    passed_tests = sum(1 for result in results.values() if "PASSED" in result)
    total_tests = len(results)
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! WebSocket real-time search is working!")
    else:
        print("⚠️  Some tests failed. Check the logs above.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
