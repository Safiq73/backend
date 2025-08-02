#!/usr/bin/env python3
"""
Test WebSocket Disable Functionality
Verifies that WebSocket connections are properly rejected when disabled.
"""

import asyncio
import websockets
import json
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

async def test_websocket_disabled():
    """Test that WebSocket connections are rejected when service is disabled"""
    
    print("🧪 Testing WebSocket Disable Functionality...")
    print("=" * 50)
    
    # Test analytics WebSocket endpoint
    try:
        print("📡 Attempting to connect to analytics WebSocket...")
        uri = "ws://localhost:8000/ws/analytics"
        
        async with websockets.connect(uri) as websocket:
            print("❌ ERROR: Connection was accepted when it should be rejected!")
            return False
            
    except ConnectionClosedOK as e:
        print(f"✅ SUCCESS: Analytics WebSocket connection properly rejected")
        print(f"   Close code: {e.code}, Reason: {e.reason}")
        
    except ConnectionClosedError as e:
        print(f"✅ SUCCESS: Analytics WebSocket connection properly rejected")
        print(f"   Close code: {e.code}, Reason: {e.reason}")
        
    except ConnectionRefusedError:
        print("✅ SUCCESS: Connection refused (server not running or WebSocket disabled)")
        
    except Exception as e:
        print(f"⚠️  Connection failed with: {type(e).__name__}: {e}")
    
    print()
    
    # Test search WebSocket endpoint  
    try:
        print("🔍 Attempting to connect to search WebSocket...")
        uri = "ws://localhost:8000/ws/search"
        
        async with websockets.connect(uri) as websocket:
            print("❌ ERROR: Search connection was accepted when it should be rejected!")
            return False
            
    except ConnectionClosedOK as e:
        print(f"✅ SUCCESS: Search WebSocket connection properly rejected")
        print(f"   Close code: {e.code}, Reason: {e.reason}")
        
    except ConnectionClosedError as e:
        print(f"✅ SUCCESS: Search WebSocket connection properly rejected") 
        print(f"   Close code: {e.code}, Reason: {e.reason}")
        
    except ConnectionRefusedError:
        print("✅ SUCCESS: Connection refused (server not running or WebSocket disabled)")
        
    except Exception as e:
        print(f"⚠️  Connection failed with: {type(e).__name__}: {e}")
    
    print()
    print("=" * 50)
    print("🎯 WebSocket Disable Test Complete")
    print("   All connections should be rejected or refused when WebSocket is disabled")
    return True

if __name__ == "__main__":
    # Install websockets if needed: pip install websockets
    try:
        asyncio.run(test_websocket_disabled())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"💥 Test failed with error: {e}")
