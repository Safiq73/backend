# Mixed Content API Enhancement

This document describes the enhanced GET `/api/v1/posts` endpoint that now returns a mix of user-generated posts and external news articles.

## Overview

The enhanced endpoint provides a seamless experience by mixing user-generated civic posts with relevant news articles from external sources (NewsAPI). This creates a more engaging feed that combines local civic issues with broader news context.

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# NewsAPI Configuration
NEWSAPI_KEY=your-newsapi-key-here
NEWSAPI_COUNTRY=in
POSTS_RATIO=0.4
MIN_POSTS_PER_PAGE=0
MAX_POSTS_PER_PAGE=20
```

### Configuration Options

- **NEWSAPI_KEY**: Your NewsAPI.org API key (required for news functionality)
- **NEWSAPI_COUNTRY**: Country code for news (default: "in" for India)
- **POSTS_RATIO**: Ratio of posts vs news (0.4 = 40% posts, 60% news)
- **MIN_POSTS_PER_PAGE**: Minimum number of posts per page
- **MAX_POSTS_PER_PAGE**: Maximum number of posts per page

## API Endpoints

### GET `/api/v1/posts` (Enhanced)

**Description**: Returns mixed content (posts + news) with configurable ratios.

**Parameters**:
- `page`: Page number (default: 1)
- `size`: Items per page (default: 10, max: 100)
- `post_type`: Filter posts by type
- `area`: Filter by area/location
- `category`: Filter by category
- `sort_by`: Sort field (default: "timestamp")
- `order`: Sort order (default: "desc")

**Response Format**:
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Post Title",
      "content": "Post content",
      "source": "post",
      "post_type": "issue",
      "author": {
        "id": "uuid",
        "username": "user",
        "display_name": "User Name"
      },
      "upvotes": 5,
      "downvotes": 1,
      "created_at": "2024-01-01T00:00:00Z"
    },
    {
      "id": "news_123",
      "title": "News Article Title",
      "content": "News content with source link",
      "source": "news",
      "post_type": "news",
      "external_url": "https://example.com/article",
      "source_name": "News Source",
      "author": {
        "id": "newsapi",
        "username": "newsapi",
        "display_name": "News Source"
      },
      "upvotes": 25,
      "downvotes": 2,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "size": 20,
  "has_more": true
}
```

### GET `/api/v1/posts/posts-only`

**Description**: Returns only user-generated posts (no news).

**Parameters**: Same as main endpoint.

### GET `/api/v1/posts/news-only`

**Description**: Returns only news articles (no user posts).

**Parameters**:
- `page`: Page number
- `size`: Items per page
- `category`: News category filter
- `country`: Country code (default: "in")

## Content Distribution Logic

### Ratio-Based Distribution

1. **Calculate Post Allocation**: `max_posts = floor(size * posts_ratio)`
2. **Apply Constraints**: Ensure within min/max bounds
3. **Calculate News Allocation**: `max_news = size - max_posts`

### Dynamic Compensation

- If fewer posts are available than allocated, fill remaining slots with news
- If no posts are available for a page, return only news articles
- News articles are fetched to fill the exact remaining count

### Example Distributions

With default settings (`posts_ratio = 0.4`, `size = 20`):

| Scenario | Posts Available | Posts Returned | News Returned | Total |
|----------|----------------|---------------|--------------|-------|
| Normal | 8+ | 8 | 12 | 20 |
| Limited Posts | 4 | 4 | 16 | 20 |
| No Posts | 0 | 0 | 20 | 20 |

## Content Identification

Each item in the response includes a `source` field:

- **`"post"`**: User-generated civic post
- **`"news"`**: External news article

Additional fields for news articles:
- `external_url`: Link to original article
- `source_name`: Name of news publication

## Pagination

### Mixed Content Pagination

- Posts and news are paginated independently
- Post pagination: Standard database pagination
- News pagination: Distributed across pages to ensure variety

### Efficiency Optimizations

1. **Skip Empty Post Pages**: If no posts exist for a page range, skip the database query
2. **News Page Distribution**: Spread news across multiple NewsAPI pages to avoid repetition
3. **Quick Post Check**: Use lightweight query to check post availability before full fetch

## Frontend Integration

### Updated Types

```typescript
export interface CivicPost {
  // ... existing fields
  source?: 'post' | 'news'
  external_url?: string
  source_name?: string
}
```

### Handling Mixed Content

```typescript
// Check if item is a news article
const isNews = post.source === 'news'

// Display external link for news
if (isNews && post.external_url) {
  // Show "Read Full Article" button
}

// Show source attribution for news
if (isNews && post.source_name) {
  // Display "Source: {source_name}"
}
```

## Error Handling

### NewsAPI Failures

- If NewsAPI is unavailable, the endpoint returns only posts
- Network errors are logged and don't break the main functionality
- Invalid API keys result in news-free responses

### Database Failures

- If post database is unavailable, the endpoint returns only news
- Graceful degradation ensures some content is always available

## Performance Considerations

### Caching

- Consider implementing Redis caching for news articles
- Cache duration: 15-30 minutes for news content
- Posts remain real-time from database

### Rate Limits

- NewsAPI has rate limits (varies by plan)
- Implement exponential backoff for API failures
- Consider news prefetching for high-traffic periods

## Testing

Run the test script to verify functionality:

```bash
cd backend
python test_mixed_content.py
```

This will test:
- NewsAPI connectivity
- Mixed content distribution
- Configuration settings

## Security Considerations

1. **API Key Protection**: Store NewsAPI key securely in environment variables
2. **Content Validation**: News content is sanitized and validated
3. **Rate Limiting**: Consider rate limiting the mixed content endpoint
4. **Content Filtering**: Inappropriate news content should be filtered (future enhancement)

## Future Enhancements

1. **Content Personalization**: Use user preferences to select relevant news
2. **Advanced Filtering**: Filter news by keywords, sentiment, or relevance
3. **Multiple News Sources**: Integrate additional news APIs
4. **Content Caching**: Implement Redis caching for better performance
5. **Real-time Updates**: WebSocket integration for live content updates
