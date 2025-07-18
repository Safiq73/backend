# CivicPulse API Documentation

## Security & Best Practices

### 1. Authentication & Authorization
- **JWT Tokens**: All protected endpoints require valid JWT tokens
- **Token Refresh**: Automatic token refresh on expiration
- **Token Blacklisting**: Revoked tokens are stored in blacklist
- **Role-Based Access**: Different permissions for citizens and representatives

### 2. Input Validation & Sanitization
- **Schema Validation**: Pydantic models validate all input data
- **XSS Prevention**: HTML tags and scripts are sanitized
- **SQL Injection Prevention**: Parameterized queries only
- **Length Limits**: All text fields have maximum length constraints

### 3. Rate Limiting
- **Per-Minute Limits**: 60 requests per minute per IP
- **Per-Hour Limits**: 1000 requests per hour per IP
- **Automatic Blocking**: Temporary blocks for exceeded limits
- **Health Check Exemption**: Health endpoints bypass rate limits

### 4. Security Headers
- **X-Content-Type-Options**: Prevents MIME type sniffing
- **X-Frame-Options**: Prevents clickjacking attacks
- **X-XSS-Protection**: Enables browser XSS protection
- **Strict-Transport-Security**: Enforces HTTPS connections
- **Content-Security-Policy**: Restricts resource loading

### 5. Data Protection
- **Password Hashing**: bcrypt with salt for secure storage
- **Sensitive Data Logging**: No passwords or tokens in logs
- **Data Encryption**: Sensitive data encrypted at rest
- **Secure Configuration**: Environment-based configuration

## API Endpoints

### Authentication Endpoints

#### POST `/api/v1/auth/register`
Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "username",
  "password": "SecurePass123!",
  "display_name": "Display Name",
  "bio": "Optional bio",
  "avatar_url": "https://example.com/avatar.jpg"
}
```

**Validation Rules:**
- Email: Valid email format, not from temporary providers
- Username: 3-50 chars, alphanumeric + underscore, not reserved
- Password: Min 8 chars, uppercase, lowercase, number, special char
- Display name: 1-100 chars, no empty strings
- Bio: Max 500 chars
- Avatar URL: Valid HTTP/HTTPS URL

**Response:**
```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "username": "username",
      "display_name": "Display Name"
    },
    "tokens": {
      "access_token": "jwt-token",
      "refresh_token": "jwt-refresh-token",
      "token_type": "bearer"
    }
  }
}
```

#### POST `/api/v1/auth/login`
Authenticate user and return tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "username": "username",
      "display_name": "Display Name"
    },
    "tokens": {
      "access_token": "jwt-token",
      "refresh_token": "jwt-refresh-token",
      "token_type": "bearer"
    }
  }
}
```

#### POST `/api/v1/auth/refresh`
Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "jwt-refresh-token"
}
```

**Response:**
```json
{
  "access_token": "new-jwt-token",
  "refresh_token": "new-jwt-refresh-token",
  "token_type": "bearer"
}
```

#### POST `/api/v1/auth/logout`
Revoke refresh token and logout user.

**Request Body:**
```json
{
  "refresh_token": "jwt-refresh-token"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

### Posts Endpoints

#### GET `/api/v1/posts`
Get paginated list of posts with optional filtering.

**Query Parameters:**
- `page`: Page number (default: 1)
- `size`: Items per page (default: 10, max: 100)
- `post_type`: Filter by post type (issue, announcement, news, accomplishment)
- `area`: Filter by area/location
- `post_status`: Filter by status (open, in-progress, resolved)
- `category`: Filter by category
- `sort_by`: Sort field (default: timestamp)
- `order`: Sort order (asc, desc, default: desc)

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Post Title",
      "content": "Post content",
      "post_type": "issue",
      "area": "Downtown",
      "category": "Infrastructure",
      "status": "open",
      "author": {
        "id": "uuid",
        "username": "author",
        "display_name": "Author Name"
      },
      "vote_count": 5,
      "comment_count": 3,
      "user_vote": "upvote",
      "is_saved": false,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "size": 10,
  "has_more": true
}
```

#### POST `/api/v1/posts`
Create a new post (requires authentication).

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Request Body:**
```json
{
  "title": "Post Title",
  "content": "Post content with detailed description",
  "post_type": "issue",
  "area": "Downtown",
  "category": "Infrastructure",
  "media_urls": ["https://example.com/image.jpg"]
}
```

**Validation Rules:**
- Title: 5-200 chars, no HTML
- Content: 10-2000 chars, no scripts/unsafe HTML
- Area: Max 100 chars
- Category: Max 50 chars
- Media URLs: Max 5 URLs, HTTP/HTTPS only

**Response:**
```json
{
  "success": true,
  "message": "Post created successfully",
  "data": {
    "post": {
      "id": "uuid",
      "title": "Post Title",
      "content": "Post content",
      "post_type": "issue",
      "area": "Downtown",
      "category": "Infrastructure",
      "status": "open",
      "author": {
        "id": "uuid",
        "username": "author",
        "display_name": "Author Name"
      },
      "vote_count": 0,
      "comment_count": 0,
      "user_vote": null,
      "is_saved": false,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  }
}
```

## Error Handling

### Error Response Format
All errors follow a consistent format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes
- `200`: Success
- `400`: Bad Request (validation errors, business logic errors)
- `401`: Unauthorized (invalid/missing token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found (resource doesn't exist)
- `422`: Unprocessable Entity (validation errors)
- `429`: Too Many Requests (rate limit exceeded)
- `500`: Internal Server Error (server-side errors)

### Rate Limit Headers
When rate limiting is active, responses include:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time when rate limit resets (Unix timestamp)
- `Retry-After`: Seconds to wait before retrying (on 429 errors)

## Development Guidelines

### Testing
- Use the comprehensive test suite in `tests/`
- Test all validation rules and edge cases
- Mock external dependencies
- Test security features (XSS, SQL injection, etc.)

### Configuration
- Use environment variables for all configuration
- Validate configuration on startup
- Use different configurations for dev/staging/production
- Never commit secrets to version control

### Logging
- Log all security-related events
- Use structured logging for easier analysis
- Include request IDs for tracing
- Avoid logging sensitive information

### Security Checklist
- [ ] All endpoints have proper authentication
- [ ] Input validation on all user data
- [ ] Rate limiting configured
- [ ] Security headers enabled
- [ ] HTTPS enforced in production
- [ ] Database queries parameterized
- [ ] Sensitive data encrypted
- [ ] Error messages don't leak information
- [ ] Regular security updates applied

## Production Deployment

### Environment Variables
See `.env.production` for required production configuration.

### Database Setup
1. Create PostgreSQL database with PostGIS extension
2. Run migrations in `app/db/migrations/`
3. Configure connection pooling
4. Set up regular backups

### Security Hardening
1. Use strong, unique SECRET_KEY
2. Enable HTTPS with valid certificates
3. Configure firewall rules
4. Set up monitoring and alerting
5. Regular security audits
6. Keep dependencies updated

### Performance Optimization
1. Configure database connection pooling
2. Use caching for frequently accessed data
3. Implement database indexing
4. Monitor query performance
5. Use CDN for static assets
6. Configure load balancing if needed
