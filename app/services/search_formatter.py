"""
Search Result Formatting and Aggregation Module
Handles formatting, pagination, and aggregation of search results
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class SearchResultType(str, Enum):
    """Search result entity types."""
    USERS = "users"
    POSTS = "posts"
    REPRESENTATIVES = "representatives"


class SearchSortOption(str, Enum):
    """Available search sorting options."""
    RELEVANCE = "relevance"
    RECENT = "recent"
    POPULAR = "popular"


class SearchResultFormatter:
    """Formats and aggregates search results for unified API response."""
    
    @staticmethod
    def format_user_result(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format user search result with consistent structure."""
        return {
            'id': user_data.get('id'),
            'type': SearchResultType.USERS,
            'username': user_data.get('username'),
            'display_name': user_data.get('display_name'),
            'bio': user_data.get('bio'),
            'avatar_url': user_data.get('avatar_url'),
            'is_verified': user_data.get('is_verified', False),
            'location': user_data.get('location'),
            'followers_count': user_data.get('followers_count', 0),
            'following_count': user_data.get('following_count', 0),
            'created_at': user_data.get('created_at'),
            'relevance_score': float(user_data.get('relevance_score') or 0),
            'metadata': {
                'entity_type': 'user',
                'searchable_fields': ['username', 'display_name', 'bio', 'location']
            }
        }
    
    @staticmethod
    def format_post_result(post_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format post search result with consistent structure."""
        return {
            'id': post_data.get('id'),
            'type': SearchResultType.POSTS,
            'title': post_data.get('title'),
            'content': SearchResultFormatter._truncate_content(post_data.get('content')),
            'post_type': post_data.get('post_type'),
            'status': post_data.get('status'),
            'location': post_data.get('location'),
            'tags': post_data.get('tags', []),
            'upvotes': post_data.get('upvotes', 0),
            'downvotes': post_data.get('downvotes', 0),
            'comment_count': post_data.get('comment_count', 0),
            'created_at': post_data.get('created_at'),
            'last_activity_at': post_data.get('last_activity_at'),
            'media_urls': post_data.get('media_urls', []),
            'assignee': post_data.get('assignee'),
            'author': {
                'username': post_data.get('author_username'),
                'display_name': post_data.get('author_display_name'),
                'avatar_url': post_data.get('author_avatar_url'),
                'is_verified': post_data.get('author_verified', False)
            },
            'relevance_score': float(post_data.get('relevance_score') or 0),
            'metadata': {
                'entity_type': 'post',
                'searchable_fields': ['title', 'content', 'location', 'tags'],
                'engagement_score': (
                    post_data.get('upvotes', 0) - 
                    post_data.get('downvotes', 0) + 
                    post_data.get('comment_count', 0)
                )
            }
        }
    
    @staticmethod
    def format_representative_result(rep_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format representative search result with consistent structure."""
        return {
            'id': rep_data.get('id'),
            'type': SearchResultType.REPRESENTATIVES,
            'name': rep_data.get('name'),
            'designation': rep_data.get('designation'),
            'constituency': rep_data.get('constituency'),
            'party': rep_data.get('party'),
            'is_verified': rep_data.get('is_verified', False),
            'contact_email': rep_data.get('contact_email'),
            'avatar_url': rep_data.get('avatar_url'),
            'created_at': rep_data.get('created_at'),
            'linked_user': {
                'username': rep_data.get('linked_username'),
                'display_name': rep_data.get('linked_display_name')
            } if rep_data.get('user_id') else None,
            'relevance_score': float(rep_data.get('relevance_score') or 0),
            'metadata': {
                'entity_type': 'representative',
                'searchable_fields': ['name', 'designation', 'constituency', 'party'],
                'is_linked': rep_data.get('user_id') is not None
            }
        }
    
    @staticmethod
    def _truncate_content(content: Optional[str], max_length: int = 200) -> Optional[str]:
        """Truncate content for search results with ellipsis."""
        if not content:
            return content
        
        if len(content) <= max_length:
            return content
        
        # Try to cut at word boundary
        truncated = content[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.8:  # If we can cut at a word boundary without losing too much
            return truncated[:last_space] + "..."
        else:
            return truncated + "..."
    
    @staticmethod
    def format_search_results(raw_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """Format all search results using appropriate formatters."""
        formatted_results = {}
        
        if 'users' in raw_results:
            formatted_results['users'] = [
                SearchResultFormatter.format_user_result(user) 
                for user in raw_results['users']
            ]
        
        if 'posts' in raw_results:
            formatted_results['posts'] = [
                SearchResultFormatter.format_post_result(post) 
                for post in raw_results['posts']
            ]
        
        if 'representatives' in raw_results:
            formatted_results['representatives'] = [
                SearchResultFormatter.format_representative_result(rep) 
                for rep in raw_results['representatives']
            ]
        
        return formatted_results


class SearchResultAggregator:
    """Aggregates and provides analytics for search results."""
    
    @staticmethod
    def aggregate_results(
        formatted_results: Dict[str, List[Dict[str, Any]]],
        query: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aggregate search results with comprehensive metadata."""
        
        # Calculate entity counts
        entity_counts = {}
        total_results = 0
        max_relevance_scores = {}
        
        for entity_type, results in formatted_results.items():
            count = len(results)
            entity_counts[entity_type] = count
            total_results += count
            
            if results:
                max_relevance_scores[entity_type] = max(
                    result.get('relevance_score') or 0 for result in results
                )
            else:
                max_relevance_scores[entity_type] = 0
        
        # Determine primary result type (highest scoring entity type)
        primary_result_type = None
        if max_relevance_scores:
            primary_result_type = max(max_relevance_scores.items(), key=lambda x: x[1])[0]
        
        # Calculate search quality metrics
        has_high_relevance = any(score > 5.0 for score in max_relevance_scores.values())
        has_verified_results = SearchResultAggregator._has_verified_results(formatted_results)
        has_recent_results = SearchResultAggregator._has_recent_results(formatted_results)
        
        return {
            'results': formatted_results,
            'aggregation': {
                'total_results': total_results,
                'entity_counts': entity_counts,
                'primary_result_type': primary_result_type,
                'max_relevance_scores': max_relevance_scores,
                'quality_indicators': {
                    'has_high_relevance': has_high_relevance,
                    'has_verified_results': has_verified_results,
                    'has_recent_results': has_recent_results
                }
            },
            'query_analysis': {
                'original_query': query,
                'query_length': len(query),
                'word_count': len(query.split()),
                'contains_location_terms': SearchResultAggregator._contains_location_terms(query),
                'contains_political_terms': SearchResultAggregator._contains_political_terms(query)
            },
            'search_metadata': metadata
        }
    
    @staticmethod
    def _has_verified_results(results: Dict[str, List[Dict[str, Any]]]) -> bool:
        """Check if any results contain verified entities."""
        for entity_type, entity_results in results.items():
            for result in entity_results:
                if result.get('is_verified'):
                    return True
                if entity_type == 'posts' and result.get('author', {}).get('is_verified'):
                    return True
        return False
    
    @staticmethod
    def _has_recent_results(results: Dict[str, List[Dict[str, Any]]]) -> bool:
        """Check if any results are from the last 30 days."""
        cutoff_date = datetime.now(timezone.utc).replace(day=1)  # Roughly 30 days ago
        
        for entity_results in results.values():
            for result in entity_results:
                created_at = result.get('created_at')
                if created_at and isinstance(created_at, datetime):
                    if created_at > cutoff_date:
                        return True
        return False
    
    @staticmethod
    def _contains_location_terms(query: str) -> bool:
        """Check if query contains location-related terms."""
        location_keywords = [
            'city', 'town', 'district', 'state', 'constituency', 'ward',
            'street', 'area', 'locality', 'region', 'zone'
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in location_keywords)
    
    @staticmethod
    def _contains_political_terms(query: str) -> bool:
        """Check if query contains political-related terms."""
        political_keywords = [
            'mp', 'mla', 'minister', 'mayor', 'councillor', 'representative',
            'congress', 'bjp', 'party', 'election', 'government', 'policy'
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in political_keywords)


class SearchPaginator:
    """Handles pagination for search results."""
    
    @staticmethod
    def paginate_results(
        results: Dict[str, List[Dict[str, Any]]],
        limit: int,
        offset: int,
        entity_specific_limits: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """Paginate search results with entity-specific limits."""
        
        paginated_results = {}
        pagination_info = {}
        
        for entity_type, entity_results in results.items():
            # Use entity-specific limit if provided, otherwise use global limit
            entity_limit = entity_specific_limits.get(entity_type, limit) if entity_specific_limits else limit
            
            # Calculate pagination
            total_count = len(entity_results)
            start_index = offset
            end_index = start_index + entity_limit
            
            # Apply pagination
            paginated_results[entity_type] = entity_results[start_index:end_index]
            
            # Calculate pagination metadata
            has_more = end_index < total_count
            next_offset = end_index if has_more else None
            
            pagination_info[entity_type] = {
                'total_count': total_count,
                'current_count': len(paginated_results[entity_type]),
                'offset': offset,
                'limit': entity_limit,
                'has_more': has_more,
                'next_offset': next_offset,
                'total_pages': (total_count + entity_limit - 1) // entity_limit,
                'current_page': (offset // entity_limit) + 1
            }
        
        return {
            'results': paginated_results,
            'pagination': pagination_info
        }


class SearchHighlighter:
    """Highlights search terms in result content."""
    
    @staticmethod
    def highlight_results(
        results: Dict[str, List[Dict[str, Any]]],
        search_terms: List[str],
        highlight_tag: str = "mark"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Add highlighting to search results."""
        
        highlighted_results = {}
        
        for entity_type, entity_results in results.items():
            highlighted_results[entity_type] = []
            
            for result in entity_results:
                highlighted_result = result.copy()
                
                if entity_type == SearchResultType.USERS:
                    highlighted_result = SearchHighlighter._highlight_user(
                        highlighted_result, search_terms, highlight_tag
                    )
                elif entity_type == SearchResultType.POSTS:
                    highlighted_result = SearchHighlighter._highlight_post(
                        highlighted_result, search_terms, highlight_tag
                    )
                elif entity_type == SearchResultType.REPRESENTATIVES:
                    highlighted_result = SearchHighlighter._highlight_representative(
                        highlighted_result, search_terms, highlight_tag
                    )
                
                highlighted_results[entity_type].append(highlighted_result)
        
        return highlighted_results
    
    @staticmethod
    def _highlight_text(text: str, terms: List[str], tag: str) -> str:
        """Highlight search terms in text."""
        if not text:
            return text
        
        highlighted = text
        for term in terms:
            # Case-insensitive highlighting
            import re
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            highlighted = pattern.sub(f'<{tag}>\\g<0></{tag}>', highlighted)
        
        return highlighted
    
    @staticmethod
    def _highlight_user(result: Dict[str, Any], terms: List[str], tag: str) -> Dict[str, Any]:
        """Highlight user-specific fields."""
        fields_to_highlight = ['username', 'display_name', 'bio']
        
        for field in fields_to_highlight:
            if result.get(field):
                result[f'{field}_highlighted'] = SearchHighlighter._highlight_text(
                    result[field], terms, tag
                )
        
        return result
    
    @staticmethod
    def _highlight_post(result: Dict[str, Any], terms: List[str], tag: str) -> Dict[str, Any]:
        """Highlight post-specific fields."""
        fields_to_highlight = ['title', 'content']
        
        for field in fields_to_highlight:
            if result.get(field):
                result[f'{field}_highlighted'] = SearchHighlighter._highlight_text(
                    result[field], terms, tag
                )
        
        return result
    
    @staticmethod
    def _highlight_representative(result: Dict[str, Any], terms: List[str], tag: str) -> Dict[str, Any]:
        """Highlight representative-specific fields."""
        fields_to_highlight = ['name', 'designation', 'constituency', 'party']
        
        for field in fields_to_highlight:
            if result.get(field):
                result[f'{field}_highlighted'] = SearchHighlighter._highlight_text(
                    result[field], terms, tag
                )
        
        return result
