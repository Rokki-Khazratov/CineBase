# API Reference

## 🔗 Base URL

```
http://localhost:8000/api/v1
```

## 🔐 Authentication

All protected endpoints require a JWT token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## 📚 Endpoints

### Authentication

#### Register User

```http
POST /auth/register
```

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "securepass123"
}
```

**Response:**

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "role": "user",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

**Errors:**

- `400` - Validation error
- `409` - Email already exists

#### Login User

```http
POST /auth/login
```

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "securepass123"
}
```

**Response:**

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "role": "user",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

**Errors:**

- `400` - Validation error
- `401` - Invalid credentials

#### Get Current User

```http
GET /auth/me
```

**Headers:**

```
Authorization: Bearer <token>
```

**Response:**

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "role": "user",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Errors:**

- `401` - Unauthorized

### Movies

#### List Movies

```http
GET /movies
```

**Query Parameters:**

- `limit` (int, 1-50, default 20) - Number of items per page
- `offset` (int, ≥0, default 0) - Number of items to skip
- `genre` (str) - Filter by genre
- `year_gte` (int) - Filter movies from year
- `year_lte` (int) - Filter movies to year
- `title_ilike` (str) - Search in title (case-insensitive)
- `sort` (str) - Sort by field (year, -year, created_at, -created_at, title, -title)

**Headers:**

```
Authorization: Bearer <token>
```

**Response:**

```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "title": "The Matrix",
      "year": 1999,
      "genres": ["Action", "Sci-Fi"],
      "overview": "A computer hacker learns about the true nature of reality.",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

**Headers:**

```
X-Cache: HIT|MISS
```

**Errors:**

- `400` - Invalid parameters
- `401` - Unauthorized

#### Create Movie

```http
POST /movies
```

**Headers:**

```
Authorization: Bearer <admin-token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "title": "The Matrix",
  "year": 1999,
  "genres": ["Action", "Sci-Fi"],
  "overview": "A computer hacker learns about the true nature of reality."
}
```

**Response:**

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "The Matrix",
  "year": 1999,
  "genres": ["Action", "Sci-Fi"],
  "overview": "A computer hacker learns about the true nature of reality.",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Errors:**

- `400` - Validation error
- `401` - Unauthorized
- `403` - Forbidden (admin only)

#### Get Movie by ID

```http
GET /movies/{movie_id}
```

**Headers:**

```
Authorization: Bearer <token>
```

**Response:**

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "The Matrix",
  "year": 1999,
  "genres": ["Action", "Sci-Fi"],
  "overview": "A computer hacker learns about the true nature of reality.",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Headers:**

```
X-Cache: HIT|MISS
```

**Errors:**

- `401` - Unauthorized
- `404` - Movie not found

#### Update Movie

```http
PATCH /movies/{movie_id}
```

**Headers:**

```
Authorization: Bearer <admin-token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "title": "The Matrix Reloaded",
  "year": 2003
}
```

**Response:**

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "The Matrix Reloaded",
  "year": 2003,
  "genres": ["Action", "Sci-Fi"],
  "overview": "A computer hacker learns about the true nature of reality.",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Errors:**

- `400` - Validation error
- `401` - Unauthorized
- `403` - Forbidden (admin only)
- `404` - Movie not found

#### Delete Movie

```http
DELETE /movies/{movie_id}
```

**Headers:**

```
Authorization: Bearer <admin-token>
```

**Response:**

```json
{
  "message": "Movie deleted successfully"
}
```

**Errors:**

- `401` - Unauthorized
- `403` - Forbidden (admin only)
- `404` - Movie not found

### System

#### Health Check

```http
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0",
  "database": "connected",
  "redis": "connected"
}
```

**Errors:**

- `503` - Service unhealthy

## 📝 Data Models

### User

```json
{
  "id": "uuid",
  "email": "string",
  "role": "user|admin",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Movie

```json
{
  "id": "uuid",
  "title": "string",
  "year": "integer",
  "genres": ["string"],
  "overview": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Paginated Response

```json
{
  "items": ["array of items"],
  "total": "integer",
  "limit": "integer",
  "offset": "integer"
}
```

## 🚨 Error Responses

### Error Format

```json
{
  "detail": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "meta": {
      "field": "value",
      "timestamp": "2024-01-01T00:00:00Z"
    }
  }
}
```

### Error Codes

#### 400 Bad Request

- `VALIDATION_ERROR` - Input validation failed
- `INVALID_PARAMETERS` - Invalid query parameters

#### 401 Unauthorized

- `UNAUTHORIZED` - Missing or invalid token
- `INVALID_CREDENTIALS` - Wrong email/password

#### 403 Forbidden

- `FORBIDDEN` - Insufficient permissions
- `ADMIN_REQUIRED` - Admin role required

#### 404 Not Found

- `NOT_FOUND` - Resource not found
- `MOVIE_NOT_FOUND` - Movie with given ID not found

#### 409 Conflict

- `CONFLICT` - Resource conflict
- `EMAIL_EXISTS` - Email already registered

#### 422 Unprocessable Entity

- `VALIDATION_ERROR` - Pydantic validation failed

#### 500 Internal Server Error

- `INTERNAL_ERROR` - Unexpected server error

## 🔍 Examples

### Complete Authentication Flow

```bash
# 1. Register user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123"}'

