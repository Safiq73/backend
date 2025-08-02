# Post Status Update API Documentation

## Overview

The Post Status Update API allows authorized users to update the status of posts in the CivicPulse system. This endpoint includes proper authorization checks to ensure only the post author or assigned representatives can modify the post status.

## Endpoint Details

**URL:** `PATCH /api/v1/posts/{post_id}/status`

**Authentication:** Required (JWT Bearer token)

**Authorization:** 
- Post author can always update status
- If post has an assignee, the user linked to that representative account can update status
- All other users will receive a 403 Forbidden error

## Request

### Path Parameters

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| post_id   | string | Yes      | UUID of the post to update |

### Request Body

```json
{
  "status": "in_progress"
}
```

| Field  | Type   | Required | Description | Valid Values |
|--------|--------|----------|-------------|--------------|
| status | string | Yes      | New status for the post | "open", "in_progress", "resolved", "closed" |

### Example Request

```bash
curl -X PATCH "http://localhost:8000/api/v1/posts/123e4567-e89b-12d3-a456-426614174000/status" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in_progress"
  }'
```

## Response

### Success Response (200 OK)

```json
{
  "success": true,
  "message": "Post status updated to in_progress successfully",
  "data": {
    "post": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "title": "Road repair needed on Main Street",
      "content": "The road has multiple potholes that need immediate attention.",
      "post_type": "issue",
      "status": "in_progress",
      "location": "Main Street, Mumbai",
      "author": {
        "id": "user-uuid",
        "username": "john_doe",
        "display_name": "John Doe",
        "avatar_url": "https://example.com/avatar.jpg",
        "rep_accounts": []
      },
      "assignee": "rep-uuid",
      "upvotes": 15,
      "downvotes": 2,
      "comment_count": 8,
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T14:22:00Z",
      "last_activity_at": "2025-01-15T14:22:00Z",
      "is_upvoted": false,
      "is_downvoted": false,
      "is_saved": false
    }
  }
}
```

### Error Responses

#### 400 Bad Request
```json
{
  "success": false,
  "message": "Invalid status value",
  "error": "Status must be one of: open, in_progress, resolved, closed"
}
```

#### 401 Unauthorized
```json
{
  "success": false,
  "message": "Authentication required",
  "error": "Missing or invalid authorization token"
}
```

#### 403 Forbidden
```json
{
  "success": false,
  "message": "Not authorized to update post status. Only post author or assigned representatives can update status.",
  "error": "Insufficient permissions"
}
```

#### 404 Not Found
```json
{
  "success": false,
  "message": "Post not found",
  "error": "No post found with the provided ID"
}
```

#### 500 Internal Server Error
```json
{
  "success": false,
  "message": "Failed to update post status",
  "error": "Internal server error occurred"
}
```

## Authorization Logic

The authorization system checks the following conditions in order:

1. **Post Author Check**: If the current user is the author of the post, they are authorized to update the status.

2. **Representative Assignment Check**: 
   - If the post has an `assignee` (representative UUID)
   - Get the user's linked representative accounts
   - If any of the user's representative accounts match the post's assignee, they are authorized

3. **Denial**: If neither condition is met, the request is denied with a 403 error.

## Implementation Details

### Service Layer (PostService)

The `update_post_status` method in `PostService` handles:
- Post existence validation
- Authorization checks via `_check_post_status_authorization`
- Status update via `DatabaseService`
- Response formatting

### Authorization Method

```python
async def _check_post_status_authorization(self, post: Dict[str, Any], user_id: UUID) -> bool:
    """Check if user is authorized to update post status"""
    # Check if user is the post author
    if UUID(post['author']['id']) == user_id:
        return True
    
    # Check if post has an assignee and user is linked to that representative
    assignee_id = post.get('assignee')
    if assignee_id:
        user_rep_accounts = await rep_service.get_user_rep_accounts(user_id)
        for rep_account in user_rep_accounts:
            if str(rep_account['id']) == str(assignee_id):
                return True
    
    return False
```

### Database Layer

The `update_post_status` method in `DatabaseService`:
- Updates the post status
- Updates `updated_at` and `last_activity_at` timestamps
- Returns the full updated post with author information

## Status Workflow

The typical status workflow for posts:

1. **open** → Initial state when post is created
2. **in_progress** → Representative or author has started working on the issue
3. **resolved** → Issue has been addressed/resolved
4. **closed** → Post is closed (no further action needed)

## Usage Examples

### Citizen Updates Their Own Post
```javascript
// Author updating their own post status
fetch('/api/v1/posts/123/status', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ status: 'resolved' })
})
```

### Representative Updates Assigned Post
```javascript
// Representative updating status of post assigned to them
fetch('/api/v1/posts/456/status', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${repToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ status: 'in_progress' })
})
```

## Testing

A test script is provided at `backend/test_post_status_update.py` to validate the functionality:

```bash
cd backend
python test_post_status_update.py
```

This endpoint provides a secure and controlled way to update post statuses while maintaining proper authorization and data integrity.
