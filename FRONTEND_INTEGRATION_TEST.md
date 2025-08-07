# 🧪 Frontend Integration Test Script

## Quick Test to Verify Follow Status Integration

Run this test script to verify that your frontend is now using the integrated follow status API instead of making multiple calls.

### 1. Browser Console Test

Open your browser's DevTools console and run this script:

```javascript
// Test script to monitor API calls
let apiCallCounts = {
  posts: 0,
  followStatus: 0,
  total: 0
};

// Intercept fetch requests
const originalFetch = window.fetch;
window.fetch = function(...args) {
  const url = args[0];
  apiCallCounts.total++;
  
  if (url.includes('/posts')) {
    apiCallCounts.posts++;
    if (url.includes('include_follow_status=true')) {
      console.log('✅ CORRECT: Posts API called with follow status integration:', url);
    } else {
      console.log('⚠️  MISSING: Posts API called WITHOUT follow status integration:', url);
    }
  }
  
  if (url.includes('/follow-status')) {
    apiCallCounts.followStatus++;
    console.error('🚨 PROBLEM: Old follow status API called:', url);
    console.trace('Call stack:');
  }
  
  return originalFetch.apply(this, arguments);
};

console.log('🔍 Monitoring API calls...');
console.log('Expected: 1 posts API call with include_follow_status=true');
console.log('Expected: 0 individual follow-status API calls');

// Report function
window.reportAPIUsage = () => {
  console.log('\n📊 API Usage Report:');
  console.log(`Posts API calls: ${apiCallCounts.posts}`);
  console.log(`Follow Status API calls: ${apiCallCounts.followStatus}`);
  console.log(`Total API calls: ${apiCallCounts.total}`);
  
  if (apiCallCounts.followStatus === 0) {
    console.log('✅ SUCCESS: No individual follow status calls detected!');
  } else {
    console.log('❌ ISSUE: Found individual follow status calls - frontend needs more fixes');
  }
  
  return apiCallCounts;
};

console.log('Navigate to your posts page, then run: reportAPIUsage()');
```

### 2. Network Tab Verification

1. Open DevTools → Network tab
2. Filter by "follow-status"
3. Navigate to your posts page
4. **Expected Result**: ZERO requests to `/users/{id}/follow-status`

### 3. Posts API Verification

1. Open DevTools → Network tab
2. Filter by "posts"
3. Navigate to your posts page
4. Click on the posts API request
5. **Expected Result**: URL contains `include_follow_status=true`

### 4. Visual Verification

1. Load a posts page with authors you're not following
2. **Expected Result**: Follow buttons should appear without any loading delay
3. **Previous Behavior**: Follow buttons would show loading spinners while checking status

---

## 🔧 If Tests Fail

### Problem: Still seeing follow-status API calls
**Solution**: Check these files and ensure they're using the new pattern:

1. **Any custom post components** - Make sure they pass `initialFollowStatus={post.follow_status}`
2. **Any direct postsService.getPosts calls** - Add `include_follow_status: true`

### Problem: Follow buttons still loading
**Solution**: Ensure your FollowButton components receive `initialFollowStatus` prop

### Problem: API doesn't include follow status
**Solution**: Check that your API calls include the parameter:
```javascript
// ✅ Correct
fetch('/api/v1/posts?include_follow_status=true&page=1&size=10')

// ❌ Wrong  
fetch('/api/v1/posts?page=1&size=10')
```

---

## 📈 Performance Impact

**Before**: N+1 API calls
- 1 call to get posts
- N calls to get follow status for each author

**After**: 1 API call
- 1 call to get posts with follow status included

**Improvement**: ~90% reduction in API calls for feeds with mixed authors!

---

## 🎯 Success Criteria

- ✅ Posts API includes `include_follow_status=true`
- ✅ Zero calls to `/users/{id}/follow-status` 
- ✅ Follow buttons show immediately without loading
- ✅ Follow status works correctly (true/false/null)
- ✅ Network tab shows minimal API calls

Run the browser console test above to verify! 🚀
