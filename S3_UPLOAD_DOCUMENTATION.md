# S3 Media Upload Implementation for CivicPulse

This implementation adds robust file upload functionality to the CivicPulse post creation API, supporting both images and videos uploaded to Amazon S3.

## 🎯 Features Implemented

### Core Functionality
- ✅ **Multipart/form-data support** for file uploads during post creation
- ✅ **AWS S3 integration** with boto3 SDK
- ✅ **File type validation** (images: JPEG, PNG, GIF, WebP; videos: MP4, WebM, OGG, AVI, MOV)
- ✅ **File size limits** (images: 10MB, videos: 100MB)
- ✅ **Multiple file upload** support (max 10 files per post)
- ✅ **Public URL generation** for uploaded files
- ✅ **Error handling** with proper HTTP status codes
- ✅ **Environment-based configuration** for S3 credentials

### Security & Validation
- ✅ **MIME type validation** to prevent malicious file uploads
- ✅ **File size enforcement** to prevent abuse
- ✅ **Unique file naming** using UUIDs to prevent conflicts
- ✅ **Organized storage** with folder structure: `posts/{post_id}/{unique_id}.{ext}`

## 📡 API Endpoints

### New Endpoint: Create Post with Media
```
POST /api/v1/posts/with-media
Content-Type: multipart/form-data
```

**Form Fields:**
- `title` (required): Post title (1-500 chars)
- `content` (required): Post content (1-10000 chars) 
- `post_type` (required): One of: issue, announcement, news, accomplishment, discussion
- `assignee` (optional): Representative UUID
- `location` (optional): Location description
- `latitude` (optional): Latitude (-90 to 90)
- `longitude` (optional): Longitude (-180 to 180)
- `tags` (optional): JSON string of tags array
- `files` (optional): Array of files to upload

**Example Response:**
```json
{
  "success": true,
  "message": "Post created successfully with 2 media files",
  "data": {
    "post": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "title": "Road Repair Needed",
      "content": "There's a pothole on Main Street",
      "media_urls": [
        "https://bucket.s3.region.amazonaws.com/posts/123.../image1.jpg",
        "https://bucket.s3.region.amazonaws.com/posts/123.../video1.mp4"
      ],
      // ... other post fields
    },
    "uploaded_media_urls": [
      "https://bucket.s3.region.amazonaws.com/posts/123.../image1.jpg",
      "https://bucket.s3.region.amazonaws.com/posts/123.../video1.mp4"
    ]
  }
}
```

### Existing Endpoint: Create Post (JSON)
```
POST /api/v1/posts
Content-Type: application/json
```
This endpoint remains unchanged for creating posts without file uploads or with pre-existing media URLs.

## ⚙️ Configuration

### Environment Variables
Add these to your `.env` file:

```bash
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1

# Optional: For local development with MinIO/LocalStack
AWS_S3_ENDPOINT_URL=http://localhost:9000

# File Upload Limits (optional)
S3_MAX_IMAGE_SIZE=10485760  # 10MB
S3_MAX_VIDEO_SIZE=104857600  # 100MB
MAX_FILES_PER_POST=10
```

### S3 Bucket Configuration
1. Create an S3 bucket in AWS
2. Configure bucket permissions for public read access:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    }
  ]
}
```
3. Set up CORS policy if accessing from web frontend:
```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "POST", "PUT"],
    "AllowedOrigins": ["*"],
    "ExposeHeaders": []
  }
]
```

## 🏗️ Architecture

### Files Created/Modified

1. **`app/services/s3_upload_service.py`** (NEW)
   - Main S3 upload service with file validation
   - Handles single and multiple file uploads
   - Manages file deletion and presigned URLs
   - Error handling and logging

2. **`app/api/endpoints/posts.py`** (MODIFIED)
   - Added new `/with-media` endpoint
   - Imports S3 upload service
   - Form data validation and processing

3. **`app/core/config.py`** (MODIFIED)
   - Added S3 configuration settings
   - File size limits configuration

4. **`requirements.txt`** (MODIFIED)
   - Added boto3 and botocore dependencies

### Service Integration

```python
# S3 Service Usage Example
from app.services.s3_upload_service import s3_upload_service

# Upload single file
url = await s3_upload_service.upload_file(file, post_id="optional")

# Upload multiple files
urls = await s3_upload_service.upload_multiple_files(files, post_id="optional")

# Check if service is available
if s3_upload_service.is_available():
    # Proceed with upload
    pass
```

## 🧪 Testing

### Manual Testing with curl
```bash
# Test with image upload
curl -X POST http://localhost:8000/api/v1/posts/with-media \
  -F "title=Test Post" \
  -F "content=Testing image upload" \
  -F "post_type=issue" \
  -F "files=@test_image.jpg" \
  -F "files=@test_video.mp4"
```

### Frontend Integration Example
```javascript
// Frontend form submission example
const formData = new FormData();
formData.append('title', 'My Post Title');
formData.append('content', 'Post content here');
formData.append('post_type', 'issue');
formData.append('tags', JSON.stringify(['tag1', 'tag2']));

// Add files
files.forEach(file => {
    formData.append('files', file);
});

const response = await fetch('/api/v1/posts/with-media', {
    method: 'POST',
    body: formData,
    headers: {
        'Authorization': `Bearer ${token}`
    }
});
```

## 🔧 Error Handling

The implementation includes comprehensive error handling:

### File Validation Errors (400)
- Invalid file type
- File too large
- No file provided
- Too many files (>10)

### Service Errors (503)
- S3 service unavailable
- Missing AWS credentials
- Bucket not accessible

### Upload Errors (500)
- S3 upload failures
- Network connectivity issues
- Unexpected server errors

## 🚀 Deployment Considerations

### Production Setup
1. **IAM Permissions**: Create dedicated IAM user with S3 upload permissions
2. **Bucket Security**: Configure proper bucket policies and ACLs
3. **CDN**: Consider CloudFront for faster media delivery
4. **Monitoring**: Set up CloudWatch metrics for upload monitoring
5. **Backup**: Configure S3 versioning and backup policies

### Performance Optimization
- Files are uploaded with `CacheControl: max-age=31536000` (1 year)
- Public ACL for direct browser access
- Unique file paths prevent naming conflicts
- Organized folder structure for easy management

### Fallback Strategy
If S3 is unavailable, the service gracefully handles it:
- Returns HTTP 503 with clear error message
- Logs the issue for monitoring
- Doesn't crash the application

## 📝 Usage Notes

1. **Backward Compatibility**: The original `/posts` endpoint remains unchanged
2. **Database Storage**: Media URLs are stored in the `media_urls` TEXT[] field
3. **File Organization**: Files are organized by post ID for easy management
4. **Public Access**: Uploaded files are publicly accessible via direct URLs
5. **Cleanup**: Consider implementing a cleanup job for orphaned files

## 🔮 Future Enhancements

Potential improvements for future iterations:
- Image resizing and thumbnail generation
- Video transcoding for different formats
- Virus scanning integration
- Upload progress tracking
- Batch upload optimization
- Integration with CDN for global distribution
- Automatic file cleanup for deleted posts
