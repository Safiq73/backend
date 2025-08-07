# Integrated Follow Status API Usage Guide

## Overview

The follow status functionality has been **fully integrated** into the posts API endpoints, eliminating the need for separate follow status API calls. This provides a more efficient and streamlined way to get posts with follow status information.

## 🚀 Updated API Endpoints with Follow Status

### 1. GET /api/v1/posts
**Mixed content (posts + news) with follow status**

```bash
# Get posts with follow status included
GET /api/v1/posts?include_follow_status=true&page=1&size=10
Authorization: Bearer <jwt_token>
```

### 2. GET /api/v1/posts/posts-only
**User posts only with follow status**

```bash
# Get user posts with follow status included
GET /api/v1/posts/posts-only?include_follow_status=true&page=1&size=10
Authorization: Bearer <jwt_token>
```

### 3. GET /api/v1/posts/{post_id}
**Individual post with follow status**

```bash
# Get specific post with follow status included
GET /api/v1/posts/123e4567-e89b-12d3-a456-426614174000?include_follow_status=true
Authorization: Bearer <jwt_token>
```

### 4. GET /api/v1/posts/nearby
**Nearby posts with follow status**

```bash
# Get nearby posts with follow status included
GET /api/v1/posts/nearby?latitude=19.0760&longitude=72.8777&include_follow_status=true
Authorization: Bearer <jwt_token>
```

## 📝 Response Format

When `include_follow_status=true`, each post includes the `follow_status` field:

```json
{
  "success": true,
  "message": "Posts retrieved successfully",
  "data": {
    "items": [
      {
        "id": "post-uuid",
        "title": "Road repair needed on Main Street",
        "content": "The road has multiple potholes...",
        "author": {
          "id": "author-uuid",
          "username": "john_doe", 
          "display_name": "John Doe"
        },
        "follow_status": true,  // ← NEW INTEGRATED FIELD
        "upvotes": 15,
        "downvotes": 2,
        "created_at": "2025-01-15T10:30:00Z"
        // ... other post fields
      }
    ],
    "total": 50,
    "page": 1,
    "size": 10
  }
}
```

## 🔄 Migration from Old Follow Status API

### ❌ Old Way (Multiple API Calls)
```javascript
// 1. Get posts
const postsResponse = await fetch('/api/v1/posts?page=1&size=10');
const postsData = await postsResponse.json();

// 2. For each post, get follow status (N additional API calls!)
for (const post of postsData.items) {
  const followResponse = await fetch(`/api/v1/users/${post.author.id}/follow-status`);
  const followData = await followResponse.json();
  post.isFollowing = followData.is_following;
}
```

### ✅ New Way (Single API Call)
```javascript
// Get posts with follow status in one efficient call
const response = await fetch('/api/v1/posts?include_follow_status=true&page=1&size=10');
const postsData = await response.json();

// Follow status is already available in each post!
postsData.items.forEach(post => {
  console.log(`Follow status for ${post.author.display_name}: ${post.follow_status}`);
});
```

## 🎯 Follow Status Values

| Value | Description | Use Case |
|-------|-------------|----------|
| `true` | Current user follows the post author | Show "Following" badge, hide "Follow" button |
| `false` | Current user doesn't follow the post author | Show "Follow" button |
| `null` | Current user is the author OR not authenticated | Don't show follow controls |

## 💡 Frontend Implementation Examples

### React Component with Integrated Follow Status

```typescript
interface Post {
  id: string;
  title: string;
  content: string;
  author: {
    id: string;
    username: string;
    display_name: string;
  };
  follow_status: boolean | null;
  upvotes: number;
  downvotes: number;
}

const PostsList: React.FC = () => {
  const [posts, setPosts] = useState<Post[]>([]);

  const fetchPosts = async () => {
    try {
      const response = await fetch('/api/v1/posts?include_follow_status=true&page=1&size=10', {
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      });
      const data = await response.json();
      setPosts(data.items);
    } catch (error) {
      console.error('Failed to fetch posts:', error);
    }
  };

  const handleFollow = async (authorId: string) => {
    try {
      await fetch(`/api/v1/users/${authorId}/follow`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      });
      
      // Refresh posts to get updated follow status
      fetchPosts();
    } catch (error) {
      console.error('Failed to follow user:', error);
    }
  };

  return (
    <div className="posts-list">
      {posts.map(post => (
        <div key={post.id} className="post-card">
          <h3>{post.title}</h3>
          <div className="post-author">
            <span>By {post.author.display_name}</span>
            
            {/* Follow Status Integration */}
            {post.follow_status === true && (
              <span className="following-badge">Following</span>
            )}
            
            {post.follow_status === false && (
              <button 
                onClick={() => handleFollow(post.author.id)}
                className="follow-btn"
              >
                Follow
              </button>
            )}
            
            {/* No follow controls if post.follow_status === null */}
          </div>
          
          <p>{post.content}</p>
          <div className="post-stats">
            <span>👍 {post.upvotes}</span>
            <span>👎 {post.downvotes}</span>
          </div>
        </div>
      ))}
    </div>
  );
};
```

