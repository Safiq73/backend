#!/usr/bin/env python3
"""
Simple WebSocket listener for testing real-time events
"""

import asyncio
import json
import websockets
from datetime import datetime

async def listen_for_realtime_updates():
    """Connect and listen for real-time search updates"""
    url = "ws://localhost:8000/api/v1/ws/search"
    
    print(f"🔗 Connecting to {url}...")
    
    try:
        async with websockets.connect(url) as websocket:
            print("✅ Connected! Waiting for connection status...")
            
            # Wait for connection status
            message = await websocket.recv()
            data = json.loads(message)
            print(f"📥 Connection confirmed: {data.get('connection_id')}")
            
            # Subscribe to multiple queries that might get updates
            queries = ["john", "politics", "community", "update"]
            
            for query in queries:
                subscription_id = f"listener_sub_{query}_{datetime.now().timestamp()}"
                subscribe_message = {
                    "type": "subscribe",
                    "data": {
                        "subscription_id": subscription_id,
                        "query": query,
                        "entity_types": ["user", "post", "representative"],
                        "filters": {}
                    }
                }
                
                await websocket.send(json.dumps(subscribe_message))
                print(f"📤 Subscribed to '{query}' updates")
                
                # Wait for confirmation
                response = await websocket.recv()
                confirm_data = json.loads(response)
                if confirm_data.get("type") == "subscription_confirmed":
                    print(f"✅ Subscription confirmed for '{query}'")
            
            print("\n👂 Listening for real-time updates... (Press Ctrl+C to stop)")
            print("🎯 Run 'python3 simulate_realtime_events.py' in another terminal to see updates!")
            print("-" * 60)
            
            # Listen indefinitely
            update_count = 0
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    msg_type = data.get("type", "unknown")
                    
                    if msg_type == "batch_update":
                        events = data.get("events", [])
                        update_count += len(events)
                        
                        print(f"\n🎉 REAL-TIME UPDATE BATCH ({len(events)} events)")
                        print(f"⏰ Timestamp: {data.get('timestamp')}")
                        
                        for i, event in enumerate(events, 1):
                            print(f"\n   📋 Event {i}:")
                            print(f"      Type: {event['event_type']}")
                            print(f"      Entity: {event['entity_type']} (ID: {event['entity_id']})")
                            print(f"      Queries: {', '.join(event['affected_queries'])}")
                            print(f"      Relevance: {event.get('relevance_score', 'N/A')}")
                            
                            # Show entity-specific data
                            entity_data = event.get('data', {})
                            if event['entity_type'] == 'user':
                                print(f"      User: {entity_data.get('full_name', 'N/A')} (@{entity_data.get('username', 'N/A')})")
                            elif event['entity_type'] == 'post':
                                print(f"      Post: {entity_data.get('title', 'N/A')}")
                            elif event['entity_type'] == 'representative':
                                print(f"      Rep: {entity_data.get('full_name', 'N/A')} ({entity_data.get('office', 'N/A')})")
                        
                        print(f"\n📊 Total updates received so far: {update_count}")
                        print("-" * 60)
                    
                    elif msg_type == "pong":
                        print("🏓 Heartbeat received")
                    
                    elif msg_type in ["subscription_confirmed", "connection_status"]:
                        # Already handled these
                        pass
                    
                    else:
                        print(f"📥 Other message: {msg_type}")
                
                except websockets.exceptions.ConnectionClosed:
                    print("❌ Connection closed")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
                    break
                    
    except Exception as e:
        print(f"❌ Failed to connect: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(listen_for_realtime_updates())
    except KeyboardInterrupt:
        print("\n👋 Stopped listening for updates")
    except Exception as e:
        print(f"\n❌ Error: {e}")
