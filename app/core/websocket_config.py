"""
WebSocket Configuration Management
Allows enabling/disabling WebSocket features with graceful fallback
"""

import os
from typing import Optional
from dataclasses import dataclass
from enum import Enum

class WebSocketMode(str, Enum):
    """WebSocket operation modes"""
    ENABLED = "enabled"           # Full WebSocket functionality
    DISABLED = "disabled"         # No WebSocket, REST API only
    FALLBACK = "fallback"         # Try WebSocket, fall back to REST
    MAINTENANCE = "maintenance"   # WebSocket disabled for maintenance

@dataclass
class WebSocketConfig:
    """WebSocket configuration settings"""
    mode: WebSocketMode = WebSocketMode.DISABLED
    
    # Connection settings
    max_connections: int = 1000
    connection_timeout: int = 30
    heartbeat_interval: int = 30
    
    # Rate limiting
    max_messages_per_minute: int = 60
    batch_interval: float = 2.0
    
    # Fallback settings
    polling_interval: int = 30  # seconds for REST API polling when WebSocket disabled
    enable_real_time_features: bool = True
    
    # Feature flags
    enable_search_websocket: bool = True
    enable_analytics_websocket: bool = True
    enable_notifications_websocket: bool = True
    
    @classmethod
    def from_env(cls) -> 'WebSocketConfig':
        """Create configuration from environment variables"""
        mode = WebSocketMode(os.getenv('WEBSOCKET_MODE', WebSocketMode.DISABLED.value))
        
        return cls(
            mode=mode,
            max_connections=int(os.getenv('WEBSOCKET_MAX_CONNECTIONS', '1000')),
            connection_timeout=int(os.getenv('WEBSOCKET_TIMEOUT', '30')),
            heartbeat_interval=int(os.getenv('WEBSOCKET_HEARTBEAT', '30')),
            max_messages_per_minute=int(os.getenv('WEBSOCKET_RATE_LIMIT', '60')),
            batch_interval=float(os.getenv('WEBSOCKET_BATCH_INTERVAL', '2.0')),
            polling_interval=int(os.getenv('REST_POLLING_INTERVAL', '30')),
            enable_real_time_features=os.getenv('ENABLE_REALTIME', 'true').lower() == 'true',
            enable_search_websocket=os.getenv('ENABLE_SEARCH_WS', 'true').lower() == 'true',
            enable_analytics_websocket=os.getenv('ENABLE_ANALYTICS_WS', 'true').lower() == 'true',
            enable_notifications_websocket=os.getenv('ENABLE_NOTIFICATIONS_WS', 'true').lower() == 'true'
        )
    
    def is_websocket_enabled(self) -> bool:
        """Check if WebSocket functionality is enabled"""
        return self.mode == WebSocketMode.ENABLED
    
    def is_fallback_mode(self) -> bool:
        """Check if fallback mode is enabled"""
        return self.mode == WebSocketMode.FALLBACK
    
    def should_use_websocket(self, feature: str = "general") -> bool:
        """Determine if WebSocket should be used for a specific feature"""
        if self.mode == WebSocketMode.DISABLED:
            return False
        
        if self.mode == WebSocketMode.MAINTENANCE:
            return False
        
        # Check feature-specific flags
        if feature == "search" and not self.enable_search_websocket:
            return False
        
        if feature == "analytics" and not self.enable_analytics_websocket:
            return False
        
        if feature == "notifications" and not self.enable_notifications_websocket:
            return False
        
        return True

# Global configuration instance
websocket_config = WebSocketConfig.from_env()

def get_websocket_config() -> WebSocketConfig:
    """Get the current WebSocket configuration"""
    return websocket_config

def update_websocket_mode(mode: WebSocketMode):
    """Update the WebSocket mode at runtime"""
    global websocket_config
    websocket_config.mode = mode

def is_websocket_feature_enabled(feature: str = "general") -> bool:
    """Quick check if a WebSocket feature is enabled"""
    return websocket_config.should_use_websocket(feature)
