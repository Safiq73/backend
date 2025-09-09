"""
Representative eVote endpoints
Handles all eVote-related API operations
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.models.pydantic_models import (
    RepresentativeEVoteRequest,
    RepresentativeEVoteResponse,
    RepresentativeEVoteStatus,
    RepresentativeEVoteStats,
    RepresentativeEVoteTrends,
    UserEVoteHistoryResponse,
    APIResponse
)
from app.services.representative_evote_service import RepresentativeEVoteService
from app.services.auth_service import get_current_user
from app.core.logging_config import get_logger
from app.schemas import UserResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/representatives", tags=["representative-evotes"])

# Initialize service
evote_service = RepresentativeEVoteService()

# Static routes must come before parameterized routes
@router.get("/evotes/top", response_model=APIResponse)
async def get_top_evoted_representatives(
    limit: int = Query(10, ge=1, le=50, description="Number of top representatives to return")
):
    """
    Get top eVoted representatives.
    Public endpoint - no authentication required.
    """
    try:
        result = await evote_service.get_top_evoted_representatives(limit)
        return APIResponse(
            success=True,
            message="Top eVoted representatives retrieved successfully",
            data={"representatives": result}
        )
    except Exception as e:
        logger.error(f"Error getting top eVoted representatives: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get top eVoted representatives"
        )

@router.post("/{rep_id}/evote", response_model=RepresentativeEVoteResponse)
async def evote_for_representative(
    rep_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Add eVote for a representative.
    User can only eVote once per representative.
    """
    try:
        result = await evote_service.evote_for_representative(
            user_id=current_user["id"],
            rep_id=rep_id
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding eVote for user {current_user['id']} and rep {rep_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add eVote"
        )

@router.delete("/{rep_id}/evote", response_model=RepresentativeEVoteResponse)
async def remove_evote_for_representative(
    rep_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Remove eVote for a representative.
    User must have previously eVoted to remove.
    """
    try:
        result = await evote_service.remove_evote(
            user_id=UUID(current_user["id"]),
            rep_id=rep_id
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing eVote for user {current_user['id']} and rep {rep_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove eVote"
        )

@router.get("/{rep_id}/evote", response_model=RepresentativeEVoteStatus)
async def get_user_evote_status(
    rep_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Check if current user has eVoted for the representative.
    """
    try:
        result = await evote_service.get_user_evote_status(
            user_id=current_user["id"],
            rep_id=rep_id
        )
        return result
    except Exception as e:
        logger.error(f"Error getting eVote status for user {current_user['id']} and rep {rep_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get eVote status"
        )

@router.get("/{rep_id}/evote-stats", response_model=RepresentativeEVoteStats)
async def get_representative_evote_stats(rep_id: UUID):
    """
    Get eVote statistics for a representative.
    Public endpoint - no authentication required.
    """
    try:
        result = await evote_service.get_representative_evote_stats(rep_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting eVote stats for rep {rep_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get eVote statistics"
        )

@router.get("/{rep_id}/evote-trends", response_model=RepresentativeEVoteTrends)
async def get_representative_evote_trends(
    rep_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days for trend data (max 365)")
):
    """
    Get eVote trends for line graphs.
    Returns daily cumulative eVote counts.
    Public endpoint - no authentication required.
    """
    try:
        result = await evote_service.get_evote_trends(rep_id, days)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting eVote trends for rep {rep_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get eVote trends"
        )

# User-specific eVote endpoints
user_evote_router = APIRouter(prefix="/users", tags=["user-evotes"])

@user_evote_router.get("/me/evotes", response_model=UserEVoteHistoryResponse)
async def get_user_evote_history(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get current user's eVoting history.
    Returns all representatives the user has eVoted for.
    """
    try:
        result = await evote_service.get_user_evote_history(
            user_id=UUID(current_user["id"]),
            page=page,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"Error getting eVote history for user {current_user['id']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get eVote history"
        )

# Include user router in main router
router.include_router(user_evote_router)
