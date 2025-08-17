# File Upload Implementation for CivicPulse Posts

This document describes the implementation of file upload support in the CivicPulse post creation API.

## Overview

The CivicPulse API now supports uploading image and video files as part of post creation. Files are uploaded to Amazon S3 and the URLs are stored in the `media_urls` field of the posts table.

## Features

- **Multi-file Upload**: Support for uploading multiple files per post
- **File Type Validation**: Accepts images (JPEG, PNG, GIF, WebP) and videos (MP4, WebM, OGG, AVI, MOV)
- **File Size Limits**: Configurable limits for images (10MB) and videos (100MB)
- **S3 Integration**: Files are uploaded to Amazon S3 with proper metadata
- **Fallback Support**: API continues to work even if S3 is unavailable
- **File Management**: Endpoints for adding/removing files from existing posts

## API Endpoints

### 1. Create Post with Files

**POST** `/api/v1/posts`

Upload files as `multipart/form-data` along with post data.

**Request Format:**
```
Content-Type: multipart/form-data

Fields:
- title: string (required, 1-500 chars)
- content: string (required, 1-10000 chars)
- post_type: string (required, one of: issue|announcement|news|accomplishment|discussion)
- assignee: string (required, UUID of representative)
- location: string (optional)
- latitude: float (optional, -90 to 90)
- longitude: float (optional, -180 to 180)
- files: array of files (optional, max 10 files)
```

**Example cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/posts" \
  -F "title=Road Repair Needed" \
  -F "content=The road on Main Street has several potholes that need urgent attention." \
  -F "post_type=issue" \
  -F "assignee=12345678-1234-1234-1234-123456789012" \
  -F "location=Main Street, New Delhi" \
  -F "latitude=28.6139" \
  -F "longitude=77.2090" \
  -F "files=@/path/to/image1.jpg" \
  -F "files=@/path/to/image2.jpg"
```

**Response:**
```json
{
  "success": true,
  "message": "Post created successfully",
  "data": {
    "post": {
      "id": "post-uuid",
      "title": "Road Repair Needed",
      "content": "The road on Main Street...",
      "media_urls": [
        "https://bucket.s3.region.amazonaws.com/posts/post-uuid/file1.jpg",
        "https://bucket.s3.region.amazonaws.com/posts/post-uuid/file2.jpg"
      ],
      ...
    },
    "uploaded_files": 2,
    "media_urls": [
      "https://bucket.s3.region.amazonaws.com/posts/post-uuid/file1.jpg",
      "https://bucket.s3.region.amazonaws.com/posts/post-uuid/file2.jpg"
    ]
  }
}
```

### 2. Upload Files to Existing Post

**POST** `/api/v1/posts/{post_id}/upload`

Add additional files to an existing post.

**Request:**
```
Content-Type: multipart/form-data

Fields:
- files: array of files (required)
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully uploaded 2 files",
  "data": {
    "post": { ... },
    "new_media_urls": [
      "https://bucket.s3.region.amazonaws.com/posts/post-uuid/file3.jpg"
    ],
    "total_media_count": 3
  }
}
```

### 3. Delete Media from Post

**DELETE** `/api/v1/posts/{post_id}/media?media_url={url}`

Remove a specific media file from a post.

**Response:**
```json
{
  "success": true,
  "message": "Media file deleted successfully",
  "data": {
    "post": { ... },
    "deleted_media_url": "https://bucket.s3.region.amazonaws.com/...",
    "remaining_media_count": 2
  }
}
```

### 4. Get Upload Configuration

**GET** `/api/v1/posts/upload-info`

Get current upload limits and configuration.

**Response:**
```json
{
  "success": true,
  "message": "Upload configuration retrieved",
  "data": {
    "s3_available": true,
    "max_files_per_post": 10,
    "max_file_size": 10485760,
    "max_image_size": 10485760,
    "max_video_size": 104857600,
    "allowed_file_types": ["image/jpeg", "image/png", "image/gif", "video/mp4"],
    "allowed_image_types": ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"],
    "allowed_video_types": ["video/mp4", "video/webm", "video/ogg", "video/avi", "video/mov"]
  }
}
```

## Environment Configuration

Add these environment variables to your `.env` file:

```env
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1
AWS_S3_ENDPOINT_URL=  # Optional: for local development with MinIO

# File Upload Limits
MAX_FILES_PER_POST=10
MAX_FILE_SIZE=10485760  # 10MB
S3_MAX_IMAGE_SIZE=10485760  # 10MB
S3_MAX_VIDEO_SIZE=104857600  # 100MB
```

## File Validation

The API validates files based on:

1. **File Type**: Only allows specific MIME types
   - Images: JPEG, PNG, GIF, WebP
   - Videos: MP4, WebM, OGG, AVI, MOV

2. **File Size**: 
   - Images: Maximum 10MB (configurable)
   - Videos: Maximum 100MB (configurable)

3. **File Count**: Maximum 10 files per post (configurable)

4. **File Content**: Files must have actual content (size > 0)

## S3 Configuration

### Bucket Setup

1. Create an S3 bucket in your AWS account
2. Configure bucket permissions for your application
3. Set up CORS if needed for direct browser uploads

### File Organization

Files are stored with the following structure:
```
bucket-name/
├── posts/
│   ├── {post-id}/
│   │   ├── {uuid}.jpg
│   │   ├── {uuid}.mp4
│   │   └── ...
│   └── ...
└── uploads/
    ├── {uuid}.jpg  # Files uploaded before post creation
    └── ...
```

### File Metadata

Each uploaded file includes:
- `ContentType`: Proper MIME type
- `CacheControl`: Set to 1 year for better performance
- `ContentDisposition`: Set to "inline" for direct viewing

## Error Handling

The API handles various error scenarios:

1. **S3 Unavailable**: Posts are created without files, operation continues
2. **File Upload Failures**: Logs errors but doesn't fail the entire operation
3. **Invalid Files**: Returns 400 with specific validation errors
4. **Size Limits**: Returns 400 with clear error messages
5. **Authorization**: Returns 403 for unauthorized file operations

## Database Schema

The `posts` table includes a `media_urls` field:

```sql
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    media_urls TEXT[], -- Array of S3 URLs
    -- ... other fields
);
```

## Testing

Use the provided test script to verify the implementation:

```bash
python backend/test_file_upload_api.py
```

The test script covers:
- Upload configuration endpoint
- Post creation with files
- Post creation without files
- File validation scenarios

## Security Considerations

1. **File Type Validation**: MIME type checking prevents malicious files
2. **Size Limits**: Prevent DoS attacks via large file uploads
3. **Authorization**: Only post owners can modify post files
4. **S3 Security**: Use IAM roles and bucket policies for secure access
5. **URL Access**: Consider using signed URLs for sensitive content

## Performance Optimization

1. **Async Uploads**: All S3 operations are asynchronous
2. **Parallel Processing**: Multiple files are uploaded concurrently
3. **Caching**: S3 files include cache headers for better performance
4. **Error Recovery**: Failed uploads don't block post creation

## Development vs Production

### Development Mode
- S3 service can be disabled for local development
- Mock S3 service provides static URLs for testing
- Files are validated but not actually uploaded

### Production Mode
- Requires valid AWS credentials and S3 bucket
- All files are uploaded to S3
- Proper error handling and monitoring

## Future Enhancements

Potential improvements:
1. **Image Processing**: Automatic resizing and optimization
2. **CDN Integration**: CloudFront distribution for better performance
3. **Virus Scanning**: Integrate with AWS GuardDuty or similar
4. **Progress Tracking**: Upload progress for large files
5. **Batch Operations**: Bulk file management operations
