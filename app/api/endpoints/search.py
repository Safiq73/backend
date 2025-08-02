"""
Unified Search API Endpoint for CivicPulse Platform
Provides comprehensive search functionality across users, posts, and representatives
"""

import logging
from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.services.search_service import SearchService
from app.services.auth_service import get_current_user, get_current_user_optional
from app.models.pydantic_models import UserResponse

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(tags=["search"])

# Initialize search service
search_service = SearchService()


class SearchEntityType(str, Enum):
    """Available entity types for search."""
    USERS = "users"
    POSTS = "posts"
    REPRESENTATIVES = "representatives"
    ALL = "all"


class SearchSortOption(str, Enum):
    """Available sorting options for search results."""
    RELEVANCE = "relevance"
    RECENT = "recent"
    POPULAR = "popular"


class SearchSuggestionType(str, Enum):
    """Available suggestion types."""
    POPULAR = "popular"
    RECENT = "recent"
    SIMILAR = "similar"
    AUTOCOMPLETE = "autocomplete"
    TRENDING = "trending"


class SearchFilters(BaseModel):
    """Search filters for advanced search functionality."""
    
    # User filters
    verified: Optional[bool] = Field(None, description="Filter by verified status")
    min_followers: Optional[int] = Field(None, ge=0, description="Minimum follower count")
    
    # Post filters
    post_type: Optional[str] = Field(None, description="Filter by post type")
    status: Optional[str] = Field(None, description="Filter by post status")
    location: Optional[str] = Field(None, description="Filter by location")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    min_upvotes: Optional[int] = Field(None, ge=0, description="Minimum upvotes")
    
    # Representative filters
    party: Optional[str] = Field(None, description="Filter by political party")
    constituency: Optional[str] = Field(None, description="Filter by constituency")
    linked_only: Optional[bool] = Field(None, description="Only show linked representatives")
    
    # Date filters
    date_from: Optional[str] = Field(None, description="Filter from date (ISO format)")
    date_to: Optional[str] = Field(None, description="Filter to date (ISO format)")
    
    # UI options
    highlight: Optional[bool] = Field(True, description="Enable result highlighting")
    
    @validator('tags', pre=True)
    def parse_tags(cls, v):
        """Parse tags from string or list."""
        if isinstance(v, str):
            return [tag.strip() for tag in v.split(',') if tag.strip()]
        return v


class SearchRequest(BaseModel):
    """Request model for unified search."""
    
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    entity_types: Optional[List[SearchEntityType]] = Field(
        default=[SearchEntityType.ALL], 
        description="Entity types to search"
    )
    limit: Optional[int] = Field(20, ge=1, le=100, description="Results per entity type")
    offset: Optional[int] = Field(0, ge=0, description="Pagination offset")
    sort_by: Optional[SearchSortOption] = Field(
        SearchSortOption.RELEVANCE, 
        description="Sort criteria"
    )
    filters: Optional[SearchFilters] = Field(None, description="Additional filters")
    
    @validator('entity_types', pre=True)
    def process_entity_types(cls, v):
        """Process entity types, handling 'all' case."""
        if not v or SearchEntityType.ALL in v:
            return [SearchEntityType.USERS, SearchEntityType.POSTS, SearchEntityType.REPRESENTATIVES]
        return v


class AdvancedSearchRequest(BaseModel):
    """Request model for advanced search with structured components."""
    
    text: Optional[str] = Field(None, description="General text search")
    title: Optional[str] = Field(None, description="Search in titles")
    content: Optional[str] = Field(None, description="Search in content")
    author: Optional[str] = Field(None, description="Search by author")
    location: Optional[str] = Field(None, description="Search by location")
    tags: Optional[List[str]] = Field(None, description="Search by tags")
    
    entity_types: Optional[List[SearchEntityType]] = Field(
        default=[SearchEntityType.ALL],
        description="Entity types to search"
    )
    limit: Optional[int] = Field(20, ge=1, le=100, description="Results per entity type")
    offset: Optional[int] = Field(0, ge=0, description="Pagination offset")
    sort_by: Optional[SearchSortOption] = Field(
        SearchSortOption.RELEVANCE,
        description="Sort criteria"
    )
    filters: Optional[SearchFilters] = Field(None, description="Additional filters")
    
    @validator('entity_types', pre=True)
    def process_entity_types(cls, v):
        """Process entity types, handling 'all' case."""
        if not v or SearchEntityType.ALL in v:
            return [SearchEntityType.USERS, SearchEntityType.POSTS, SearchEntityType.REPRESENTATIVES]
        return v


class SuggestionRequest(BaseModel):
    """Request model for search suggestions."""
    
    partial_query: str = Field(..., min_length=0, max_length=100, description="Partial search query")
    suggestion_types: Optional[List[SearchSuggestionType]] = Field(
        default=[SearchSuggestionType.POPULAR, SearchSuggestionType.AUTOCOMPLETE],
        description="Types of suggestions to return"
    )
    limit: Optional[int] = Field(10, ge=1, le=50, description="Maximum suggestions per type")


