# Representative Account Linking Feature

## Overview

This feature allows users to link their CivicPulse account to exactly one representative account at a time. Users can select from available representative accounts, link them to their profile, and update the association through the settings interface.

## Backend Implementation

### Database Schema

The implementation uses the existing database schema:

- **`users` table**: Contains `rep_accounts` column (UUID array) to store linked representative IDs
- **`representatives` table**: From static-data, contains representative information with `user_id` field to link back to users
- **`jurisdictions` table**: Contains jurisdiction information for representatives
- **`titles` table**: Contains title/role information for representatives

### Key Components

#### 1. Representative Service (`app/services/representative_service.py`)

The `RepresentativeService` class handles all representative-related operations:

**Key Methods:**
- `get_available_representatives()`: Returns all unclaimed representative accounts
- `get_representative_by_id(rep_id)`: Gets detailed representative information
- `get_user_linked_representative(user_id)`: Gets the representative linked to a user
- `link_user_to_representative(user_id, rep_id)`: Links a user to a representative
- `unlink_user_from_representative(user_id)`: Removes the link
- `update_user_representative(user_id, new_rep_id)`: Updates the linked representative

#### 2. Representative Models (`app/models/pydantic_models.py`)

**New Models Added:**
- `RepresentativeBase`: Base model for representative data
- `RepresentativeResponse`: Full representative information for API responses
- `RepresentativeLinkRequest`: Request model for linking operations
- `UserWithRepresentativeResponse`: Extended user response with representative info

#### 3. Representative Endpoints (`app/api/endpoints/representatives.py`)

**Available Endpoints:**

```
GET /api/v1/representatives/available
```
- Returns all available (unclaimed) representative accounts
- No authentication required

```
GET /api/v1/representatives/{rep_id}
```
- Returns details for a specific representative
- No authentication required

```
GET /api/v1/representatives/user/{user_id}/linked
```
- Returns the representative linked to a user
- Requires authentication (user can access own data)

```
POST /api/v1/representatives/link
```
- Links current user to a representative account
- Requires authentication
- Body: `{"representative_id": "uuid"}`

```
PUT /api/v1/representatives/link
```
- Updates current user's linked representative
- Requires authentication
- Body: `{"representative_id": "uuid"}`

```
DELETE /api/v1/representatives/link
```
- Unlinks current user from their representative
- Requires authentication

#### 4. Updated User Endpoints (`app/api/endpoints/users.py`)

**Modified Endpoints:**

```
GET /api/v1/users/profile
```
- Now includes linked representative information in the response
- Returns `UserWithRepresentativeResponse` model

```
GET /api/v1/users/settings/representative
```
- New endpoint for representative settings management
- Returns current linked representative and available options

### Business Logic

#### Linking Rules
1. **One Representative Per User**: Each user can link to exactly one representative at a time
2. **One User Per Representative**: Each representative can only be claimed by one user
3. **Atomic Operations**: Linking/unlinking operations are transactional
4. **Update Behavior**: Updating a link automatically unlinks from the previous representative

#### Data Consistency
- The `users.rep_accounts` array stores the linked representative UUID
- The `representatives.user_id` field is updated to reference the linked user
- Both tables are updated atomically within transactions

## API Usage Examples

### 1. Get Available Representatives

```bash
curl -X GET "http://localhost:8000/api/v1/representatives/available"
```

**Response:**
```json
{
  "success": true,
  "message": "Available representatives retrieved successfully",
  "data": {
    "representatives": [
      {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "jurisdiction_id": "456e7890-e89b-12d3-a456-426614174001",
        "title_id": "789e0123-e89b-12d3-a456-426614174002",
        "user_id": null,
        "jurisdiction_name": "Mumbai North",
        "jurisdiction_level": "parliamentary_constituency",
        "title_name": "Member of Parliament",
        "abbreviation": "MP",
        "level_rank": 3,
        "description": "Elected representative to the Parliament",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z"
      }
    ],
    "total": 1
  }
}
```

### 2. Link Representative to User

```bash
curl -X POST "http://localhost:8000/api/v1/representatives/link" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"representative_id": "123e4567-e89b-12d3-a456-426614174000"}'
```

**Response:**
```json
{
  "success": true,
  "message": "Representative account linked successfully",
  "data": {
    "user": {
      "id": "user-uuid",
      "username": "john_doe",
      "email": "john@example.com",
      "linked_representative": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "title_name": "Member of Parliament",
        "jurisdiction_name": "Mumbai North"
      }
    },
    "representative": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "title_name": "Member of Parliament",
      "jurisdiction_name": "Mumbai North",
      "user_id": "user-uuid"
    }
  }
}
```

### 3. Get User Profile with Representative

```bash
curl -X GET "http://localhost:8000/api/v1/users/profile" \
  -H "Authorization: Bearer <access_token>"
```

**Response:**
```json
{
  "success": true,
  "message": "User profile retrieved successfully",
  "data": {
    "id": "user-uuid",
    "username": "john_doe",
    "email": "john@example.com",
    "display_name": "John Doe",
    "bio": "Citizen representative",
    "linked_representative": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "title_name": "Member of Parliament",
      "jurisdiction_name": "Mumbai North",
      "abbreviation": "MP"
    }
  }
}
```

### 4. Get Representative Settings

```bash
curl -X GET "http://localhost:8000/api/v1/users/settings/representative" \
  -H "Authorization: Bearer <access_token>"
```

**Response:**
```json
{
  "success": true,
  "message": "Representative settings retrieved successfully",
  "data": {
    "linked_representative": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "title_name": "Member of Parliament",
      "jurisdiction_name": "Mumbai North"
    },
    "available_representatives": [
      {
        "id": "456e7890-e89b-12d3-a456-426614174001",
        "title_name": "State MLA",
        "jurisdiction_name": "Bandra West"
      }
    ],
    "can_change": true
  }
}
```

## Error Handling

The implementation includes comprehensive error handling:

- **404 Not Found**: Representative doesn't exist
- **400 Bad Request**: Representative already claimed
- **401 Unauthorized**: Authentication required
- **500 Internal Server Error**: Database or system errors

## Security Considerations

1. **Authentication Required**: All linking operations require valid JWT tokens
2. **User Isolation**: Users can only manage their own representative links
3. **Transaction Safety**: All database operations use transactions
4. **Input Validation**: All UUIDs and request data are validated

## Testing

A test script is provided at `backend/test_representatives.py` to validate the service functionality:

```bash
cd backend
python3 test_representatives.py
```

## Database Migration Notes

The implementation uses existing schema from the static-data repository. No additional database migrations are required, as the schema already includes:

- `users.rep_accounts` column for storing linked representatives
- `representatives.user_id` column for reverse linking
- Proper indexes for performance

## Integration with Frontend

The backend provides all necessary endpoints for frontend integration:

1. **Settings Page**: Use `/users/settings/representative` to show current status and options
2. **Profile Display**: User profiles automatically include representative information
3. **Representative Selection**: Use `/representatives/available` to populate selection dropdowns
4. **Link Management**: Use POST/PUT/DELETE endpoints for link operations

This implementation provides a complete backend foundation for the representative account linking feature as requested.
