# Follow/Unfollow Functionality Documentation

## Overview

This document describes the implementation of user follow/unfollow functionality for the CivicPulse backend API. The system allows users to follow and unfollow each other, with automatic tracking of mutual relationships.

## Database Schema

### Follows Table

```sql
CREATE TABLE follows (
    follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    followed_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mutual BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (follower_id, followed_id),
    CONSTRAINT no_self_follow CHECK (follower_id != followed_id)
);
```

### Key Features:
- **Primary Key**: Combination of `follower_id` and `followed_id` prevents duplicate follows
- **Mutual Column**: Automatically updated when both users follow each other
- **Self-Follow Prevention**: Database constraint prevents users from following themselves
- **Cascade Deletion**: Follow relationships are cleaned up when users are deleted

### User Table Extensions

```sql
ALTER TABLE users ADD COLUMN followers_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN following_count INTEGER DEFAULT 0;
```

## Database Triggers

### Mutual Status Trigger
Automatically updates the `mutual` column when follow relationships are created or deleted:

```sql
CREATE OR REPLACE FUNCTION update_mutual_status()
RETURNS TRIGGER AS $$
BEGIN
    -- Updates mutual status in both directions when follows are added/removed
END;
$$ LANGUAGE plpgsql;
```

### Follow Count Trigger
Automatically maintains user follow counts:

```sql
CREATE OR REPLACE FUNCTION update_user_follow_counts()
RETURNS TRIGGER AS $$
BEGIN
    -- Increments/decrements follow counts on users table
END;
$$ LANGUAGE plpgsql;
```

## API Endpoints

### 1. Follow User
**POST** `/users/{user_id}/follow`

Follow a specific user.

**Parameters:**
- `user_id` (path): UUID of the user to follow

**Authentication:** Required (Bearer token)

**Response:**
```json
{
    "success": true,
    "message": "User followed successfully",
    "data": {
        "success": true,
        "message": "User followed successfully",
        "mutual": false
    }
}
```

**Error Cases:**
- `400`: User cannot follow themselves
- `400`: User is already being followed
- `404`: User to follow not found
- `401`: Authentication required

### 2. Unfollow User
**DELETE** `/users/{user_id}/unfollow`

Unfollow a specific user.

**Parameters:**
- `user_id` (path): UUID of the user to unfollow

**Authentication:** Required (Bearer token)

**Response:**
```json
{
    "success": true,
    "message": "User unfollowed successfully",
    "data": {
        "success": true,
        "message": "User unfollowed successfully"
    }
}
```

**Error Cases:**
- `400`: User is not being followed
- `401`: Authentication required

### 3. Get Followers
**GET** `/users/{user_id}/followers`

Get list of users following the specified user.

**Parameters:**
- `user_id` (path): UUID of the user
- `page` (query): Page number (default: 1)
- `size` (query): Items per page (default: 20, max: 100)

**Authentication:** Required (Bearer token)

**Response:**
```json
{
    "success": true,
    "message": "Followers retrieved successfully",
    "data": {
        "followers": [
            {
                "id": "uuid",
                "username": "username",
                "display_name": "Display Name",
                "avatar_url": "url",
                "is_verified": false,
                "mutual": true,
                "followed_at": "2025-07-30T10:00:00Z"
            }
        ],
        "total_count": 25,
        "page": 1,
        "size": 20,
        "has_next": true
    }
}
```

### 4. Get Following
**GET** `/users/{user_id}/following`

Get list of users that the specified user is following.

**Parameters:**
- `user_id` (path): UUID of the user
- `page` (query): Page number (default: 1)
- `size` (query): Items per page (default: 20, max: 100)

**Authentication:** Required (Bearer token)

**Response:**
```json
{
    "success": true,
    "message": "Following list retrieved successfully",
    "data": {
        "following": [
            {
                "id": "uuid",
                "username": "username",
                "display_name": "Display Name",
                "avatar_url": "url",
                "is_verified": false,
                "mutual": true,
                "followed_at": "2025-07-30T10:00:00Z"
            }
        ],
        "total_count": 15,
        "page": 1,
        "size": 20,
        "has_next": false
    }
}
```

### 5. Get Follow Statistics
**GET** `/users/{user_id}/follow-stats`

Get follow statistics for a user.

**Parameters:**
- `user_id` (path): UUID of the user

**Authentication:** Required (Bearer token)

**Response:**
```json
{
    "success": true,
    "message": "Follow statistics retrieved successfully",
    "data": {
        "followers_count": 25,
        "following_count": 15,
        "mutual_follows_count": 8
    }
}
```

### 6. Check Follow Status
**GET** `/users/{user_id}/follow-status`

