from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from typing import Optional, List, Dict, Any
from app.schemas import PostCreate, PostUpdate, PostResponse, PaginatedResponse, APIResponse
from app.services.post_service import PostService
from app.services.mixed_content_service import mixed_content_service
from app.services.auth_service import get_current_user
from app.core.config import settings
from app.core.logging_config import get_logger, log_error_with_context

router = APIRouter()
post_service = PostService()
logger = get_logger('app.posts')


@router.get("", response_model=PaginatedResponse)
async def get_posts(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    post_type: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    post_status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    sort_by: str = Query("timestamp"),
    order: str = Query("desc"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Get mixed content (posts + news) with filters and pagination"""
    try:
        # For now, if no user is authenticated, still return posts but without user-specific data
        user_id = current_user["id"] if current_user else None
        
        logger.info(
            f"Fetching mixed content | Page: {page}, Size: {size} | "
            f"Filters: type={post_type}, area={area}, status={post_status}, category={category} | "
            f"Sort: {sort_by} {order} | User: {user_id or 'anonymous'}"
        )
        
        # Use mixed content service to get posts + news
        paginated_result = await mixed_content_service.get_mixed_content(
            page=page,
            size=size,
            user_id=user_id,
            post_type=post_type,
            area=area,
            category=category,
            sort_by=sort_by,
            order=order
        )
        
        logger.info(f"Successfully fetched {len(paginated_result.items)} mixed items for user {user_id or 'anonymous'}")
        return paginated_result
        
    except Exception as e:
        log_error_with_context(
            logger, e,
            {
                'operation': 'get_mixed_content',
                'user_id': user_id,
                'page': page,
                'size': size,
                'filters': {
                    'post_type': post_type,
                    'area': area,
                    'status': post_status,
                    'category': category
                }
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch mixed content"
        )


@router.get("/posts-only", response_model=PaginatedResponse)
async def get_posts_only(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    post_type: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    post_status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    sort_by: str = Query("timestamp"),
    order: str = Query("desc"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Get only user-generated posts (no news) with filters and pagination"""
    try:
        # For now, if no user is authenticated, still return posts but without user-specific data
        user_id = current_user["id"] if current_user else None
        
        logger.info(
            f"Fetching posts only | Page: {page}, Size: {size} | "
            f"Filters: type={post_type}, area={area}, status={post_status}, category={category} | "
            f"Sort: {sort_by} {order} | User: {user_id or 'anonymous'}"
        )
        
        posts = await post_service.get_posts(
            skip=(page - 1) * size,
            limit=size,
            post_type=post_type,
            location=area,
            current_user_id=user_id
        )
        
        # Add source field to posts
        for post in posts:
            post["source"] = "post"
        
        # Convert to paginated response format
        paginated_posts = PaginatedResponse(
            items=posts,
            total=len(posts),  # For now, we'll use the current count
            page=page,
            size=size,
            has_more=len(posts) >= size  # Simple check for now
        )
        
        logger.info(f"Successfully fetched {len(posts)} posts only for user {user_id or 'anonymous'}")
        return paginated_posts
        
    except Exception as e:
        log_error_with_context(
            logger, e,
            {
                'operation': 'get_posts_only',
                'user_id': user_id,
                'page': page,
                'size': size,
                'filters': {
                    'post_type': post_type,
                    'area': area,
                    'status': post_status,
                    'category': category
                }
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch posts only"
        )


@router.get("/news-only", response_model=PaginatedResponse)
async def get_news_only(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    category: Optional[str] = Query(None),
    country: str = Query(None),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Get only news articles (no user posts) with pagination"""
    try:
        user_id = current_user["id"] if current_user else None
        
        # Use settings default if no country specified
        news_country = country or settings.newsapi_country
        
        logger.info(
            f"Fetching news only | Page: {page}, Size: {size} | "
            f"Category: {category}, Country: {news_country} | User: {user_id or 'anonymous'}"
        )
        
        from app.services.news_service import news_service
        
        # Map category to news category if provided
        news_category = None
        if category:
            category_mapping = {
                "Technology": "technology",
                "Healthcare": "health",
                "Economy": "business",
                "Sports": "sports",
                "Entertainment": "entertainment",
                "Education": "general",
                "Infrastructure": "general",
                "Environment": "science",
                "Politics": "general",
                "Safety": "general"
            }
            news_category = category_mapping.get(category, "general")
        
        news_articles = await news_service.fetch_news(
            count=size,
            country=news_country,
            category=news_category,
            page=page
        )
        
        # Convert to paginated response format
        paginated_news = PaginatedResponse(
            items=news_articles,
            total=len(news_articles),
            page=page,
            size=size,
            has_more=len(news_articles) >= size
        )
        
        logger.info(f"Successfully fetched {len(news_articles)} news articles for user {user_id or 'anonymous'}")
        return paginated_news
        
    except Exception as e:
        log_error_with_context(
            logger, e,
            {
                'operation': 'get_news_only',
                'user_id': user_id,
                'page': page,
                'size': size,
                'category': category,
                'country': news_country
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch news articles"
        )


@router.post("", response_model=APIResponse)
async def create_post(
    post_data: PostCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new post"""
    try:
        logger.info(f"Creating post | User: {current_user['id']} | Title: {post_data.title}")
        
        # Create post data dict
        post_dict = {
            'title': post_data.title,
            'content': post_data.content,
            'post_type': post_data.post_type,
            'area': post_data.area,
            'category': post_data.category,
            'media_urls': post_data.media_urls or [],
            'tags': post_data.tags or [],  # Add role tags
            'user_id': current_user['id']
        }
        
        post = await post_service.create_post(post_dict, current_user['id'])
        
        logger.info(f"Post created successfully | Post ID: {post['id']} | User: {current_user['id']}")
        
        return APIResponse(
            success=True,
            message="Post created successfully",
            data={"post": post}
        )
        
    except Exception as e:
        log_error_with_context(
            logger, e,
            {
                'operation': 'create_post',
                'user_id': current_user['id'],
                'title': post_data.title
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create post"
        )


@router.get("/{post_id}", response_model=APIResponse)
async def get_post(
    post_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Get a specific post by ID"""
    try:
        user_id = current_user["id"] if current_user else None
        logger.info(f"Fetching post | Post ID: {post_id} | User: {user_id or 'anonymous'}")
        
        post = await post_service.get_post_by_id(post_id, user_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        logger.info(f"Post fetched successfully | Post ID: {post_id}")
        
        return APIResponse(
            success=True,
            message="Post retrieved successfully",
            data={"post": post}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error_with_context(
            logger, e,
            {
                'operation': 'get_post',
                'post_id': post_id,
                'user_id': user_id
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch post"
        )


@router.put("/{post_id}", response_model=APIResponse)
async def update_post(
    post_id: str,
    post_data: PostUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update a post"""
    try:
        logger.info(f"Updating post | Post ID: {post_id} | User: {current_user['id']}")
        
        # Check if post exists and user owns it
        existing_post = await post_service.get_post_by_id(post_id, current_user['id'])
        if not existing_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        if existing_post['user_id'] != current_user['id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this post"
            )
        
        # Update post
        update_data = post_data.dict(exclude_unset=True)
        post = await post_service.update_post(post_id, update_data)
        
        logger.info(f"Post updated successfully | Post ID: {post_id}")
        
        return APIResponse(
            success=True,
            message="Post updated successfully",
            data={"post": post}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error_with_context(
            logger, e,
            {
                'operation': 'update_post',
                'post_id': post_id,
                'user_id': current_user['id']
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update post"
        )


@router.delete("/{post_id}", response_model=APIResponse)
async def delete_post(
    post_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a post"""
    try:
        logger.info(f"Deleting post | Post ID: {post_id} | User: {current_user['id']}")
        
        # Check if post exists and user owns it
        existing_post = await post_service.get_post_by_id(post_id, current_user['id'])
        if not existing_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        if existing_post['user_id'] != current_user['id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this post"
            )
        
        # Delete post
        await post_service.delete_post(post_id)
        
        logger.info(f"Post deleted successfully | Post ID: {post_id}")
        
        return APIResponse(
            success=True,
            message="Post deleted successfully",
            data={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error_with_context(
            logger, e,
            {
                'operation': 'delete_post',
                'post_id': post_id,
                'user_id': current_user['id']
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete post"
        )


@router.post("/{post_id}/vote", response_model=APIResponse)
async def vote_on_post(
    post_id: str,
    vote_type: str = Query(..., regex="^(up|down)$"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Vote on a post"""
    try:
        logger.info(f"Voting on post | Post ID: {post_id} | User: {current_user['id']} | Vote: {vote_type}")
        
        # Check if post exists
        post = await post_service.get_post_by_id(post_id, current_user['id'])
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Vote on post
        result = await post_service.vote_on_post(post_id, current_user['id'], vote_type)
        
        logger.info(f"Vote recorded successfully | Post ID: {post_id} | Vote: {vote_type}")
        
        return APIResponse(
            success=True,
            message=f"Vote {vote_type} recorded successfully",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error_with_context(
            logger, e,
            {
                'operation': 'vote_on_post',
                'post_id': post_id,
                'user_id': current_user['id'],
                'vote_type': vote_type
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record vote"
        )


@router.post("/{post_id}/save", response_model=APIResponse)
async def save_post(
    post_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Save/unsave a post"""
    try:
        logger.info(f"Toggling save on post | Post ID: {post_id} | User: {current_user['id']}")
        
        # Check if post exists
        post = await post_service.get_post_by_id(post_id, current_user['id'])
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Toggle save status
        result = await post_service.save_post(post_id, current_user['id'])
        
        action = "saved" if result['is_saved'] else "unsaved"
        logger.info(f"Post {action} successfully | Post ID: {post_id}")
        
        return APIResponse(
            success=True,
            message=f"Post {action} successfully",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error_with_context(
            logger, e,
            {
                'operation': 'save_post',
                'post_id': post_id,
                'user_id': current_user['id']
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save/unsave post"
        )


@router.post("/{post_id}/upload-media", response_model=APIResponse)
async def upload_media(
    post_id: str,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Upload media for a post"""
    try:
        logger.info(f"Uploading media for post | Post ID: {post_id} | User: {current_user['id']}")
        
        # Check if post exists and user owns it
        post = await post_service.get_post_by_id(post_id, current_user['id'])
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        if post['user_id'] != current_user['id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to upload media for this post"
            )
        
        # For now, return a mock URL - this would be replaced with actual S3 upload
        mock_url = f"https://example.com/media/{post_id}/{file.filename}"
        
        logger.info(f"Media uploaded successfully | Post ID: {post_id} | URL: {mock_url}")
        
        return APIResponse(
            success=True,
            message="Media uploaded successfully",
            data={"media_url": mock_url}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error_with_context(
            logger, e,
            {
                'operation': 'upload_media',
                'post_id': post_id,
                'user_id': current_user['id'],
                'filename': file.filename if file else None
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload media"
        )