### Vue.js Example

```vue
<template>
  <div class="posts-container">
    <div v-for="post in posts" :key="post.id" class="post-item">
      <h3>{{ post.title }}</h3>
      <div class="author-info">
        <span>{{ post.author.display_name }}</span>
        
        <!-- Follow Status Integration -->
        <span v-if="post.follow_status === true" class="following">
          ✓ Following
        </span>
        
        <button 
          v-else-if="post.follow_status === false"
          @click="followUser(post.author.id)"
          class="follow-btn"
        >
          Follow
        </button>
      </div>
      
      <p>{{ post.content }}</p>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      posts: []
    };
  },
  
  async mounted() {
    await this.fetchPosts();
  },
  
  methods: {
    async fetchPosts() {
      try {
        const response = await fetch('/api/v1/posts?include_follow_status=true', {
          headers: {
            'Authorization': `Bearer ${this.authToken}`
          }
        });
        const data = await response.json();
        this.posts = data.items;
      } catch (error) {
        console.error('Failed to fetch posts:', error);
      }
    },
    
    async followUser(authorId) {
      try {
        await fetch(`/api/v1/users/${authorId}/follow`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.authToken}`
          }
        });
        
        // Refresh posts to get updated follow status
        await this.fetchPosts();
      } catch (error) {
        console.error('Failed to follow user:', error);
      }
    }
  }
};
</script>
```

## ⚡ Performance Benefits

### Before Integration:
- **API Calls**: 1 + N (where N = number of posts)
- **Network Requests**: Multiple round trips
- **Loading Time**: Slower due to sequential requests
- **Rate Limiting**: Higher chance of hitting limits

### After Integration:
- **API Calls**: 1 (single request)
- **Network Requests**: Single round trip
- **Loading Time**: Faster, better UX
- **Rate Limiting**: Significantly reduced API usage

### Performance Comparison

```javascript
// Example with 10 posts

// OLD WAY: 11 API calls (1 + 10)
const startTime = Date.now();
const posts = await fetchPosts();           // 1 call
for (const post of posts) {
  await getFollowStatus(post.author.id);    // 10 more calls
}
const endTime = Date.now();
console.log(`Time: ${endTime - startTime}ms`); // ~2000ms

// NEW WAY: 1 API call
const startTime = Date.now();
const postsWithFollowStatus = await fetchPostsWithFollowStatus(); // 1 call
const endTime = Date.now();
console.log(`Time: ${endTime - startTime}ms`); // ~200ms
```

## 🛠️ Backend Integration Details

The follow status is now seamlessly integrated at the service layer:

```python
# Backend automatically handles follow status when requested
async def get_posts(
    self,
    skip: int = 0,
    limit: int = 20,
    include_follow_status: bool = False,  # New parameter
    current_user_id: Optional[UUID] = None
) -> List[Dict[str, Any]]:
    
    # Get posts from database
    posts = await self.db_service.get_posts(...)
    
    # Format each post with optional follow status
    responses = []
    for post in posts:
        response = await self._format_post_response(
            post, 
            current_user_id, 
            include_follow_status  # Passed through
        )
        responses.append(response)
    
    return responses
```

## 🔒 Security & Privacy

- ✅ Follow status only returned for authenticated users
- ✅ Users can't see follow status when not logged in
- ✅ Users' own posts return `null` follow status (privacy)
- ✅ All existing authorization checks remain in place
- ✅ No new security vulnerabilities introduced

## 📊 Usage Analytics

Track the adoption of the new integrated API:

```javascript
// Track API usage
const trackApiUsage = (endpoint, hasFollowStatus) => {
  analytics.track('API_Usage', {
    endpoint,
    include_follow_status: hasFollowStatus,
    timestamp: new Date()
  });
};

// When fetching posts
const response = await fetch('/api/v1/posts?include_follow_status=true');
trackApiUsage('/posts', true);
```

## 🚀 Next Steps

1. **Update your frontend code** to use `include_follow_status=true`
2. **Remove old follow status API calls** to reduce network overhead
3. **Test the integration** with your existing UI components
4. **Monitor performance improvements** in your analytics
5. **Consider deprecating** the standalone follow status endpoint

---

## Summary

The integrated follow status API provides:
- 🎯 **Single API call** instead of N+1 calls
- ⚡ **Better performance** and user experience  
- 🔄 **Full backward compatibility**
- 🔒 **Maintained security** and privacy
- 💻 **Easier frontend implementation**

This enhancement eliminates the need for multiple API calls while maintaining all existing functionality!
