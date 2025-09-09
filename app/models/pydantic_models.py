"""
Pydantic models for CivicPulse API - Corrected and aligned with database schema
"""

from pydantic import BaseModel, Field, EmailStr, validator, model_validator
from typing import Optional, List, Dict, Any, Union, TypeVar, Generic
from datetime import datetime
from uuid import UUID
from enum import Enum
import re

# Title models - now using foreign key relationship
class TitleBase(BaseModel):
    title_name: str = Field(..., min_length=1, max_length=100)
    abbreviation: Optional[str] = Field(None, max_length=20)
    level_rank: Optional[int] = None
    title_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    level: Optional[str] = Field(None, max_length=50)
    is_elected: bool = False
    term_length: Optional[int] = None
    status: str = Field(default="active", max_length=20)

class TitleCreate(TitleBase):
    pass

class TitleUpdate(BaseModel):
    title_name: Optional[str] = Field(None, min_length=1, max_length=100)
    abbreviation: Optional[str] = Field(None, max_length=20)
    level_rank: Optional[int] = None
    title_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    level: Optional[str] = Field(None, max_length=50)
    is_elected: Optional[bool] = None
    term_length: Optional[int] = None
    status: Optional[str] = Field(None, max_length=20)

class TitleResponse(TitleBase):
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
    title: Optional[UUID] = None  # Foreign key to titles table

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
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format and restrictions"""
        if v is None:
            return v
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

class UserResponse(UserBase):
    id: UUID
    is_active: bool = True
    is_verified: bool = False
    followers_count: int = 0
    following_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Author info for posts/comments
class AuthorInfo(BaseModel):
    id: UUID
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    rep_accounts: List['RepresentativeWithDetails'] = []  # Representative account details

# Post models - aligned with corrected schema
class PostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1, max_length=10000)
    post_type: PostType = PostType.DISCUSSION
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
    post_id: UUID = Field(..., description="UUID of the post to comment on")

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

# Push notification models
class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str

class PushSubscriptionCreate(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys

class PushSubscriptionResponse(BaseModelWithTimestamps):
    id: UUID
    endpoint: str
    is_active: bool

    class Config:
        from_attributes = True

# Define type variable for generic responses
T = TypeVar('T')

# API Response models for pagination
class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
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
    user_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    search_query: Optional[str] = None

class PostSort(BaseModel):
    sort_by: str = Field(default="created_at", pattern="^(created_at|updated_at|upvotes|comment_count|priority_score)$")
    order: str = Field(default="desc", pattern="^(asc|desc)$")

# Representative models
class RepresentativeBase(BaseModel):
    jurisdiction_id: UUID
    title_id: UUID

# Enhanced title information model
class TitleInfo(BaseModel):
    id: UUID
    title_name: str
    abbreviation: Optional[str] = None
    level_rank: Optional[int] = None
    title_type: Optional[str] = None
    description: Optional[str] = None
    level: Optional[str] = None
    is_elected: Optional[bool] = None
    term_length: Optional[int] = None
    status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Enhanced jurisdiction information model  
class JurisdictionInfo(BaseModel):
    id: UUID
    name: str
    level_name: str
    level_rank: int
    parent_jurisdiction_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Enhanced representative response with detailed info
class RepresentativeWithDetails(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    evote_count: int = 0
    created_at: datetime
    updated_at: datetime
    title_info: TitleInfo
    jurisdiction_info: JurisdictionInfo

    class Config:
        from_attributes = True

# Legacy representative response for backward compatibility
class RepresentativeResponse(RepresentativeBase, BaseModelWithTimestamps):
    id: UUID
    user_id: Optional[UUID] = None
    jurisdiction_name: str
    jurisdiction_level: str
    title_name: str
    abbreviation: Optional[str] = None
    level_rank: Optional[int] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True

class RepresentativeLinkRequest(BaseModel):
    representative_id: UUID

class UserWithRepresentativeResponse(UserResponse):
    rep_accounts: List[RepresentativeWithDetails] = []

# Public user response without email for public profiles
class PublicUserResponse(BaseModel):
    id: UUID
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    title: Optional[UUID] = None
    is_active: bool = True
    is_verified: bool = False
    followers_count: int = 0
    following_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PublicUserWithRepresentativeResponse(PublicUserResponse):
    rep_accounts: List[RepresentativeWithDetails] = []

# Follow/Following models
class FollowUser(BaseModel):
    id: UUID
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_verified: bool = False
    mutual: bool = False
    followed_at: datetime

    class Config:
        from_attributes = True

class FollowResponse(BaseModel):
    success: bool = True
    message: str
    mutual: bool = False

class UnfollowResponse(BaseModel):
    success: bool = True
    message: str

class FollowersListResponse(BaseModel):
    followers: List[FollowUser]
    total_count: int
    page: int
    size: int
    has_next: bool

class FollowingListResponse(BaseModel):
    following: List[FollowUser]
    total_count: int
    page: int
    size: int
    has_next: bool

class FollowStatsResponse(BaseModel):
    followers_count: int
    following_count: int
    mutual_follows_count: int

# eVote models
class RepresentativeEVoteRequest(BaseModel):
    """Request model for eVoting"""
    pass  # No additional fields needed, rep_id comes from URL

class RepresentativeEVoteResponse(BaseModel):
    """Response model for eVote operations"""
    success: bool = True
    message: str
    has_evoted: bool = False
    total_evotes: int = 0

class RepresentativeEVoteStatus(BaseModel):
    """Model for checking user's eVote status"""
    has_evoted: bool = False
    evoted_at: Optional[datetime] = None

