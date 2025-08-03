from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, UploadFile, File
from typing import Optional, List, Dict, Any
from app.schemas import PostCreate, PostUpdate, PostStatusUpdate, PostAssigneeUpdate, PostResponse, PaginatedResponse, APIResponse, AssigneeOption, TitleInfo, JurisdictionInfo
from app.services.post_service import PostService
from app.services.mixed_content_service import mixed_content_service
from app.services.db_service import DatabaseService
from app.services.auth_service import get_current_user, get_current_user_optional
from app.services.s3_upload_service import s3_upload_service
from app.core.config import settings
from app.core.logging_config import get_logger, log_error_with_context

router = APIRouter()
post_service = PostService()
db_service = DatabaseService()
logger = get_logger('app.posts')


@router.get("", response_model=PaginatedResponse)
async def get_posts(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    post_type: Optional[str] = Query(None),
    post_status: Optional[str] = Query(None),
    assignee: Optional[List[str]] = Query(None, description="Filter by assignee representative IDs (can specify multiple)"),
    sort_by: str = Query("timestamp"),
    order: str = Query("desc"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Get mixed content (posts + news) with filters and pagination"""
    try:
        # For now, if no user is authenticated, still return posts but without user-specific data
        user_id = current_user["id"] if current_user else None
        
        logger.info(
            f"Fetching mixed content | Page: {page}, Size: {size} | "
            f"Filters: type={post_type}, status={post_status}, assignee={assignee} | "
            f"Sort: {sort_by} {order} | User: {user_id or 'anonymous'}"
        )
        
        # Use mixed content service to get posts + news
        paginated_result = await mixed_content_service.get_mixed_content(
            page=page,
            size=size,
            user_id=user_id,
            post_type=post_type,
            assignee=assignee,
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
                    'status': post_status,
                    'assignee': assignee
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
    post_status: Optional[str] = Query(None),
    assignee: Optional[List[str]] = Query(None, description="Filter by assignee representative IDs (can specify multiple)"),
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
            f"Filters: type={post_type}, status={post_status}, assignee={assignee} | "
            f"Sort: {sort_by} {order} | User: {user_id or 'anonymous'}"
        )
        
        posts = await post_service.get_posts(
            skip=(page - 1) * size,
            limit=size,
            post_type=post_type,
            assignee=assignee,
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
                    'status': post_status
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


@router.get("/representatives/by-location", response_model=APIResponse)
async def get_representatives_by_location(
    latitude: float = Query(..., ge=6.5, le=37.5, description="Latitude within India bounds"),
    longitude: float = Query(..., ge=68.0, le=97.5, description="Longitude within India bounds"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Get representatives and judiciary for a specific location"""
    try:
        user_id = current_user["id"] if current_user else None
        
        logger.info(
            f"Fetching representatives by location | Lat: {latitude}, Lng: {longitude} | "
            f"User: {user_id or 'anonymous'}"
        )
        
        representatives = await db_service.get_representatives_by_location(latitude, longitude)
        
        # Format for frontend display
        assignee_options = []
        for rep in representatives:
            option = AssigneeOption(
                value=rep['representative_id'],
                label=rep['display_name'],
                title=TitleInfo(**rep['title']),
                jurisdiction=JurisdictionInfo(**rep['jurisdiction'])
            )
            assignee_options.append(option)
        
        logger.info(f"Found {len(assignee_options)} representative options for location")
        
        return APIResponse(
            success=True,
            message=f"Found {len(assignee_options)} representatives for location",
            data={
                "assignee_options": [option.dict() for option in assignee_options],
                "location": {"latitude": latitude, "longitude": longitude},
                "total": len(assignee_options)
            }
        )
        
    except Exception as e:
        log_error_with_context(
            logger, e,
            {
                'operation': 'get_representatives_by_location',
                'latitude': latitude,
                'longitude': longitude,
                'user_id': user_id
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch representatives for location"
        )


@router.post("", response_model=APIResponse)
async def create_post(
    title: str = Form(..., min_length=1, max_length=500),
    content: str = Form(..., min_length=1, max_length=10000),
    post_type: str = Form(..., regex="^(issue|announcement|news|accomplishment|discussion)$"),
    assignee: str = Form(..., description="UUID of representative assigned to handle this post"),
    location: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None, ge=-90, le=90),
    longitude: Optional[float] = Form(None, ge=-180, le=180),
    files: List[UploadFile] = File([], description="Media files (images/videos) to upload"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    
    # Validate file count
    file_count = len(files) if files else 0
    if file_count > settings.max_files_per_post:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Maximum allowed: {settings.max_files_per_post}"
        )
    
    # Upload files to S3 if provided
    media_urls = []
    if files and any(file.filename for file in files):  # Check for actual files
        # Filter out empty files
        valid_files = [f for f in files if f.filename and f.size > 0]
        
        if valid_files:
            logger.info(f"Uploading {len(valid_files)} files to S3")
            
            # Check if S3 service is available
            if not s3_upload_service.is_available():
                logger.warning("S3 service not available, files will not be uploaded")
                # Continue with post creation without files
            else:
                # Upload files to S3
                media_urls = await s3_upload_service.upload_multiple_files(
                    files=valid_files,
                    post_id=None,  # We'll update this after post creation if needed
                    use_presigned_url=False  # Use direct URLs for now
                )
                logger.info(f"Successfully uploaded {len(media_urls)} files")
    
    # Create post data dict
    post_dict = {
        'title': title.strip(),
        'content': content.strip(),
        'post_type': post_type,
        'assignee': assignee,
        'location': location,
        'latitude': latitude,
        'longitude': longitude,
        'media_urls': media_urls,
        'user_id': current_user['id']
    }
    
    post = await post_service.create_post(post_dict, current_user['id'])
    return APIResponse(
        success=True,
        message="Post created successfully",
        data={
            "post": post,
            "uploaded_files": len(media_urls),
            "media_urls": media_urls
        }
    )
        

@router.get("/nearby", response_model=APIResponse)
async def get_nearby_posts(
    latitude: float = Query(..., ge=6.5, le=37.5, description="Latitude within India bounds"),
    longitude: float = Query(..., ge=68.0, le=97.5, description="Longitude within India bounds"),
    radius: float = Query(10.0, ge=0.1, le=100.0, description="Search radius in kilometers"),
    post_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Get posts near a specific location"""
    try:
        user_id = current_user["id"] if current_user else None
        
        logger.info(
            f"Fetching nearby posts | Lat: {latitude}, Lng: {longitude}, Radius: {radius}km | "
            f"Filters: type={post_type}, category={category} | User: {user_id or 'anonymous'}"
        )
        
        # Get nearby posts using spatial query
        nearby_posts = await post_service.get_posts_near_location(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius,
            post_type=post_type,
            category=category,
            limit=limit,
            offset=offset,
            user_id=user_id
        )
        
        logger.info(f"Found {len(nearby_posts)} posts within {radius}km of location")
        
        return APIResponse(
            success=True,
            message=f"Found {len(nearby_posts)} posts within {radius}km",
            data={
                "posts": nearby_posts,
                "total": len(nearby_posts),
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius
            }
        )
        
    except Exception as e:
        log_error_with_context(
            logger, e,
            {
                'operation': 'get_nearby_posts',
                'latitude': latitude,
                'longitude': longitude,
                'radius': radius,
                'user_id': user_id
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch nearby posts"
        )


@router.post("/{post_id}/upload", response_model=APIResponse)
async def upload_files_to_post(
    post_id: str,
    files: List[UploadFile] = File(..., description="Media files to upload"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Upload additional files to an existing post"""
    try:
        logger.info(f"Uploading files to post | Post ID: {post_id} | User: {current_user['id']} | Files: {len(files)}")
        
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
                detail="Not authorized to upload files to this post"
            )
        
        # Check current file count
        current_media_urls = existing_post.get('media_urls', [])
        total_files_after_upload = len(current_media_urls) + len(files)
        
        if total_files_after_upload > settings.max_files_per_post:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Total files would exceed limit. Current: {len(current_media_urls)}, Uploading: {len(files)}, Max: {settings.max_files_per_post}"
            )
        
        # Validate files
        valid_files = [f for f in files if f.filename and f.size > 0]
        if not valid_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid files provided"
            )
        
        # Check if S3 service is available
        if not s3_upload_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="File upload service is currently unavailable"
            )
        
        # Upload files to S3
        new_media_urls = await s3_upload_service.upload_multiple_files(
            files=valid_files,
            post_id=post_id,
            use_presigned_url=False
        )
        
        # Update post with new media URLs
        updated_media_urls = current_media_urls + new_media_urls
        update_data = {"media_urls": updated_media_urls}
        
        updated_post = await post_service.update_post(post_id, update_data)
        
        logger.info(f"Files uploaded successfully | Post ID: {post_id} | New files: {len(new_media_urls)}")
        
        return APIResponse(
            success=True,
            message=f"Successfully uploaded {len(new_media_urls)} files",
            data={
                "post": updated_post,
                "new_media_urls": new_media_urls,
                "total_media_count": len(updated_media_urls)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error_with_context(
            logger, e,
            {
                'operation': 'upload_files_to_post',
                'post_id': post_id,
                'user_id': current_user['id'],
                'file_count': len(files)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload files"
        )


@router.get("/upload-info", response_model=APIResponse)
async def get_upload_info():
    """Get file upload configuration and limits"""
    try:
        s3_available = s3_upload_service.is_available()
        
        return APIResponse(
            success=True,
            message="Upload configuration retrieved",
            data={
                "s3_available": s3_available,
                "max_files_per_post": settings.max_files_per_post,
                "max_file_size": settings.max_file_size,
                "max_image_size": settings.s3_max_image_size,
                "max_video_size": settings.s3_max_video_size,
                "allowed_file_types": settings.allowed_file_types,
                "allowed_image_types": s3_upload_service.ALLOWED_IMAGE_TYPES,
                "allowed_video_types": s3_upload_service.ALLOWED_VIDEO_TYPES
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get upload info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve upload information"
        )


@router.delete("/{post_id}/media", response_model=APIResponse)
async def delete_post_media(
    post_id: str,
    media_url: str = Query(..., description="URL of the media file to delete"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a specific media file from a post"""
    try:
        logger.info(f"Deleting media from post | Post ID: {post_id} | Media URL: {media_url} | User: {current_user['id']}")
        
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
                detail="Not authorized to delete media from this post"
            )
        
        # Check if media URL exists in post
        current_media_urls = existing_post.get('media_urls', [])
        if media_url not in current_media_urls:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media file not found in this post"
            )
        
        # Remove URL from post
        updated_media_urls = [url for url in current_media_urls if url != media_url]
        update_data = {"media_urls": updated_media_urls}
        
        updated_post = await post_service.update_post(post_id, update_data)
        
        # Attempt to delete from S3 (optional - don't fail if this fails)
        if s3_upload_service.is_available():
            try:
                await s3_upload_service.delete_file(media_url)
                logger.info(f"Media file deleted from S3: {media_url}")
            except Exception as delete_error:
                logger.warning(f"Failed to delete file from S3: {delete_error}")
        
        logger.info(f"Media deleted from post | Post ID: {post_id} | Remaining files: {len(updated_media_urls)}")
        
        return APIResponse(
            success=True,
            message="Media file deleted successfully",
            data={
                "post": updated_post,
                "deleted_media_url": media_url,
                "remaining_media_count": len(updated_media_urls)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error_with_context(
            logger, e,
            {
                'operation': 'delete_post_media',
                'post_id': post_id,
                'media_url': media_url,
                'user_id': current_user['id']
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete media file"
        )


@router.get("/{post_id}", response_model=APIResponse)
async def get_post(
    post_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Get a specific post by ID"""
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

@router.put("/{post_id}", response_model=APIResponse)
async def update_post(
    post_id: str,
    post_data: PostUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update a post"""
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

@router.delete("/{post_id}", response_model=APIResponse)
async def delete_post(
    post_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a post"""
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

@router.post("/{post_id}/vote", response_model=APIResponse)
async def vote_on_post(
    post_id: str,
    vote_type: str = Query(..., regex="^(up|down)$"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Vote on a post"""
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



@router.post("/{post_id}/save", response_model=APIResponse)
async def save_post(
    post_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Save/unsave a post"""
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


@router.patch("/{post_id}/status", response_model=APIResponse)
async def update_post_status(
    post_id: str,
    status_data: PostStatusUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update post status - Only authorized users (post author or assigned representative) can update"""
    logger.info(f"Updating post status | Post ID: {post_id} | New Status: {status_data.status} | User: {current_user['id']}")
    
    # Update post status with authorization checks
    updated_post = await post_service.update_post_status(
        post_id, 
        status_data.status, 
        current_user['id']
    )
    
    logger.info(f"Post status updated successfully | Post ID: {post_id} | Status: {status_data.status}")
    
    return APIResponse(
        success=True,
        message=f"Post status updated to {status_data.status} successfully",
        data={"post": updated_post}
    )


@router.patch("/{post_id}/assignee", response_model=APIResponse)
async def update_post_assignee(
    post_id: str,
    assignee_data: PostAssigneeUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update post assignee - Only authorized users (post author or current assignee) can update"""
    action = "assigned" if assignee_data.assignee else "unassigned"
    logger.info(f"Updating post assignee | Post ID: {post_id} | Action: {action} | User: {current_user['id']}")
    
    # Update post assignee with authorization checks
    updated_post = await post_service.update_post_assignee(
        post_id, 
        assignee_data.assignee, 
        current_user['id']
    )
    
    logger.info(f"Post assignee updated successfully | Post ID: {post_id} | Action: {action}")
    
    return APIResponse(
        success=True,
        message=f"Post assignee {action} successfully",
        data={"post": updated_post}
    )
    