Check follow relationship status between current user and specified user.

**Parameters:**
- `user_id` (path): UUID of the user to check status with

**Authentication:** Required (Bearer token)

**Response:**
```json
{
    "success": true,
    "message": "Follow status retrieved successfully",
    "data": {
        "is_following": true,
        "is_followed_by": false,
        "mutual": false
    }
}
```

## Service Layer Architecture

### FollowService
Main service class handling follow/unfollow business logic:
- Input validation and error handling
- Prevents self-following
- Manages duplicate follow attempts
- Integrates with database service

### DatabaseService Extensions
New methods added to handle follow operations:
- `follow_user()`: Create follow relationship
- `unfollow_user()`: Remove follow relationship
- `get_user_followers()`: Get followers list with pagination
- `get_user_following()`: Get following list with pagination
- `get_follow_stats()`: Get aggregated follow statistics
- `check_follow_status()`: Check relationship between two users

## Pydantic Models

### Request/Response Models
```python
class FollowResponse(BaseModel):
    success: bool = True
    message: str
    mutual: bool = False

class FollowUser(BaseModel):
    id: UUID
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_verified: bool = False
    mutual: bool = False
    followed_at: datetime

class FollowersListResponse(BaseModel):
    followers: List[FollowUser]
    total_count: int
    page: int
    size: int
    has_next: bool
```

### Updated UserResponse
```python
class UserResponse(UserBase):
    id: UUID
    is_active: bool = True
    is_verified: bool = False
    followers_count: int = 0
    following_count: int = 0
    created_at: datetime
    updated_at: datetime
```

## Security Considerations

1. **Authentication**: All endpoints require valid Bearer token
2. **Authorization**: Users can only perform actions on behalf of themselves
3. **Input Validation**: UUIDs are validated, pagination limits enforced
4. **Self-Follow Prevention**: Database constraint and application-level checks
5. **Rate Limiting**: Should be applied to prevent follow/unfollow spam

## Performance Optimizations

1. **Database Indexes**: Comprehensive indexing on follow table
2. **Denormalized Counts**: Follow counts stored in users table for quick access
3. **Pagination**: All list endpoints support pagination
4. **Connection Pooling**: Async database connection pool for scalability

## Installation and Setup

1. **Run Migration**:
   ```bash
   cd backend
   python run_migration.py
   ```

2. **Update API Router**: The follow endpoints are automatically included in the API

3. **Test Functionality**:
   ```bash
   python test_follow_simple.py
   ```

## Testing

### Test Cases Covered
1. User registration and authentication
2. Basic follow/unfollow operations
3. Mutual follow detection
4. Follow counts and statistics
5. Pagination of followers/following lists
6. Error handling (self-follow, double-follow, etc.)

### Running Tests
```bash
# Make sure server is running
python run.py

# In another terminal
python test_follow_simple.py
```

## Future Enhancements

1. **Follow Notifications**: Notify users when they gain new followers
2. **Follow Suggestions**: Suggest users to follow based on mutual connections
3. **Private Profiles**: Allow users to require approval for follows
4. **Follow Categories**: Allow users to categorize who they follow
5. **Activity Feeds**: Show activities from followed users
6. **Follow Limits**: Implement maximum follow limits to prevent spam

## Database Maintenance

### Monitor Follow Counts
```sql
-- Check for any discrepancies in follow counts
SELECT 
    u.id,
    u.username,
    u.followers_count,
    u.following_count,
    (SELECT COUNT(*) FROM follows WHERE followed_id = u.id) as actual_followers,
    (SELECT COUNT(*) FROM follows WHERE follower_id = u.id) as actual_following
FROM users u
WHERE 
    u.followers_count != (SELECT COUNT(*) FROM follows WHERE followed_id = u.id)
    OR u.following_count != (SELECT COUNT(*) FROM follows WHERE follower_id = u.id);
```

### Repair Follow Counts
```sql
-- Repair any inconsistent follow counts
UPDATE users SET 
    followers_count = (SELECT COUNT(*) FROM follows WHERE followed_id = users.id),
    following_count = (SELECT COUNT(*) FROM follows WHERE follower_id = users.id);
```

## Error Codes and Messages

| Status Code | Error Message | Description |
|-------------|---------------|-------------|
| 400 | "Users cannot follow themselves" | Self-follow attempt |
| 400 | "User is already being followed" | Duplicate follow attempt |
| 400 | "User is not being followed" | Unfollow non-followed user |
| 401 | "User not authenticated" | Missing or invalid auth token |
| 404 | "User not found" | Target user doesn't exist |
| 500 | "Internal server error" | Unexpected server error |
