# CivicPulse Backend API

A FastAPI backend for the CivicPulse civic engagement platform.

## Features

- **Authentication & Authorization**: JWT-based auth with refresh tokens
- **User Management**: Citizen and representative user roles
- **Post Management**: Create, read, update, delete civic posts
- **Voting System**: Upvote/downvote posts with engagement tracking
- **Comments**: Nested comments on posts
- **Notifications**: Real-time notifications for user activities
- **Analytics**: Civic engagement insights and statistics
- **File Upload**: Image and video support via Cloudinary

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with raw SQL and asyncpg
- **Authentication**: JWT tokens with bcrypt password hashing
- **File Storage**: Cloudinary
- **Validation**: Pydantic schemas
- **Testing**: Pytest

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL
- Cloudinary account (for file uploads)

### Installation

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Set up the database:
```bash
# Create PostgreSQL database
createdb civicpulse

# Run migrations (after implementing Alembic)
alembic upgrade head
```

6. Start the development server:
```bash
python run.py
```

The API will be available at `http://localhost:8000`

### API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   └── api.py          # Main API router
│   │   └── endpoints/          # API endpoints
│   │       ├── auth.py         # Authentication
│   │       ├── users.py        # User management
│   │       ├── posts.py        # Post management
│   │       ├── comments.py     # Comment system
│   │       ├── notifications.py # Notifications
│   │       └── analytics.py    # Analytics
│   ├── core/
│   │   └── config.py           # Application settings
│   ├── db/
│   │   └── database.py         # Database connection
│   ├── models/
│   │   └── __init__.py         # Pydantic models
│   ├── schemas/
│   │   └── __init__.py         # Pydantic schemas
│   ├── services/               # Business logic
│   ├── utils/                  # Utility functions
│   └── main.py                 # FastAPI app creation
├── tests/                      # Test files
├── docs/                       # Documentation
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
└── run.py                     # Development server
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - User logout

### Users
- `GET /api/v1/users/profile` - Get user profile
- `PUT /api/v1/users/profile` - Update user profile
- `POST /api/v1/users/avatar` - Upload avatar

### Posts
- `GET /api/v1/posts` - Get posts (with filters)
- `POST /api/v1/posts` - Create new post
- `GET /api/v1/posts/{post_id}` - Get specific post
- `PUT /api/v1/posts/{post_id}` - Update post
- `DELETE /api/v1/posts/{post_id}` - Delete post
- `POST /api/v1/posts/{post_id}/upvote` - Upvote post
- `POST /api/v1/posts/{post_id}/downvote` - Downvote post
- `POST /api/v1/posts/{post_id}/save` - Save/unsave post

### Comments
- `GET /api/v1/posts/{post_id}/comments` - Get post comments
- `POST /api/v1/comments` - Create comment
- `PUT /api/v1/comments/{comment_id}` - Update comment
- `DELETE /api/v1/comments/{comment_id}` - Delete comment

### Notifications
- `GET /api/v1/notifications` - Get user notifications
- `PUT /api/v1/notifications/{notification_id}/read` - Mark as read
- `PUT /api/v1/notifications/mark-all-read` - Mark all as read

### Analytics
- `GET /api/v1/analytics/dashboard` - Get dashboard analytics
- `GET /api/v1/analytics/issues` - Get issue statistics
- `GET /api/v1/analytics/areas` - Get area performance data

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black app/
isort app/
```

### Type Checking
```bash
mypy app/
```

## Deployment

The application is ready for deployment on platforms like:
- Heroku
- Railway
- DigitalOcean App Platform
- AWS/GCP/Azure

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests
4. Run the test suite
5. Submit a pull request
