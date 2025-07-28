"""
Corrected schemas for CivicPulse API aligned with database schema and implementation
"""

from typing import Optional, List, TypeVar, Generic, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum
import re


class UserRole(str, Enum):
    CITIZEN = "citizen"
    REPRESENTATIVE = "representative"
    ADMIN = "admin"
    MODERATOR = "moderator"


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


# User Schemas - standardized with username + display_name
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_]+$')
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=500)
    role: UserRole = UserRole.CITIZEN

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

    @validator('bio')
    def validate_bio(cls, v):
        """Validate bio content"""
        if v and len(v.strip()) == 0:
            return None
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
    cover_photo: Optional[str] = Field(None, max_length=500)


class UserResponse(UserBase):
    id: str
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Author info for posts/comments
class AuthorInfo(BaseModel):
    id: str
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None


# Post Schemas - aligned with corrected database schema
class PostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1, max_length=10000)
    post_type: PostType = PostType.DISCUSSION
    assignee: str = Field(..., description="UUID of representative assigned to handle this post")
    location: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    tags: Optional[List[str]] = Field(default_factory=list)
    media_urls: Optional[List[str]] = Field(default_factory=list)

    @validator('title')
    def validate_title(cls, v):
        """Validate post title"""
        if not v or len(v.strip()) == 0:
            raise ValueError('Title cannot be empty')
        return v.strip()

    @validator('content')
    def validate_content(cls, v):
        """Validate post content"""
        if not v or len(v.strip()) == 0:
            raise ValueError('Content cannot be empty')
        # Basic HTML/XSS prevention
        if '<script' in v.lower() or 'javascript:' in v.lower():
            raise ValueError('Content contains unsafe elements')
        return v.strip()

    @validator('media_urls')
    def validate_media_urls(cls, v):
        """Validate media URLs"""
        if v:
            for url in v:
                if not url.startswith(('http://', 'https://')):
                    raise ValueError('Invalid media URL format')
        return v

    @validator('latitude')
    def validate_latitude(cls, v):
        """Validate latitude is within India bounds"""
        if v is not None:
            # India bounds: approximately 6.5° to 37.5° N
            if not (6.5 <= v <= 37.5):
                raise ValueError('Latitude must be within India boundaries (6.5° to 37.5° N)')
        return v

    @validator('longitude')
    def validate_longitude(cls, v):
        """Validate longitude is within India bounds"""
        if v is not None:
            # India bounds: approximately 68° to 97.5° E
            if not (68.0 <= v <= 97.5):
                raise ValueError('Longitude must be within India boundaries (68° to 97.5° E)')
        return v

    @validator('assignee')
    def validate_assignee(cls, v):
        """Validate assignee is a valid UUID"""
        if not v:
            raise ValueError('Assignee is required')
        import uuid
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('Assignee must be a valid UUID')
        return v


class PostCreate(PostBase):
    pass


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    post_type: Optional[PostType] = None
    status: Optional[PostStatus] = None
    assignee: Optional[str] = Field(None, description="UUID of representative assigned to handle this post")
    location: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    tags: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None


class PostResponse(PostBase):
    id: str
    user_id: str
    author: AuthorInfo  # Consistent author info structure
    status: PostStatus = PostStatus.OPEN
    upvotes: int = 0
    downvotes: int = 0
    comment_count: int = 0
    view_count: int = 0
    share_count: int = 0
    priority_score: int = 0
    created_at: datetime
    updated_at: datetime
    last_activity_at: Optional[datetime] = None
    user_vote: Optional[VoteType] = None  # Current user's vote
    is_saved: bool = False  # Whether current user has saved this post

    class Config:
        from_attributes = True


# Comment Schemas
class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    parent_id: Optional[str] = None

    @validator('content')
    def validate_content(cls, v):
        """Validate comment content"""
        if not v or len(v.strip()) == 0:
            raise ValueError('Content cannot be empty')
        # Basic HTML/XSS prevention
        if '<script' in v.lower() or 'javascript:' in v.lower():
            raise ValueError('Content contains unsafe elements')
        return v.strip()


class CommentCreate(CommentBase):
    pass


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class CommentResponse(CommentBase):
    id: str
    post_id: str
    user_id: str
    author: AuthorInfo  # Consistent author info structure
    edited: bool = False
    edited_at: Optional[datetime] = None
    upvotes: int = 0
    downvotes: int = 0
    reply_count: int = 0
    thread_level: int = 0
    thread_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    user_vote: Optional[VoteType] = None  # Current user's vote
    replies: Optional[List['CommentResponse']] = None  # Nested replies

    class Config:
        from_attributes = True


# Vote Schemas
class VoteCreate(BaseModel):
    vote_type: VoteType


class VoteResponse(BaseModel):
    id: str
    user_id: str
    post_id: Optional[str] = None
    comment_id: Optional[str] = None
    vote_type: VoteType
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Notification Schemas
class NotificationResponse(BaseModel):
    id: str
    user_id: str
    post_id: Optional[str] = None
    comment_id: Optional[str] = None
    triggered_by_user_id: Optional[str] = None
    notification_type: NotificationType
    title: str
    message: str
    action_url: Optional[str] = None
    read: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Authentication Schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None


# Statistics Schemas
class UserStats(BaseModel):
    posts_count: int = 0
    comments_count: int = 0
    upvotes_received: int = 0


class PostStats(BaseModel):
    upvotes: int = 0
    downvotes: int = 0
    comment_count: int = 0
    view_count: int = 0
    share_count: int = 0


# Pagination
T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    has_more: bool


# API Response
class APIResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None


# Search and Filter Schemas
class PostFilter(BaseModel):
    post_type: Optional[PostType] = None
    status: Optional[PostStatus] = None
    user_id: Optional[str] = None
    tags: Optional[List[str]] = None
    search_query: Optional[str] = None


class PostSort(BaseModel):
    sort_by: str = Field(default="created_at", pattern="^(created_at|updated_at|upvotes|comment_count|priority_score)$")
    order: str = Field(default="desc", pattern="^(asc|desc)$")


# Representative Assignment Schemas
class TitleInfo(BaseModel):
    id: str
    title_name: str
    abbreviation: Optional[str] = None
    level_rank: int
    description: Optional[str] = None
    title_type: Optional[str] = None


class JurisdictionInfo(BaseModel):
    id: str
    name: str
    level_name: str
    level_rank: int


class AssigneeOption(BaseModel):
    value: str  # representative_id
    label: str  # display name
    title: TitleInfo
    jurisdiction: JurisdictionInfo


class RepresentativesByLocationResponse(BaseModel):
    assignee_options: List[AssigneeOption]
    location: Dict[str, float]
    total: int


# Enable forward references
CommentResponse.model_rebuild()
