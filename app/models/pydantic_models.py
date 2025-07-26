"""
Pydantic models for CivicPulse API - Corrected and aligned with database schema
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum
import re

# Role models - now using foreign key relationship
class RoleBase(BaseModel):
    role_name: str = Field(..., min_length=1, max_length=100)
    abbreviation: Optional[str] = Field(None, max_length=20)
    level_rank: Optional[int] = None
    role_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    level: Optional[str] = Field(None, max_length=50)
    is_elected: bool = False
    term_length: Optional[int] = None
    status: str = Field(default="active", max_length=20)

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    role_name: Optional[str] = Field(None, min_length=1, max_length=100)
    abbreviation: Optional[str] = Field(None, max_length=20)
    level_rank: Optional[int] = None
    role_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    level: Optional[str] = Field(None, max_length=50)
    is_elected: Optional[bool] = None
    term_length: Optional[int] = None
    status: Optional[str] = Field(None, max_length=20)

class RoleResponse(RoleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PostType(str, Enum):
    ISSUE = "issue"
    ANNOUNCEMENT = "announcement"
    NEWS = "news"
    ACCOMPLISHMENT = "accomplishment"
    DISCUSSION = "discussion"

class PostStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class VoteType(str, Enum):
    UPVOTE = "upvote"
    DOWNVOTE = "downvote"

class NotificationType(str, Enum):
    ISSUE_UPDATE = "issue_update"
    COMMENT = "comment"
    VOTE = "vote"
    ASSIGNMENT = "assignment"
    RESOLUTION = "resolution"
    MENTION = "mention"
    FOLLOW = "follow"

# Base model classes
class BaseModelWithTimestamps(BaseModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# User models - standardized with username + display_name
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=500)
    role: Optional[UUID] = None  # Foreign key to role table

    @validator('username')
    def validate_username(cls, v):
        """Validate username format and restrictions"""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        reserved_names = ['admin', 'api', 'www', 'support', 'help', 'system', 'root']
        if v.lower() in reserved_names:
            raise ValueError('This username is reserved')
        return v.lower()

    @validator('display_name')
    def validate_display_name(cls, v):
        """Validate display name"""
        if v and len(v.strip()) == 0:
            raise ValueError('Display name cannot be empty')
        return v.strip() if v else None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=500)

class UserResponse(UserBase):
    id: UUID
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime
    role_info: Optional[RoleResponse] = None  # Populated role information

    class Config:
        from_attributes = True

# Author info for posts/comments
class AuthorInfo(BaseModel):
    id: UUID
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role_info: Optional[RoleResponse] = None  # Populated role information

# Post models - aligned with corrected schema
class PostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1, max_length=10000)
    post_type: PostType = PostType.DISCUSSION
    area: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = Field(default_factory=list)
    media_urls: Optional[List[str]] = Field(default_factory=list)

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    post_type: Optional[PostType] = None
    status: Optional[PostStatus] = None
    area: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None

class PostResponse(PostBase, BaseModelWithTimestamps):
    id: UUID
    user_id: UUID
    author: AuthorInfo
    status: PostStatus = PostStatus.OPEN
    upvotes: int = 0
    downvotes: int = 0
    comment_count: int = 0
    view_count: int = 0
    share_count: int = 0
    priority_score: int = 0
    last_activity_at: Optional[datetime] = None
    user_vote: Optional[VoteType] = None  # Current user's vote
    is_saved: bool = False  # Whether current user has saved this post

    class Config:
        from_attributes = True

# Comment models
class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    parent_id: Optional[UUID] = None

class CommentCreate(CommentBase):
    pass

class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

class CommentResponse(CommentBase, BaseModelWithTimestamps):
    id: UUID
    post_id: UUID
    user_id: UUID
    author: AuthorInfo
    edited: bool = False
    edited_at: Optional[datetime] = None
    upvotes: int = 0
    downvotes: int = 0
    reply_count: int = 0
    thread_level: int = 0
    thread_path: Optional[str] = None
    user_vote: Optional[VoteType] = None  # Current user's vote
    replies: Optional[List['CommentResponse']] = None  # Nested replies

    class Config:
        from_attributes = True

# Vote models
class VoteCreate(BaseModel):
    vote_type: VoteType

class VoteResponse(BaseModelWithTimestamps):
    id: UUID
    user_id: UUID
    post_id: Optional[UUID] = None
    comment_id: Optional[UUID] = None
    vote_type: VoteType

    class Config:
        from_attributes = True

# Notification models
class NotificationResponse(BaseModelWithTimestamps):
    id: UUID
    user_id: UUID
    post_id: Optional[UUID] = None
    comment_id: Optional[UUID] = None
    triggered_by_user_id: Optional[UUID] = None
    notification_type: NotificationType
    title: str
    message: str
    action_url: Optional[str] = None
    read: bool = False
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# API Response models for pagination
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    has_more: bool

class PostListResponse(BaseModel):
    posts: List[PostResponse]
    total: int
    page: int
    size: int
    has_more: bool

class CommentListResponse(BaseModel):
    comments: List[CommentResponse]
    total: int
    page: int
    size: int
    has_more: bool

# Authentication models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    username: Optional[str] = None
    email: Optional[str] = None

# API Response wrapper
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None

# Statistics models
class UserStats(BaseModel):
    posts_count: int = 0
    comments_count: int = 0
    upvotes_received: int = 0
    following_count: int = 0
    followers_count: int = 0

class PostStats(BaseModel):
    upvotes: int = 0
    downvotes: int = 0
    comment_count: int = 0
    view_count: int = 0
    share_count: int = 0

# Search and filter models
class PostFilter(BaseModel):
    post_type: Optional[PostType] = None
    status: Optional[PostStatus] = None
    area: Optional[str] = None
    category: Optional[str] = None
    user_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    search_query: Optional[str] = None

class PostSort(BaseModel):
    sort_by: str = Field(default="created_at", pattern="^(created_at|updated_at|upvotes|comment_count|priority_score)$")
    order: str = Field(default="desc", pattern="^(asc|desc)$")

# Enable forward references
CommentResponse.model_rebuild()
