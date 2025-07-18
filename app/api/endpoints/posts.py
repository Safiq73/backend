from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from typing import Optional, List, Dict, Any
from app.schemas import PostCreate, PostUpdate, PostResponse, PaginatedResponse, APIResponse
from app.services.post_service import PostService
from app.services.auth_service import get_current_user
from app.core.logging_config import get_logger, log_error_with_context

router = APIRouter()
post_service = PostService()
logger = get_logger('app.posts')


@router.get("/", response_model=PaginatedResponse)
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
    """Get posts with filters and pagination"""
    try:
        # For now, if no user is authenticated, still return posts but without user-specific data
        user_id = current_user["id"] if current_user else None
        
        logger.info(
            f"Fetching posts | Page: {page}, Size: {size} | "
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
        
        # Convert to paginated response format
        from app.schemas import PaginatedResponse
        paginated_posts = PaginatedResponse(
            items=posts,
            total=len(posts),  # For now, we'll use the current count
            page=page,
            size=size,
            has_more=len(posts) >= size  # Simple check for now
        )
        
        logger.info(f"Successfully fetched {len(posts)} posts for user {user_id or 'anonymous'}")
        return paginated_posts
        
    except Exception as e:
        log_error_with_context(
            logger, e,
            {
                'operation': 'get_posts',
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
            detail="Failed to fetch posts"
        )


@router.post("/", response_model=APIResponse)
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
            'user_id': current_user['id']
        }
        
        post = await post_service.create_post(post_dict)
        
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
        result = await post_service.toggle_save_post(post_id, current_user['id'])
        
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
