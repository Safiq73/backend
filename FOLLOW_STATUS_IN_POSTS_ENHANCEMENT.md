# Follow Status in Posts API Enhancement

## Overview

This enhancement adds an optional `include_follow_status` parameter to the posts API endpoints that allows clients to fetch follow status information for post authors directly within the posts response, eliminating the need for multiple API calls.

## Problem Solved

Previously, to display follow status for post authors, clients had to:
1. Fetch posts from `/api/v1/posts`
2. For each post, make a separate call to `/api/v1/users/{author_id}/follow-status`

This resulted in N+1 API calls (1 for posts + N for each author's follow status), which is inefficient and increases network overhead.

## Solution

Added an optional `include_follow_status` boolean parameter to the posts endpoints. When set to `true`, each post object in the response will include a `follow_status` field indicating whether the current authenticated user follows the post author.

## API Changes

### Modified Endpoints

#### 1. GET /api/v1/posts
**New Parameter:**
- `include_follow_status` (optional, boolean, default: false) - Include follow status for post authors

**Example Request:**
```bash
GET /api/v1/posts?page=1&size=10&include_follow_status=true
Authorization: Bearer <jwt_token>
```

**Enhanced Response:**
```json
{
  "items": [
    {
      "id": "post-uuid",
      "title": "Sample Post",
      "content": "Post content...",
      "author": {
        "id": "author-uuid",
        "username": "john_doe",
        "display_name": "John Doe"
      },
      "follow_status": true,  // NEW FIELD
      "upvotes": 15,
      "downvotes": 2,
      // ... other post fields
    }
  ],
  "total": 50,
  "page": 1,
  "size": 10,
  "has_more": true
}
```

#### 2. GET /api/v1/posts/posts-only
**New Parameter:**
- `include_follow_status` (optional, boolean, default: false) - Include follow status for post authors

**Usage:** Same as above

## Follow Status Values

The `follow_status` field can have the following values:

| Value | Description |
|-------|-------------|
| `true` | Current user follows the post author |
| `false` | Current user does not follow the post author |
| `null` | Current user is the post author OR user is not authenticated |

## Implementation Details

### Backend Changes

1. **API Endpoints** (`app/api/endpoints/posts.py`):
   - Added `include_follow_status` parameter to both `/posts` and `/posts/posts-only` endpoints
   - Parameter passed through to service layer

2. **Post Service** (`app/services/post_service.py`):
   - Updated `get_posts()` method to accept `include_follow_status` parameter
   - Modified `_format_post_response()` to conditionally include follow status
   - Added follow status checking logic using existing `FollowService`

3. **Mixed Content Service** (`app/services/mixed_content_service.py`):
   - Updated `get_mixed_content()` method to support and pass through the new parameter

### Follow Status Logic

The follow status is determined as follows:

```python
# Only check follow status if requested and user is authenticated
if include_follow_status and current_user_id:
    # Get the author ID from the post
    author_id = post['author']['id']
    
    # Only check if current user is not the author
    if author_id != current_user_id:
        follow_data = await follow_service.check_follow_status(current_user_id, author_id)
        follow_status = follow_data.get('is_following', False)
    else:
        # User is viewing their own post
        follow_status = None
```

### Error Handling

- If follow status checking fails, it logs the error but doesn't fail the entire request
- The `follow_status` field will be `null` if checking fails
- Backward compatibility is maintained - existing API calls work unchanged

## Usage Examples

### Frontend Implementation

#### Before (Multiple API Calls)
```javascript
// 1. Fetch posts
const postsResponse = await fetch('/api/v1/posts?page=1&size=10');
const posts = await postsResponse.json();

// 2. For each post, fetch follow status (N additional calls)
for (const post of posts.items) {
  const followResponse = await fetch(`/api/v1/users/${post.author.id}/follow-status`);
  const followData = await followResponse.json();
  post.isFollowing = followData.is_following;
}
```

#### After (Single API Call)
```javascript
// Single API call with follow status included
const response = await fetch('/api/v1/posts?page=1&size=10&include_follow_status=true');
const posts = await response.json();

// Follow status is already available in each post
posts.items.forEach(post => {
  if (post.follow_status === true) {
    // User follows this author
  } else if (post.follow_status === false) {
    // User doesn't follow this author
  } else {
    // User is the author or not authenticated
  }
});
```

### React Component Example

```typescript
interface PostWithFollowStatus {
  id: string;
  title: string;
  author: {
    id: string;
    username: string;
    display_name: string;
  };
  follow_status: boolean | null;
  // ... other fields
}

const PostsList: React.FC = () => {
  const [posts, setPosts] = useState<PostWithFollowStatus[]>([]);

  useEffect(() => {
    const fetchPosts = async () => {
      const response = await fetch('/api/v1/posts?include_follow_status=true');
      const data = await response.json();
      setPosts(data.items);
    };
    
    fetchPosts();
  }, []);

  return (
    <div>
      {posts.map(post => (
        <div key={post.id}>
          <h3>{post.title}</h3>
          <div>
            By {post.author.display_name}
            {post.follow_status === true && <span>• Following</span>}
            {post.follow_status === false && (
              <button onClick={() => followUser(post.author.id)}>
                Follow
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
```

## Performance Considerations

### Benefits
- **Reduced API Calls**: From N+1 to 1 API call
- **Lower Network Overhead**: Single request instead of multiple
- **Better User Experience**: Faster loading, less API rate limiting

### Overhead
- **Database Queries**: Additional follow status checks per post
- **Response Size**: Slightly larger response payload
- **Processing Time**: Minimal increase due to follow status lookups

### Recommendations
- Only use `include_follow_status=true` when you actually need follow status
- Consider caching follow relationships for better performance
- Use pagination to limit the number of posts processed

## Backward Compatibility

✅ **Fully Backward Compatible**
- Existing API calls work unchanged
- New parameter is optional with default value `false`
- Response structure unchanged when parameter not used
- No breaking changes to existing functionality

## Testing

A test script is provided at `backend/test_follow_status_in_posts.py` to validate the functionality:

```bash
cd backend
python3 test_follow_status_in_posts.py
```

### Test Cases Covered
1. Posts without follow status (original behavior)
2. Posts with follow status enabled (authenticated user)
3. Posts-only endpoint with follow status
4. Unauthenticated requests (should return null follow status)

## Security Considerations

- Follow status is only returned for authenticated users
- Users cannot see follow status when not logged in
- Users' own posts return `null` follow status (privacy)
- Existing authorization and permission checks remain unchanged

## Future Enhancements

Potential future improvements:
1. Batch follow status checking for better performance
2. Caching layer for frequently accessed follow relationships
3. Include mutual follow status (`is_mutual`)
4. Support for follow status in other endpoints (comments, etc.)

---

## Summary

This enhancement provides a more efficient way to fetch follow status alongside posts, reducing API calls from N+1 to 1 while maintaining full backward compatibility and proper error handling.