# 2. Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123"}'

# 3. Get current user
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Movie Operations

```bash
# 1. List movies with pagination
curl -X GET "http://localhost:8000/api/v1/movies?limit=10&offset=0&sort=year" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 2. Filter movies by genre
curl -X GET "http://localhost:8000/api/v1/movies?genre=Action&year_gte=2000" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 3. Search movies by title
curl -X GET "http://localhost:8000/api/v1/movies?title_ilike=matrix" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 4. Create movie (admin only)
curl -X POST "http://localhost:8000/api/v1/movies" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Matrix",
    "year": 1999,
    "genres": ["Action", "Sci-Fi"],
    "overview": "A computer hacker learns about the true nature of reality."
  }'

# 5. Update movie (admin only)
curl -X PATCH "http://localhost:8000/api/v1/movies/MOVIE_ID" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "The Matrix Reloaded", "year": 2003}'

# 6. Delete movie (admin only)
curl -X DELETE "http://localhost:8000/api/v1/movies/MOVIE_ID" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

### Error Handling

```bash
# Invalid credentials
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "wrong@example.com", "password": "wrongpass"}'

# Response:
# {
#   "detail": {
#     "code": "INVALID_CREDENTIALS",
#     "message": "Invalid email or password",
#     "meta": {
#       "timestamp": "2024-01-01T00:00:00Z"
#     }
#   }
# }

# Unauthorized access
curl -X GET "http://localhost:8000/api/v1/auth/me"

# Response:
# {
#   "detail": {
#     "code": "UNAUTHORIZED",
#     "message": "Authentication required",
#     "meta": {
#       "timestamp": "2024-01-01T00:00:00Z"
#     }
#   }
# }
```

## 🔧 Rate Limiting

Currently no rate limiting is implemented. Future versions will include:

- 100 requests per minute per IP
- 1000 requests per hour per user
- 10 requests per minute for auth endpoints

## 📊 Caching

### Cache Headers

- `X-Cache: HIT` - Response served from cache
- `X-Cache: MISS` - Response generated from database

### Cache TTL

- Movies: 60 seconds
- Users: 300 seconds (5 minutes)

### Cache Invalidation

- Movies are invalidated on create/update/delete
- User cache is invalidated on profile updates

## 🔒 Security

### Authentication

- JWT tokens with 15-minute expiration
- Bearer token in Authorization header
- Stateless authentication (no server-side sessions)

### Authorization

- Role-based access control (User/Admin)
- Admin required for movie create/update/delete
- User can only read movies and manage own profile

### Input Validation

- All inputs validated with Pydantic
- SQL injection protection via SQLAlchemy ORM
- XSS protection with proper content types

## 📈 Performance

### Pagination

- Default limit: 20 items
- Maximum limit: 50 items
- Efficient offset-based pagination

### Filtering

- Database-level filtering for performance
- Indexed fields for fast queries
- Case-insensitive text search

### Sorting

- Whitelisted sort fields only
- Database-level sorting
- Support for ascending/descending order

## 🔄 Versioning

Current API version: `v1`

Version is included in the URL path: `/api/v1/`

Future versions will maintain backward compatibility for at least 6 months.