class RepresentativeEVoteStats(BaseModel):
    """Model for representative eVote statistics"""
    representative_id: UUID
    total_evotes: int = 0
    evote_percentage: Optional[float] = None  # Percentage of total registered users
    rank: Optional[int] = None  # Rank among all representatives

class EVoteTrendData(BaseModel):
    """Model for eVote trend data points"""
    date: str  # ISO date format
    total_evotes: int

class RepresentativeEVoteTrends(BaseModel):
    """Model for eVote trends response"""
    representative_id: UUID
    period_days: int
    trends: List[EVoteTrendData]
    current_total: int
    period_change: int  # Change from start to end of period

class UserEVoteHistory(BaseModel):
    """Model for user's eVoting history"""
    representative_id: UUID
    representative_name: str
    title_info: TitleInfo
    jurisdiction_info: JurisdictionInfo
    evoted_at: datetime
    is_active: bool = True  # Whether the eVote is still active

class UserEVoteHistoryResponse(BaseModel):
    """Response model for user's eVoting history"""
    evotes: List[UserEVoteHistory]
    total_count: int
    active_evotes_count: int

class AccountStatsMetric(BaseModel):
    """Model for individual account statistics metric"""
    key: str
    label: str
    value: Union[int, float, str]
    type: str  # "number", "string", "percentage", etc.

class AccountStatsResponse(BaseModel):
    """Model for structured account statistics response"""
    account_type: str
    account_ids: List[UUID]
    metrics: List[AccountStatsMetric]
    evotes: Optional[AccountStatsMetric] = None  # Single object, only for representatives

class CitizenAccountStatsResponse(BaseModel):
    """Model for citizen account statistics response (no evotes)"""
    account_type: str
    account_ids: List[UUID]
    metrics: List[AccountStatsMetric]

class RepresentativeAccountStatsResponse(BaseModel):
    """Model for representative account statistics response"""
    account_type: str
    account_ids: List[UUID]
    metrics: List[AccountStatsMetric]

class AccountStatsRequest(BaseModel):
    """Request model for fetching account statistics"""
    account_ids: List[UUID]
    representative_account: bool = Field(False, description="Whether these are representative accounts")

    @validator('account_ids')
    def must_have_at_least_one_id(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one account ID must be provided")
        return v

    @model_validator(mode='after')
    def validate_account_ids_for_type(cls, values):
        """Validate account_ids count based on account type"""
        account_ids = values.account_ids
        representative_account = values.representative_account
        
        if not representative_account and len(account_ids) > 1:
            raise ValueError("For citizen account stats (representative_account is false), you must provide exactly one account ID.")
        
        return values

# Enable forward references
CommentResponse.model_rebuild()
AuthorInfo.model_rebuild()

