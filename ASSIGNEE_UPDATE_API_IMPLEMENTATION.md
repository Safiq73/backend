# Post Update API Restrictions and Assignee Update Implementation

## Overview

This implementation adds proper restrictions to the post update API and creates a dedicated assignee update API with proper authorization controls.

## Changes Made

### 1. Restricted Post Update API

**File:** `backend/app/schemas/__init__.py`

- **Removed** `status` and `assignee` fields from `PostUpdate` schema
- Post update API can no longer modify status or assignee fields
- Only content-related fields can be updated via the general update API

```python
class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    post_type: Optional[PostType] = None
    location: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    tags: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None
```

### 2. New Assignee Update Schema

**File:** `backend/app/schemas/__init__.py`

- Added `PostAssigneeUpdate` schema for dedicated assignee updates

```python
class PostAssigneeUpdate(BaseModel):
    assignee: Optional[str] = Field(..., description="UUID of representative to assign to this post (null to unassign)")

    class Config:
        use_enum_values = True
```

### 3. Database Service Enhancement

**File:** `backend/app/services/db_service.py`

- Added `update_post_assignee()` method for database-level assignee updates

```python
async def update_post_assignee(self, post_id: UUID, assignee_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Update post assignee specifically"""
    async with db_manager.get_connection() as conn:
        query = """
            UPDATE posts 
            SET assignee = $1, updated_at = NOW(), last_activity_at = NOW()
            WHERE id = $2
            RETURNING id, user_id, assignee
        """
        
        # Convert assignee_id to UUID if provided, otherwise set to None
        assignee_uuid = UUID(assignee_id) if assignee_id else None
        
        row = await conn.fetchrow(query, assignee_uuid, post_id)
        if not row:
            return None
        
        # Get the full post with author info
        return await self.get_post_by_id(post_id)
```

### 4. Post Service Enhancement

**File:** `backend/app/services/post_service.py`

#### Added Assignee Update Method

```python
async def update_post_assignee(self, post_id: UUID, assignee_id: Optional[str], current_user_id: UUID) -> Dict[str, Any]:
    """Update post assignee with authorization checks"""
    # Get the post first to check authorization
    post = await self.db_service.get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if user is authorized to update assignee
    is_authorized = await self._check_post_assignee_authorization(post, current_user_id)
    if not is_authorized:
        raise HTTPException(
            status_code=403, 
            detail="Not authorized to update post assignee. Only post author or current assignee can update assignee."
        )
    
    # If assigning to someone, validate the representative exists
    if assignee_id:
        from app.services.representative_service import RepresentativeService
        rep_service = RepresentativeService()
        representative = await rep_service.get_representative_by_id(assignee_id)
        if not representative:
            raise HTTPException(status_code=400, detail="Invalid representative ID")
    
    # Update the post assignee
    updated_post = await self.db_service.update_post_assignee(post_id, assignee_id)
    if not updated_post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    response = await self._format_post_response(updated_post, current_user_id)
    
    action = "assigned" if assignee_id else "unassigned"
    logger.info(f"Updated post {post_id} assignee ({action}) by user {current_user_id}")
    return response
```

#### Added Authorization Check Method

```python
async def _check_post_assignee_authorization(self, post: Dict[str, Any], user_id: UUID) -> bool:
    """Check if user is authorized to update post assignee"""
    # Check if user is the post author
    post_author_id = post['author']['id']
    if isinstance(post_author_id, str):
        post_author_id = UUID(post_author_id)
    if post_author_id == user_id:
        return True
    
    # Check if user is the current assignee
    assignee_id = post.get('assignee')
    if assignee_id:
        # Get user's linked representative accounts
        from app.services.representative_service import RepresentativeService
        rep_service = RepresentativeService()
        user_rep_accounts = await rep_service.get_user_rep_accounts(user_id)
        
        # Check if any of user's representative accounts match the current assignee
        for rep_account in user_rep_accounts:
            if str(rep_account['id']) == str(assignee_id):
                return True
    
    return False
```

#### Fixed UUID Conversion Issues

- Fixed UUID handling in `_check_post_status_authorization`, `update_post`, and `delete_post` methods
- Added proper type checking before UUID conversion to handle both string and UUID objects

### 5. API Endpoint Addition

**File:** `backend/app/api/endpoints/posts.py`

- Added import for `PostAssigneeUpdate` schema
- Added new PATCH endpoint for assignee updates

```python
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
```

## API Usage

### Assignee Update API

**Endpoint:** `PATCH /api/v1/posts/{post_id}/assignee`

**Authorization:** Required (Bearer token)

**Request Body:**
```json
{
  "assignee": "representative-uuid-here"  // or null to unassign
}
```

**Response:**
```json
{
  "success": true,
  "message": "Post assignee assigned successfully",
  "data": {
    "post": {
      // Updated post object with new assignee
    }
  }
}
```

### Authorization Rules

1. **Post Author:** Can always update assignee (assign/unassign)
2. **Current Assignee:** Can update assignee (typically to unassign themselves or reassign)
3. **Other Users:** Cannot update assignee

### Restricted Fields in Post Update

The following fields are **no longer** available in the general post update API (`PUT /api/v1/posts/{post_id}`):

- `status` - Use `PATCH /api/v1/posts/{post_id}/status` instead
- `assignee` - Use `PATCH /api/v1/posts/{post_id}/assignee` instead

## Testing

Three test files were created to verify the implementation:

1. **`test_assignee_update.py`** - Tests database-level assignee update functionality
2. **`test_assignee_authorization.py`** - Tests authorization logic
3. **`test_assignee_api.py`** - Documents API structure

### Test Results

✅ **Database Updates:** Assignee can be set to null (unassign) or valid UUID (assign)  
✅ **Post Author Authorization:** Post authors can update assignee  
✅ **Access Control:** Random users are denied access  
✅ **API Structure:** Endpoint available with proper schema validation  

## Security Considerations

1. **Representative Validation:** When assigning, the system validates that the representative ID exists
2. **Authorization Checks:** Only authorized users (post author or current assignee) can update assignee
3. **Input Validation:** UUID format validation for assignee IDs
4. **Audit Logging:** All assignee updates are logged with user and action details

## Frontend Integration

The frontend will need to update the post update interface to:

1. Remove assignee selection from general post edit forms
2. Add dedicated assignee update components similar to status updates
3. Use the new `PATCH /api/v1/posts/{post_id}/assignee` endpoint
4. Handle authorization errors appropriately

### Example Frontend Usage

```typescript
// Update assignee
const updateAssignee = async (postId: string, assigneeId: string | null) => {
  const response = await fetch(`/api/v1/posts/${postId}/assignee`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      assignee: assigneeId
    })
  });
  
  if (!response.ok) {
    throw new Error('Failed to update assignee');
  }
  
  return response.json();
};
```

## Migration Notes

**Existing Code:** The general post update API (`PUT /api/v1/posts/{post_id}`) will continue to work but will ignore `status` and `assignee` fields if provided in the request body.

**No Database Changes:** No database migrations are required as this only changes API behavior and adds new endpoints.