class SearchResponse(BaseModel):
    """Response model for search results."""
    
    query: str = Field(..., description="Original search query")
    results: Dict[str, List[Dict[str, Any]]] = Field(..., description="Search results by entity type")
    suggestions: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict, description="Search suggestions")
    entity_suggestions: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict, description="Entity-specific suggestions")
    aggregation: Dict[str, Any] = Field(default_factory=dict, description="Result aggregation metadata")
    query_analysis: Dict[str, Any] = Field(default_factory=dict, description="Query analysis results")
    pagination: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Pagination information")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Search metadata")


@router.get("/", response_model=SearchResponse, summary="Unified Search")
async def unified_search(
    q: str = Query(..., min_length=2, max_length=500, description="Search query"),
    entity_types: Optional[str] = Query(None, description="Comma-separated entity types (users,posts,representatives)"),
    limit: int = Query(20, ge=1, le=100, description="Results per entity type"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    sort_by: SearchSortOption = Query(SearchSortOption.RELEVANCE, description="Sort criteria"),
    
    # Filter parameters
    verified: Optional[bool] = Query(None, description="Filter by verified status"),
    min_followers: Optional[int] = Query(None, ge=0, description="Minimum follower count"),
    post_type: Optional[str] = Query(None, description="Filter by post type"),
    status: Optional[str] = Query(None, description="Filter by post status"),
    location: Optional[str] = Query(None, description="Filter by location"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    min_upvotes: Optional[int] = Query(None, ge=0, description="Minimum upvotes"),
    party: Optional[str] = Query(None, description="Filter by political party"),
    constituency: Optional[str] = Query(None, description="Filter by constituency"),
    linked_only: Optional[bool] = Query(None, description="Only show linked representatives"),
    highlight: bool = Query(True, description="Enable result highlighting"),
    
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """
    Perform unified search across users, posts, and representatives.
    
    This endpoint provides comprehensive search functionality with:
    - Full-text search with relevance scoring
    - Fuzzy matching for typo tolerance
    - Advanced filtering options
    - Result highlighting
    - Search suggestions
    - Analytics tracking
    
    **Query Parameters:**
    - **q**: Search query (required, min 2 characters)
    - **entity_types**: Comma-separated list of entity types to search
    - **limit**: Maximum results per entity type (1-100, default 20)
    - **offset**: Pagination offset (default 0)
    - **sort_by**: Sort criteria (relevance, recent, popular)
    
    **Filter Parameters:**
    - **verified**: Filter by verified status
    - **location**: Filter by location
    - **tags**: Comma-separated tags
    - And many more specific filters...
    
    **Response includes:**
    - Search results grouped by entity type
    - Search suggestions and autocomplete
    - Result aggregation and analytics
    - Pagination information
    """
    try:
        # Parse entity types
        parsed_entity_types = None
        if entity_types:
            entity_list = [t.strip() for t in entity_types.split(',')]
            if 'all' not in entity_list:
                parsed_entity_types = entity_list
        
        # Build filters
        filters = {}
        if verified is not None:
            filters['verified'] = verified
        if min_followers is not None:
            filters['min_followers'] = min_followers
        if post_type:
            filters['post_type'] = post_type
        if status:
            filters['status'] = status
        if location:
            filters['location'] = location
        if tags:
            filters['tags'] = [tag.strip() for tag in tags.split(',')]
        if min_upvotes is not None:
            filters['min_upvotes'] = min_upvotes
        if party:
            filters['party'] = party
        if constituency:
            filters['constituency'] = constituency
        if linked_only is not None:
            filters['linked_only'] = linked_only
        if not highlight:
            filters['highlight'] = False
        
        # Get user ID for personalization
        user_id = current_user.get('id') if current_user else None
        
        # Perform search
        search_results = await search_service.unified_search(
            query=q,
            entity_types=parsed_entity_types,
            limit=limit,
            offset=offset,
            filters=filters if filters else None,
            sort_by=sort_by.value,
            user_id=user_id
        )
        
        return SearchResponse(**search_results)
        
    except Exception as e:
        logger.error(f"Unified search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search temporarily unavailable: {str(e)}"
        )


@router.post("/", response_model=SearchResponse, summary="Advanced Unified Search")
async def advanced_unified_search(
    request: SearchRequest,
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """
    Perform advanced unified search with structured request body.
    
    This endpoint accepts a detailed search request with:
    - Complex filtering options
    - Multiple entity types
    - Advanced sorting and pagination
    - Structured filter definitions
    
    **Use this endpoint when:**
    - You need complex filtering combinations
    - You want to send filters in a structured format
    - You're building advanced search interfaces
    """
    try:
        # Convert entity types to strings
        entity_types = [et.value for et in request.entity_types] if request.entity_types else None
        
        # Convert filters to dict
        filters_dict = request.filters.dict(exclude_none=True) if request.filters else None
        
        # Get user ID for personalization
        user_id = current_user.get('id') if current_user else None
        
        # Perform search
        search_results = await search_service.unified_search(
            query=request.query,
            entity_types=entity_types,
            limit=request.limit,
            offset=request.offset,
            filters=filters_dict,
            sort_by=request.sort_by.value,
            user_id=user_id
        )
        
        return SearchResponse(**search_results)
        
    except Exception as e:
        logger.error(f"Advanced unified search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search temporarily unavailable: {str(e)}"
        )


@router.post("/advanced", response_model=SearchResponse, summary="Advanced Search with Components")
async def advanced_search_with_components(
    request: AdvancedSearchRequest,
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """
    Perform advanced search with structured query components.
    
    This endpoint allows searching with specific field targets:
    - Search in specific fields (title, content, author)
    - Combine multiple search criteria
    - Advanced filtering and sorting
    
    **Example use cases:**
    - Search for posts by specific author about certain topics
    - Find content in specific locations with certain tags
    - Complex multi-field searches
    """
    try:
        # Build query components
        query_components = {}
        if request.text:
            query_components['text'] = request.text
        if request.title:
            query_components['title'] = request.title
        if request.content:
            query_components['content'] = request.content
        if request.author:
            query_components['author'] = request.author
        if request.location:
            query_components['location'] = request.location
        if request.tags:
            query_components['tags'] = request.tags
        
        # Convert entity types to strings
        entity_types = [et.value for et in request.entity_types] if request.entity_types else None
        
        # Get user ID for personalization
        user_id = current_user.get('id') if current_user else None
        
        # Perform advanced search
        search_results = await search_service.advanced_search(
            query_components=query_components,
            entity_types=entity_types,
            limit=request.limit,
            offset=request.offset,
            sort_by=request.sort_by.value,
            user_id=user_id
        )
        
        return SearchResponse(**search_results)
        
    except Exception as e:
        logger.error(f"Advanced component search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search temporarily unavailable: {str(e)}"
        )


@router.get("/suggestions/simple", summary="Get Simple Search Suggestions")
async def get_simple_search_suggestions(
    q: str = Query("", max_length=100, description="Partial search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum suggestions"),
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """
    Get simple search suggestions as plain text array for easy frontend consumption.
    
    Returns just an array of suggestion strings instead of complex objects.
    Perfect for autocomplete dropdowns and simple suggestion lists.
    """
    try:
        # Get user ID for personalization
        user_id = current_user.get('id') if current_user else None
        
        # Get full suggestions
        full_suggestions = await search_service.get_search_suggestions(
            partial_query=q,
            suggestion_types=['popular', 'autocomplete'],
            limit=limit,
            user_id=user_id
        )
        
        # Extract just the suggestion text from all suggestion types
        simple_suggestions = []
        
        # Extract from all suggestion types
        for suggestion_type, suggestions in full_suggestions.get('suggestions', {}).items():
            for suggestion in suggestions:
                if isinstance(suggestion, dict) and 'suggestion' in suggestion:
                    text = suggestion['suggestion']
                    if text not in simple_suggestions:
                        simple_suggestions.append(text)
        
        # Extract from entity suggestions  
        for entity_type, suggestions in full_suggestions.get('entity_suggestions', {}).items():
            for suggestion in suggestions:
                if isinstance(suggestion, dict) and 'suggestion' in suggestion:
                    text = suggestion['suggestion']
                    if text not in simple_suggestions:
                        simple_suggestions.append(text)
        
        return {
            "query": q,
            "suggestions": simple_suggestions[:limit],
            "count": len(simple_suggestions[:limit])
        }
        
    except Exception as e:
        logger.error(f"Simple search suggestions failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Suggestions temporarily unavailable: {str(e)}"
        )


@router.get("/suggestions", summary="Get Search Suggestions")
async def get_search_suggestions(
    q: str = Query("", max_length=100, description="Partial search query"),
    types: Optional[str] = Query(None, description="Comma-separated suggestion types"),
    limit: int = Query(10, ge=1, le=50, description="Maximum suggestions per type"),
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """
    Get intelligent search suggestions for autocomplete and discovery.
    
    This endpoint provides:
    - Autocomplete suggestions based on partial queries
    - Popular search terms
    - Recent searches (personalized if authenticated)
    - Trending searches
    - Entity-specific suggestions
    
    **Use cases:**
    - Autocomplete dropdowns
    - Search suggestion boxes
    - Discovery of popular content
    - Search history (personalized)
    """
    try:
        # Parse suggestion types
        suggestion_types = None
        if types:
            suggestion_types = [t.strip() for t in types.split(',')]
        
        # Get user ID for personalization
        user_id = current_user.get('id') if current_user else None
        
        # Get suggestions
        suggestions = await search_service.get_search_suggestions(
            partial_query=q,
            suggestion_types=suggestion_types,
            limit=limit,
            user_id=user_id
        )
        
        return suggestions
        
    except Exception as e:
        logger.error(f"Search suggestions failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Suggestions temporarily unavailable: {str(e)}"
        )


@router.post("/suggestions", summary="Get Suggestions with Request Body")
async def get_suggestions_with_body(
    request: SuggestionRequest,
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """
    Get search suggestions using a structured request body.
    
    Alternative endpoint for getting suggestions with more control over parameters.
    """
    try:
        # Convert suggestion types to strings
        suggestion_types = [st.value for st in request.suggestion_types] if request.suggestion_types else None
        
        # Get user ID for personalization
        user_id = current_user.get('id') if current_user else None
        
        # Get suggestions
        suggestions = await search_service.get_search_suggestions(
            partial_query=request.partial_query,
            suggestion_types=suggestion_types,
            limit=request.limit,
            user_id=user_id
        )
        
        return suggestions
        
    except Exception as e:
        logger.error(f"Search suggestions with body failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Suggestions temporarily unavailable: {str(e)}"
        )


@router.get("/similar/{content_type}/{content_id}", summary="Find Similar Content")
async def find_similar_content(
    content_type: str = Path(..., description="Content type (post, user, representative)"),
    content_id: int = Path(..., description="Content ID"),
    limit: int = Query(10, ge=1, le=50, description="Maximum similar items"),
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """
    Find content similar to a given piece of content.
    
    This endpoint analyzes the content and finds similar items based on:
    - Content similarity
    - Tag overlap
    - Topic analysis
    - User behavior patterns
    
    **Supported content types:**
    - **post**: Find posts similar to a given post
    - **user**: Find users similar to a given user
    - **representative**: Find representatives similar to a given one
    """
    try:
        # Validate content type
        valid_types = ['post', 'user', 'representative']
        if content_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type. Must be one of: {valid_types}"
            )
        
        # Get user ID for personalization
        user_id = current_user.get('id') if current_user else None
        
        # Find similar content
        similar_results = await search_service.search_similar_content(
            content_id=content_id,
            content_type=content_type,
            limit=limit,
            user_id=user_id
        )
        
        return similar_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Similar content search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Similar content search temporarily unavailable: {str(e)}"
        )


@router.get("/analytics/popular-terms", summary="Get Popular Search Terms Analysis")
async def get_popular_terms_analysis(
    time_period: str = Query("7d", description="Time period (1d, 7d, 30d, 90d)"),
    entity_types: Optional[str] = Query(None, description="Comma-separated entity types"),
    limit: int = Query(50, ge=1, le=200, description="Maximum terms to analyze"),
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """
    Get comprehensive analysis of popular search terms.
    
    This endpoint provides analytics on:
    - Most popular search terms
    - Search volume trends
    - Term frequency distribution
    - Trending vs declining terms
    
    **Use cases:**
    - Administrative dashboards
    - Content strategy insights
    - Search optimization
    - Trend analysis
    
    **Requires authentication** for access to analytics data.
    """
    try:
        # For now, allow any authenticated user. In production, you might want to restrict to admins
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required for analytics access"
            )
        
        # Parse entity types
        parsed_entity_types = None
        if entity_types:
            parsed_entity_types = [t.strip() for t in entity_types.split(',')]
        
        # Validate time period
        valid_periods = ['1d', '7d', '30d', '90d']
        if time_period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time period. Must be one of: {valid_periods}"
            )
        
        # Get popular terms analysis
        analysis = await search_service.get_popular_terms_analysis(
            time_period=time_period,
            entity_types=parsed_entity_types,
            limit=limit
        )
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Popular terms analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Analytics temporarily unavailable: {str(e)}"
        )


@router.get("/health", summary="Search Service Health Check")
async def search_health_check():
    """
    Health check endpoint for the search service.
    
    Returns the current status of the search functionality including:
    - Service availability
    - Database connectivity
    - Search index status
    """
    try:
        # Basic health check - attempt a simple search
        health_result = await search_service.unified_search(
            query="test",
            entity_types=['users'],
            limit=1,
            offset=0
        )
        
        return {
            "status": "healthy",
            "service": "search",
            "timestamp": health_result['metadata']['search_time'],
            "database_connection": "ok",
            "search_functionality": "ok"
        }
        
    except Exception as e:
        logger.error(f"Search health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "search",
                "error": str(e),
                "database_connection": "error",
                "search_functionality": "error"
            }
        )
