"""
Representative eVote service layer
Handles all eVote-related operations including voting, statistics, and trends
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import date, timedelta, datetime
from fastapi import HTTPException

from app.services.db_service import DatabaseService
from app.db.database import db_manager
from app.db.queries import RepresentativeEVoteQueries
from app.models.pydantic_models import (
    RepresentativeEVoteResponse,
    RepresentativeEVoteStatus,
    RepresentativeEVoteStats,
    EVoteTrendData,
    RepresentativeEVoteTrends,
    UserEVoteHistory,
    UserEVoteHistoryResponse,
    TitleInfo,
    JurisdictionInfo
)

logger = logging.getLogger(__name__)

class RepresentativeEVoteService:
    """Service for representative eVote operations"""
    
    def __init__(self):
        self.db_service = DatabaseService()
        self.queries = RepresentativeEVoteQueries()
    
    async def evote_for_representative(self, user_id: UUID, rep_id: UUID) -> RepresentativeEVoteResponse:
        """Add eVote for representative"""
        async with db_manager.get_connection() as conn:
            async with conn.transaction():
                # Check if user already voted
                existing_vote = await conn.fetchrow(self.queries.CHECK_USER_EVOTE, user_id, rep_id)
                
                if existing_vote:
                    raise HTTPException(
                        status_code=400, 
                        detail="User has already eVoted for this representative"
                    )
                
                # Add the eVote
                evote_record = await conn.fetchrow(self.queries.ADD_EVOTE, user_id, rep_id)
                
                if not evote_record:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to add eVote"
                    )
                
                # Update daily count (+1)
                await self._update_daily_count(conn, rep_id, 1)
                
                # Get updated total
                total_evotes = await conn.fetchval(self.queries.GET_TOTAL_EVOTES, rep_id)
                
                logger.info(f"User {user_id} eVoted for representative {rep_id}")
                
                return RepresentativeEVoteResponse(
                    success=True,
                    message="eVote added successfully",
                    has_evoted=True,
                    total_evotes=total_evotes or 0
                )
    
    async def remove_evote(self, user_id: UUID, rep_id: UUID) -> RepresentativeEVoteResponse:
        """Remove eVote for representative"""
        async with db_manager.get_connection() as conn:
            async with conn.transaction():
                # Check if user has voted (must exist to remove)
                existing_vote = await conn.fetchrow(self.queries.CHECK_USER_EVOTE, user_id, rep_id)
                
                if not existing_vote:
                    raise HTTPException(
                        status_code=400,
                        detail="User has not eVoted for this representative"
                    )
                
                # Remove the eVote
                removed_record = await conn.fetchrow(self.queries.REMOVE_EVOTE, user_id, rep_id)
                
                if not removed_record:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to remove eVote"
                    )
                
                # Update daily count (-1)
                await self._update_daily_count(conn, rep_id, -1)
                
                # Get updated total
                total_evotes = await conn.fetchval(self.queries.GET_TOTAL_EVOTES, rep_id)
                
                logger.info(f"User {user_id} removed eVote for representative {rep_id}")
                
                return RepresentativeEVoteResponse(
                    success=True,
                    message="eVote removed successfully",
                    has_evoted=False,
                    total_evotes=total_evotes or 0
                )
    
    async def get_user_evote_status(self, user_id: UUID, rep_id: UUID) -> RepresentativeEVoteStatus:
        """Check if user has eVoted for representative"""
        async with db_manager.get_connection() as conn:
            evote_record = await conn.fetchrow(self.queries.CHECK_USER_EVOTE, user_id, rep_id)
            
            if evote_record:
                return RepresentativeEVoteStatus(
                    has_evoted=True,
                    evoted_at=evote_record['created_at']
                )
            else:
                return RepresentativeEVoteStatus(has_evoted=False)
    
    async def get_representative_evote_stats(self, rep_id: UUID) -> RepresentativeEVoteStats:
        """Get eVote statistics for representative"""
        async with db_manager.get_connection() as conn:
            stats = await conn.fetchrow(self.queries.GET_EVOTE_STATS, rep_id)
            
            if not stats:
                raise HTTPException(
                    status_code=404,
                    detail="Representative not found"
                )
            
            return RepresentativeEVoteStats(
                representative_id=rep_id,
                total_evotes=stats['total_evotes'] or 0,
                evote_percentage=stats['evote_percentage'],
                rank=stats['rank']
            )
    
    async def get_evote_trends(self, rep_id: UUID, days: int = 30) -> RepresentativeEVoteTrends:
        """Get eVote trends for line graphs"""
        start_date = date.today() - timedelta(days=days)
        
        async with db_manager.get_connection() as conn:
            # Get all records for this representative within the date range
            db_records = await conn.fetch(self.queries.GET_EVOTE_TRENDS, rep_id, start_date)
            
            # Convert to dictionary for easy lookup
            records_dict = {record['date']: record['total_evotes'] for record in db_records}
            
            # Get the baseline count (most recent count before our range)
            baseline = await conn.fetchval(self.queries.GET_LAST_DAILY_COUNT, rep_id, start_date)
            current_count = baseline or 0
            
            # Generate the trend data
            trends = []
            start_count = current_count
            
            for i in range(days + 1):
                current_date = start_date + timedelta(days=i)
                
                # If there's a record for this date, use it
                if current_date in records_dict:
                    current_count = records_dict[current_date]
                
                # Add the current count
                trends.append(EVoteTrendData(
                    date=current_date.isoformat(),
                    total_evotes=current_count
                ))
            
            # Calculate period change
            period_change = current_count - start_count
            
            return RepresentativeEVoteTrends(
                representative_id=rep_id,
                period_days=days,
                trends=trends,
                current_total=current_count,
                period_change=period_change
            )
    
    async def get_user_evote_history(
        self, 
        user_id: UUID, 
        page: int = 1, 
        limit: int = 20
    ) -> UserEVoteHistoryResponse:
        """Get user's eVoting history"""
        offset = (page - 1) * limit
        
        async with db_manager.get_connection() as conn:
            # Get total count
            total_count = await conn.fetchval(self.queries.GET_USER_EVOTES_COUNT, user_id) or 0
            
            # Get paginated history
            history_records = await conn.fetch(
                self.queries.GET_USER_EVOTE_HISTORY, 
                user_id, 
                limit, 
                offset
            )
            
            # Build response objects
            evotes = []
            for record in history_records:
                # Build title info
                title_info = TitleInfo(
                    id=record['title_id'],
                    title_name=record['title_name'],
                    abbreviation=record['abbreviation'],
                    level_rank=record['level_rank'],
                    title_type=record['title_type'],
                    description=record['title_description'],
                    level=record['level'],
                    is_elected=record['is_elected'],
                    term_length=record['term_length'],
                    status=record['title_status'],
                    created_at=record['title_created_at'],
                    updated_at=record['title_updated_at']
                )
                
                # Build jurisdiction info
                jurisdiction_info = JurisdictionInfo(
                    id=record['jurisdiction_id'],
                    name=record['jurisdiction_name'],
                    level_name=record['jurisdiction_level_name'],
                    level_rank=record['jurisdiction_level_rank'],
                    parent_jurisdiction_id=record['parent_jurisdiction_id'],
                    created_at=record['jurisdiction_created_at'],
                    updated_at=record['jurisdiction_updated_at']
                )
                
                evotes.append(UserEVoteHistory(
                    representative_id=record['representative_id'],
                    representative_name=f"{title_info.title_name} - {jurisdiction_info.name}",
                    title_info=title_info,
                    jurisdiction_info=jurisdiction_info,
                    evoted_at=record['evoted_at'],
                    is_active=True  # All records in the table are active eVotes
                ))
            
            return UserEVoteHistoryResponse(
                evotes=evotes,
                total_count=total_count,
                active_evotes_count=total_count  # All are active since we only store active eVotes
            )
    
    async def get_top_evoted_representatives(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top eVoted representatives"""
        async with db_manager.get_connection() as conn:
            records = await conn.fetch(self.queries.GET_TOP_EVOTED_REPRESENTATIVES, limit)
            
            return [
                {
                    "representative_id": record['id'],
                    "evote_count": record['evote_count'],
                    "title_name": record['title_name'],
                    "jurisdiction_name": record['jurisdiction_name']
                }
                for record in records
            ]
    
    async def _update_daily_count(self, conn, rep_id: UUID, increment: int):
        """Update today's cumulative count ONLY if there's a transaction"""
        today = date.today()
        
        # Check if today already has a record
        today_count = await conn.fetchval(self.queries.GET_TODAY_DAILY_COUNT, rep_id, today)
        
        if today_count is not None:
            # Update existing record for today
            new_total = today_count + increment
            await conn.execute(self.queries.UPDATE_DAILY_COUNT, rep_id, today, new_total)
            logger.info(f"Updated daily count for rep {rep_id} on {today}: {today_count} -> {new_total}")
        else:
            # No record for today yet, get the most recent count
            last_count = await conn.fetchval(self.queries.GET_LAST_DAILY_COUNT, rep_id, today)
            
            # If no previous records exist, start from 0
            previous_count = last_count or 0
            new_total = previous_count + increment
            
            # Create new record for today (only because there's a transaction)
            await conn.execute(self.queries.INSERT_DAILY_COUNT, rep_id, today, new_total)
            logger.info(f"Created daily count for rep {rep_id} on {today}: {new_total} (previous: {previous_count})")
