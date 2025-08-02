"""
Test Advanced Analytics Functionality
Tests the analytics service, WebSocket endpoints, and real-time monitoring
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.analytics_service import analytics_service, AdvancedAnalyticsService
from app.websocket.analytics_monitor import analytics_monitor, RealTimeAnalyticsMonitor
from app.websocket.analytics_endpoints import handle_analytics_message

class TestAdvancedAnalyticsService:
    """Test cases for AdvancedAnalyticsService"""

    @pytest.fixture
    def service(self):
        return AdvancedAnalyticsService()

    @pytest.fixture
    def mock_db_conn(self):
        """Mock database connection"""
        conn = AsyncMock()
        
        # Mock platform metrics
        conn.fetchval.side_effect = [
            100,  # total_users
            25,   # active_24h
            50,   # active_7d
            500,  # total_posts
            750,  # total_comments
            1000, # total_searches
            75.5, # engagement_rate
            150.0 # avg_response_time
        ]
        
        # Mock search analytics
        conn.fetch.return_value = [
            {
                'query': 'road maintenance',
                'search_count': 45,
                'unique_users': 20,
                'avg_results': 8.5,
                'last_searched': datetime.utcnow()
            },
            {
                'query': 'water supply',
                'search_count': 38,
                'unique_users': 15,
                'avg_results': 6.2,
                'last_searched': datetime.utcnow()
            }
        ]
        
        return conn

    @pytest.mark.asyncio
    async def test_get_platform_metrics(self, service, mock_db_conn):
        """Test platform metrics retrieval"""
        with patch('app.services.analytics_service.get_db') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_conn
            
            start_time = datetime.utcnow() - timedelta(days=7)
            end_time = datetime.utcnow()
            
            metrics = await service._get_platform_metrics(start_time, end_time)
            
            assert metrics.total_users == 100
            assert metrics.active_users_24h == 25
            assert metrics.active_users_7d == 50
            assert metrics.total_posts == 500
            assert metrics.total_comments == 750
            assert metrics.total_searches == 1000
            assert metrics.engagement_rate == 75.5
            assert metrics.response_time_avg_ms == 150.0

    @pytest.mark.asyncio
    async def test_get_comprehensive_dashboard_analytics(self, service):
        """Test comprehensive dashboard analytics"""
        with patch.object(service, '_get_platform_metrics') as mock_platform, \
             patch.object(service, '_get_search_analytics') as mock_search, \
             patch.object(service, '_get_user_behavior_metrics') as mock_behavior, \
             patch.object(service, '_get_content_analytics') as mock_content, \
             patch.object(service, '_get_trend_analysis') as mock_trends, \
             patch.object(service, '_get_real_time_stats') as mock_realtime:
            
            # Setup mock return values
            mock_platform.return_value = MagicMock()
            mock_search.return_value = {'popular_queries': []}
            mock_behavior.return_value = MagicMock()
            mock_content.return_value = MagicMock()
            mock_trends.return_value = {'growth_trends': []}
            mock_realtime.return_value = {'active_users_last_hour': 5}
            
            result = await service.get_comprehensive_dashboard_analytics('7d')
            
            assert 'time_period' in result
            assert 'platform_metrics' in result
            assert 'search_analytics' in result
            assert 'user_behavior' in result
            assert 'content_analytics' in result
            assert 'trend_analysis' in result
            assert 'real_time_stats' in result
            assert result['time_period'] == '7d'

    @pytest.mark.asyncio
    async def test_get_search_insights(self, service, mock_db_conn):
        """Test search insights functionality"""
        mock_db_conn.fetch.side_effect = [
            [  # weekly_patterns
                {'day_of_week': 1, 'search_count': 50, 'avg_results': 7.5},
                {'day_of_week': 2, 'search_count': 45, 'avg_results': 6.8}
            ],
            [  # query_analysis
                {'query_length': 'short', 'count': 100, 'avg_results': 5.2},
                {'query_length': 'medium', 'count': 75, 'avg_results': 8.1}
            ],
            [  # improving_queries
                {'query': 'traffic updates', 'improvement_trend': 0.85}
            ]
        ]
        
        with patch('app.services.analytics_service.get_db') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_conn
            
            insights = await service.get_search_insights('7d')
            
            assert 'weekly_patterns' in insights
            assert 'query_analysis' in insights
            assert 'improving_queries' in insights
            assert len(insights['weekly_patterns']) == 2
            assert len(insights['query_analysis']) == 2
            assert len(insights['improving_queries']) == 1

    def test_cache_functionality(self, service):
        """Test analytics caching"""
        cache_key = "test_key"
        
        # Initially not cached
        assert not service._is_cached(cache_key)
        
        # Add to cache
        service._cache[cache_key] = {"test": "data"}
        service._cache_timestamps[cache_key] = datetime.utcnow()
        
        # Should be cached now
        assert service._is_cached(cache_key)
        
        # Simulate cache expiry
        service._cache_timestamps[cache_key] = datetime.utcnow() - timedelta(seconds=400)
        assert not service._is_cached(cache_key)

class TestRealTimeAnalyticsMonitor:
    """Test cases for RealTimeAnalyticsMonitor"""

    @pytest.fixture
    def monitor(self):
        return RealTimeAnalyticsMonitor()

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, monitor):
        """Test starting and stopping monitoring"""
        assert not monitor.is_monitoring
        
        # Start monitoring
        await monitor.start_monitoring()
        assert monitor.is_monitoring
        assert monitor.monitor_task is not None
        
        # Stop monitoring
        await monitor.stop_monitoring()
        assert not monitor.is_monitoring

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe_analytics(self, monitor):
        """Test analytics subscription management"""
        connection_id = "test_conn_123"
        analytics_types = ["platform_metrics", "search_trends"]
        
        # Subscribe
        await monitor.subscribe_to_analytics(connection_id, analytics_types)
        
        assert connection_id in monitor.analytics_connections["platform_metrics"]
        assert connection_id in monitor.analytics_connections["search_trends"]
        
        # Unsubscribe from specific types
        await monitor.unsubscribe_from_analytics(connection_id, ["platform_metrics"])
        
        assert connection_id not in monitor.analytics_connections["platform_metrics"]
        assert connection_id in monitor.analytics_connections["search_trends"]
        
        # Unsubscribe from all
        await monitor.unsubscribe_from_analytics(connection_id)
        
        assert connection_id not in monitor.analytics_connections["search_trends"]

    @pytest.mark.asyncio
    async def test_broadcast_analytics_event(self, monitor):
        """Test analytics event broadcasting"""
        connection_id = "test_conn_123"
        analytics_type = "platform_metrics"
        
        # Setup subscription
        await monitor.subscribe_to_analytics(connection_id, [analytics_type])
        
        # Mock connection manager
        with patch('app.websocket.analytics_monitor.connection_manager') as mock_cm:
            mock_cm._send_to_connection.return_value = True
            
            # Broadcast event
            test_data = {"type": "test", "value": 42}
            await monitor._broadcast_analytics_event(analytics_type, test_data)
            
            # Verify the message was sent
            mock_cm._send_to_connection.assert_called_once()
            call_args = mock_cm._send_to_connection.call_args
            
            assert call_args[0][0] == connection_id  # connection_id
            message = call_args[0][1]  # message
            assert message["event_type"] == "analytics_update"
            assert message["analytics_type"] == analytics_type
            assert message["data"] == test_data

    @pytest.mark.asyncio
    async def test_broadcast_search_event(self, monitor):
        """Test search event broadcasting"""
        with patch.object(monitor, '_broadcast_analytics_event') as mock_broadcast:
            search_data = {
                "query": "test query",
                "search_type": "all",
                "result_count": 5,
                "search_time_ms": 120,
                "user_id": "user_123"
            }
            
            await monitor.broadcast_search_event(search_data)
            
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args
            
            assert call_args[0][0] == "search_trends"  # event_type
            event_data = call_args[0][1]  # data
            assert event_data["type"] == "new_search"
            assert event_data["query"] == "test query"
            assert event_data["result_count"] == 5

    def test_get_analytics_stats(self, monitor):
        """Test analytics statistics retrieval"""
        # Add some test subscriptions
        monitor.analytics_connections["platform_metrics"].add("conn1")
        monitor.analytics_connections["platform_metrics"].add("conn2")
        monitor.analytics_connections["search_trends"].add("conn1")
        
        stats = monitor.get_analytics_stats()
        
        assert "monitoring_active" in stats
        assert "subscription_counts" in stats
        assert "total_subscriptions" in stats
        assert "update_interval_seconds" in stats
        
        assert stats["subscription_counts"]["platform_metrics"] == 2
        assert stats["subscription_counts"]["search_trends"] == 1
        assert stats["total_subscriptions"] == 3

class TestAnalyticsWebSocketEndpoints:
    """Test cases for analytics WebSocket endpoints"""

    @pytest.mark.asyncio
    async def test_handle_subscribe_message(self):
        """Test handling subscribe messages"""
        connection_id = "test_conn"
        message = {
            "action": "subscribe",
            "analytics_types": ["platform_metrics", "user_activity"]
        }
        
        with patch('app.websocket.analytics_endpoints.analytics_monitor') as mock_monitor, \
             patch('app.websocket.analytics_endpoints.connection_manager') as mock_cm:
            
            # Make the methods async
            mock_monitor.subscribe_to_analytics = AsyncMock()
            mock_monitor._get_current_timestamp.return_value = "2024-01-01T00:00:00"
            mock_cm._send_to_connection = AsyncMock()
            
            await handle_analytics_message(connection_id, message)
            
            # Verify subscription was called
            mock_monitor.subscribe_to_analytics.assert_called_once_with(
                connection_id, 
                ["platform_metrics", "user_activity"]
            )
            
            # Verify confirmation was sent
            mock_cm._send_to_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_unsubscribe_message(self):
        """Test handling unsubscribe messages"""
        connection_id = "test_conn"
        message = {
            "action": "unsubscribe",
            "analytics_types": ["platform_metrics"]
        }
        
        with patch('app.websocket.analytics_endpoints.analytics_monitor') as mock_monitor, \
             patch('app.websocket.analytics_endpoints.connection_manager') as mock_cm:
            
            # Make the methods async
            mock_monitor.unsubscribe_from_analytics = AsyncMock()
            mock_monitor._get_current_timestamp.return_value = "2024-01-01T00:00:00"
            mock_cm._send_to_connection = AsyncMock()
            
            await handle_analytics_message(connection_id, message)
            
            # Verify unsubscription was called
            mock_monitor.unsubscribe_from_analytics.assert_called_once_with(
                connection_id, 
                ["platform_metrics"]
            )

    @pytest.mark.asyncio
    async def test_handle_ping_message(self):
        """Test handling ping messages"""
        connection_id = "test_conn"
        message = {"action": "ping"}
        
        with patch('app.websocket.analytics_endpoints.analytics_monitor') as mock_monitor, \
             patch('app.websocket.analytics_endpoints.connection_manager') as mock_cm:
            
            mock_monitor.get_analytics_stats.return_value = {"test": "stats"}
            mock_monitor._get_current_timestamp.return_value = "2024-01-01T00:00:00"
            mock_cm._send_to_connection = AsyncMock()
            
            await handle_analytics_message(connection_id, message)
            
            # Verify pong response was sent
            mock_cm._send_to_connection.assert_called_once()
            call_args = mock_cm._send_to_connection.call_args
            message = call_args[0][1]
            
            assert message["event_type"] == "pong"
            assert "analytics_stats" in message

    @pytest.mark.asyncio
    async def test_handle_get_current_metrics_message(self):
        """Test handling get current metrics messages"""
        connection_id = "test_conn"
        message = {"action": "get_current_metrics"}
        
        with patch('app.websocket.analytics_endpoints.connection_manager') as mock_cm, \
             patch('app.websocket.analytics_endpoints.analytics_monitor') as mock_monitor, \
             patch('app.services.analytics_service.analytics_service') as mock_service:
            
            mock_metrics = {"active_users": 10, "searches": 50}
            mock_service._get_real_time_stats = AsyncMock(return_value=mock_metrics)
            mock_monitor._get_current_timestamp.return_value = "2024-01-01T00:00:00"
            mock_cm._send_to_connection = AsyncMock()
            
            await handle_analytics_message(connection_id, message)
            
            # Verify current metrics were sent
            mock_cm._send_to_connection.assert_called_once()
            call_args = mock_cm._send_to_connection.call_args
            response = call_args[0][1]
            
            assert response["event_type"] == "current_metrics"
            assert response["data"] == mock_metrics

    @pytest.mark.asyncio
    async def test_handle_unknown_action(self):
        """Test handling unknown action messages"""
        connection_id = "test_conn"
        message = {"action": "unknown_action"}
        
        with patch('app.websocket.analytics_endpoints.connection_manager') as mock_cm, \
             patch('app.websocket.analytics_endpoints.analytics_monitor') as mock_monitor:
            
            mock_cm._send_to_connection = AsyncMock()
            mock_monitor._get_current_timestamp.return_value = "2024-01-01T00:00:00"
            
            await handle_analytics_message(connection_id, message)
            
            # Verify error response was sent
            mock_cm._send_to_connection.assert_called_once()
            call_args = mock_cm._send_to_connection.call_args
            response = call_args[0][1]
            
            assert response["event_type"] == "error"
            assert "Unknown action" in response["error"]

# Integration Tests
class TestAnalyticsIntegration:
    """Integration tests for analytics functionality"""

    @pytest.mark.asyncio
    async def test_analytics_workflow(self):
        """Test complete analytics workflow"""
        # This would test the complete flow from data collection to WebSocket broadcasting
        # For now, we'll just verify the components work together
        
        service = AdvancedAnalyticsService()
        monitor = RealTimeAnalyticsMonitor()
        
        # Test service can be created
        assert service is not None
        assert monitor is not None
        
        # Test cache operations
        await service.clear_cache()
        assert len(service._cache) == 0
        
        # Test monitor stats
        stats = monitor.get_analytics_stats()
        assert "monitoring_active" in stats

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
