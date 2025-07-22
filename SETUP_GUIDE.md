# Setup Guide: Mixed Content API Enhancement

## Prerequisites

1. **NewsAPI Account**: Sign up at [newsapi.org](https://newsapi.org/)
2. **Backend Setup**: CivicPulse backend properly configured
3. **Database**: PostgreSQL with existing posts data

## Step 1: Get NewsAPI Key

1. Visit [newsapi.org](https://newsapi.org/)
2. Sign up for a free account
3. Navigate to your account dashboard
4. Copy your API key

## Step 2: Configure Environment Variables

Create or update your `.env` file in the backend directory:

```bash
# NewsAPI Configuration
NEWSAPI_KEY=your-actual-api-key-here
NEWSAPI_COUNTRY=in
POSTS_RATIO=0.4
MIN_POSTS_PER_PAGE=0
MAX_POSTS_PER_PAGE=20
```

### Configuration Options

- **NEWSAPI_KEY**: Your NewsAPI.org API key (required)
- **NEWSAPI_COUNTRY**: Country code for news (optional, default: "in")
- **POSTS_RATIO**: Ratio of posts vs news (optional, default: 0.4 = 40% posts)
- **MIN_POSTS_PER_PAGE**: Minimum posts per page (optional, default: 0)
- **MAX_POSTS_PER_PAGE**: Maximum posts per page (optional, default: 20)

## Step 3: Install Dependencies

Ensure httpx is installed (should already be in requirements.txt):

```bash
cd backend
pip install httpx==0.25.2
```

## Step 4: Test the Implementation

Run the test script to verify everything works:

```bash
cd backend
python test_mixed_content.py
```

Expected output:
```
=== CivicPulse Mixed Content Test ===
Testing News Service...
NewsAPI Key configured: Yes
Fetched 5 news articles

Sample news article:
Title: [News Article Title]
Source: news
Category: Technology
External URL: https://example.com/article

Testing Mixed Content Service...
Posts ratio: 0.4
Min posts per page: 0
Max posts per page: 20
Mixed content result:
- Total items: 10
- Page: 1
- Size: 10
- Has more: True
- Posts: 4
- News: 6

Sample items:
1. [post] User Post Title
2. [news] News Article Title
3. [post] Another User Post
=== Test Complete ===
```

## Step 5: Start the Backend

```bash
cd backend
python run.py
```

## Step 6: Test the API Endpoints

### Get Mixed Content (Default)
```bash
curl "http://localhost:8000/api/v1/posts?page=1&size=20"
```

### Get Only Posts
```bash
curl "http://localhost:8000/api/v1/posts/posts-only?page=1&size=20"
```

### Get Only News
```bash
curl "http://localhost:8000/api/v1/posts/news-only?page=1&size=20"
```

## Step 7: Verify Frontend Integration

1. Start the frontend development server
2. Navigate to the home page
3. You should see a mix of user posts and news articles
4. News articles will have:
   - "External" badge on images
   - "Read Full Article" button
   - Disabled voting/commenting
   - Source attribution

## Troubleshooting

### No News Articles Appearing

1. **Check API Key**: Ensure NEWSAPI_KEY is set correctly
2. **Check Logs**: Look for errors in backend logs
3. **Test News Service**: Run the test script
4. **Check Rate Limits**: NewsAPI has rate limits

### Only News, No Posts

1. **Check Database**: Ensure posts exist in your database
2. **Check Post Service**: Verify post_service.get_posts() works
3. **Adjust Ratio**: Increase POSTS_RATIO value

### Frontend Issues

1. **Check Types**: Ensure frontend types include `source` field
2. **Clear Cache**: Clear browser cache and restart frontend
3. **Check Console**: Look for TypeScript/JavaScript errors

## Rate Limits

NewsAPI free tier limits:
- **Developer**: 100 requests/day
- **Business**: 50,000 requests/month
- **Enterprise**: Custom limits

For production, consider:
- Implementing caching (Redis recommended)
- Upgrading NewsAPI plan
- Adding fallback content strategies

## Security Notes

1. **API Key Protection**: Never expose NewsAPI key in frontend code
2. **Environment Variables**: Use proper environment variable management
3. **Rate Limiting**: Implement API rate limiting for your endpoints
4. **Content Validation**: Validate and sanitize news content

## Next Steps

1. **Caching**: Implement Redis caching for news articles
2. **Personalization**: Add user preference-based news filtering
3. **Multiple Sources**: Integrate additional news APIs
4. **Analytics**: Track user engagement with mixed content
5. **Performance**: Optimize database queries and API calls
