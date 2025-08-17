"""
Pydantic schemas for the recommendation system
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID


class InteractionEventType(str, Enum):
    """Valid interaction event types"""
    impression = "impression"
    click = "click"
    like = "like"
    comment = "comment"
    share = "share"
    save = "save"
    hide = "hide"
    follow_author = "follow_author"


class EventCreate(BaseModel):
    """Schema for creating interaction events"""
    post_id: UUID = Field(..., description="ID of the post being interacted with")
    event_type: InteractionEventType = Field(..., description="Type of interaction")
    surface: Optional[str] = Field("main_feed", description="Feed surface where interaction occurred")
    session_id: Optional[str] = Field(None, description="User session identifier")
    client_timestamp: Optional[datetime] = Field(None, description="Client-side timestamp")
    dwell_time_ms: Optional[int] = Field(None, description="Time spent viewing content in milliseconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EventResponse(BaseModel):
    """Response schema for event logging"""
    success: bool
    message: str
    event_id: Optional[int] = None


class RecommendationMetadata(BaseModel):
    """Metadata about why a post was recommended"""
    score: float = Field(..., description="Overall recommendation score")
    reasons: List[str] = Field(default_factory=list, description="Human-readable reasons for recommendation")
    candidate_source: str = Field(..., description="Which generator produced this candidate")
    ranking_features: Dict[str, float] = Field(default_factory=dict, description="Features used in ranking")


class PostRecommendation(BaseModel):
    """Schema for recommended posts in feed"""
    id: UUID
    title: str
    content: Optional[str] = None
    author_id: UUID
    author_username: str
    created_at: datetime
    quality_score: float = Field(default=0.0, description="Post quality score")
    metadata: Optional[RecommendationMetadata] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FeedRequest(BaseModel):
    """Request schema for feed generation"""
    limit: int = Field(20, ge=1, le=100, description="Number of posts to return")
    cursor: Optional[str] = Field(None, description="Pagination cursor")
    surface: str = Field("main_feed", description="Feed surface type")
    include_metadata: bool = Field(False, description="Include recommendation metadata")


class FeedResponse(BaseModel):
    """Response schema for personalized feed"""
    posts: List[PostRecommendation]
    next_cursor: Optional[str] = None
    has_more: bool = False
    total_count: int
    processing_time_ms: int
    surface: str
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TopicAffinity(BaseModel):
    """User's affinity for a topic"""
    topic_id: int
    topic_name: str
    score: float
    interaction_count: int
    last_interaction_at: Optional[datetime] = None


class AuthorAffinity(BaseModel):
    """User's affinity for an author"""
    author_id: int
    author_username: str
    score: float
    interaction_count: int
    is_following: bool = False
    last_interaction_at: Optional[datetime] = None


class UserPreferences(BaseModel):
    """User's computed preferences"""
    user_id: int
    top_topics: List[TopicAffinity] = Field(default_factory=list)
    top_authors: List[AuthorAffinity] = Field(default_factory=list)
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PostQuality(BaseModel):
    """Post quality metrics"""
    post_id: int
    impressions_count: int = 0
    clicks_count: int = 0
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    saves_count: int = 0
    hides_count: int = 0
    engagement_rate: float = 0.0
    ctr_bayesian: float = 0.0
    recency_decay: float = 1.0
    quality_score: float = 0.0
    last_interaction_at: Optional[datetime] = None
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RecommendationStats(BaseModel):
    """System statistics for monitoring"""
    total_interactions_24h: int
    total_posts_with_quality: int
    user_topic_affinities: int
    user_author_affinities: int
    top_topics: List[Dict[str, Any]] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)


class CandidatePost(BaseModel):
    """Internal schema for candidate posts during generation"""
    post_id: int
    score: float
    source: str  # "social", "trending", "locality", "recency"
    author_id: int
    created_at: datetime
    features: Dict[str, float] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
