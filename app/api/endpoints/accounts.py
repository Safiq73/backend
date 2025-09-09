"""
Accounts API endpoints
"""

from fastapi import APIRouter, HTTPException, Path, Query, Depends
from typing import Optional, Dict, Any, List, Union
from uuid import UUID
import logging
import asyncio

from app.services.auth_service import get_current_user_optional
from app.models.pydantic_models import APIResponse, AccountStatsMetric, CitizenAccountStatsResponse, RepresentativeAccountStatsResponse, AccountStatsRequest
from app.services.post_service import PostService
from app.services.representative_evote_service import RepresentativeEVoteService

logger = logging.getLogger(__name__)

router = APIRouter()
post_service = PostService()
evote_service = RepresentativeEVoteService()

@router.post("/stats", response_model=APIResponse)
async def get_account_stats_post(
    request: AccountStatsRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Get account statistics for single or multiple accounts via POST. Supports averaging for multiple representative accounts."""
    try:
        account_ids = request.account_ids
        representative_account = request.representative_account
        if representative_account and len(account_ids) > 1:
            # Multiple representative accounts - fetch concurrently and average
            stats_data = await get_averaged_representative_stats(account_ids)
            message = "Averaged statistics for representative accounts retrieved successfully"
        elif representative_account:
            # Single representative account
            stats_data = await get_representative_account_stats(account_ids[0])
            message = "Representative account statistics retrieved successfully"
        else:
            # Single citizen account (use first ID only)
            stats_data = await get_citizen_account_stats(account_ids[0])
            message = "Account statistics retrieved successfully"
            
        return APIResponse(
            success=True,
            message=message,
            data=stats_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get {'representative' if representative_account else 'citizen'} account stats: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve {'representative' if representative_account else 'citizen'} account statistics"
        )

async def get_citizen_account_stats(account_id: UUID) -> CitizenAccountStatsResponse:
    """Get statistics for a citizen account"""
    try:
        # Get posts data using existing service
        posts = await post_service.get_posts_by_user(account_id)
        
        # Calculate citizen metrics from posts data
        posts_count = len(posts) if posts else 0
        comments_received = sum(post.get("comment_count", 0) for post in posts) if posts else 0
        upvotes_received = sum(post.get("upvotes", 0) for post in posts) if posts else 0
        
        # Calculate total views (using mock calculation for now)
        # TODO: Replace with actual view tracking when implemented
        total_views = posts_count * 127  # Mock multiplier
        
        metrics = [
            AccountStatsMetric(
                key="posts_count", 
                label="Posts", 
                value=posts_count, 
                type="number"
            ),
            AccountStatsMetric(
                key="comments_received", 
                label="Comments", 
                value=comments_received, 
                type="number"
            ),
            AccountStatsMetric(
                key="upvotes_received", 
                label="Upvotes", 
                value=upvotes_received, 
                type="number"
            ),
            AccountStatsMetric(
                key="total_views", 
                label="Views", 
                value=total_views, 
                type="number"
            )
        ]
        
        return CitizenAccountStatsResponse(
            account_type="citizen",
            account_ids=[account_id],
            metrics=metrics
        )
    except Exception as e:
        logger.error(f"Error getting citizen account stats for {account_id}: {e}")
        raise

async def get_representative_account_stats(account_id: UUID) -> RepresentativeAccountStatsResponse:
    """Get statistics for a representative account"""
    try:
        # DUMMY IMPLEMENTATION - Replace with actual database queries later
        
        # Dummy representative performance data
        issues_data = await get_dummy_representative_issues_data(account_id)
        
        total_resolved = issues_data.get('resolved_count', 45)
        total_assigned = issues_data.get('total_assigned', 60) 
        avg_response_time = issues_data.get('avg_response_time', 2.3)  # days
        avg_resolution_time = issues_data.get('avg_resolution_time', 5.2)  # days
        
        # Calculate derived metrics
        resolution_rate = (total_resolved / total_assigned * 100) if total_assigned > 0 else 0
        efficiency_score = (total_resolved / total_assigned) * (1 / avg_resolution_time) if total_assigned > 0 and avg_resolution_time > 0 else 0
        
        # Get evote stats (this uses real data from existing service)
        try:
            evote_stats = await evote_service.get_representative_evote_stats(account_id)
            evotes_received = evote_stats.total_evotes
        except Exception as e:
            logger.warning(f"Could not get evote stats for representative {account_id}: {e}")
            evotes_received = 0
        
        metrics = [
            AccountStatsMetric(
                key="total_resolved_issues", 
                label="Resolved", 
                value=total_resolved, 
                type="number"
            ),
            AccountStatsMetric(
                key="resolution_rate", 
                label="Resolution Rate", 
                value=round(resolution_rate, 1), 
                type="percentage"
            ),
            AccountStatsMetric(
                key="average_response_time", 
                label="Avg Time", 
                value=round(avg_response_time, 1), 
                type="number"
            ),
            AccountStatsMetric(
                key="efficiency_score", 
                label="Efficiency", 
                value=round(efficiency_score, 2), 
                type="number"
            )
        ]
        
        return RepresentativeAccountStatsResponse(
            account_type="representative",
            account_ids=[account_id],
            metrics=metrics,
        )
    except Exception as e:
        logger.error(f"Error getting representative account stats for {account_id}: {e}")
        raise

async def get_dummy_representative_issues_data(account_id: UUID) -> Dict[str, Any]:
    """
    DUMMY FUNCTION - Replace with actual database query
    
    This should query the database for:
    - Total issues assigned to the representative
    - Total resolved issues 
    - Average response time (time from assignment to first response)
    - Average resolution time (time from assignment to resolution)
    """
    # Simulate some variance based on account_id for demo purposes
    account_str = str(account_id)
    hash_val = hash(account_str) % 100
    
    return {
        'total_assigned': 50 + (hash_val % 30),  # 50-80 issues
        'resolved_count': 30 + (hash_val % 25),  # 30-55 resolved
        'avg_response_time': 1.5 + (hash_val % 10) * 0.2,  # 1.5-3.5 days
        'avg_resolution_time': 3.0 + (hash_val % 15) * 0.3  # 3.0-7.5 days
    }

async def get_averaged_representative_stats(account_ids: List[UUID]) -> RepresentativeAccountStatsResponse:
    """Get averaged statistics for multiple representative accounts"""
    try:
        # Fetch stats for all accounts concurrently
        tasks = [get_representative_account_stats(account_id) for account_id in account_ids]
        all_stats = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out any exceptions and keep only successful results
        valid_stats = [stats for stats in all_stats if not isinstance(stats, Exception)]
        
        if not valid_stats:
            raise Exception("No valid stats could be retrieved for the provided account IDs")
        
        # Calculate averages for each metric
        metric_sums = {}
        metric_counts = {}
        evote_sum = 0
        evote_count = 0
        
        for stats in valid_stats:
            # Process regular metrics
            for metric in stats.metrics:
                if metric.key not in metric_sums:
                    metric_sums[metric.key] = 0
                    metric_counts[metric.key] = 0
                metric_sums[metric.key] += float(metric.value)
                metric_counts[metric.key] += 1
        
        # Create averaged metrics
        averaged_metrics = []
        for key, total in metric_sums.items():
            count = metric_counts[key]
            avg_value = total / count if count > 0 else 0
            
            # Get the label and type from the first occurrence
            original_metric = None
            for stats in valid_stats:
                for metric in stats.metrics:
                    if metric.key == key:
                        original_metric = metric
                        break
                if original_metric:
                    break
            
            if original_metric:
                averaged_metrics.append(AccountStatsMetric(
                    key=key,
                    label=original_metric.label,
                    value=round(avg_value, 1) if original_metric.type == "percentage" else round(avg_value, 2),
                    type=original_metric.type
                ))

        return RepresentativeAccountStatsResponse(
            account_type="representative",
            account_ids=account_ids,
            metrics=averaged_metrics,
        )
        
    except Exception as e:
        logger.error(f"Error getting averaged representative stats for {account_ids}: {e}")
        raise
