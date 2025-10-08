# Movie Recommendation API Documentation

## Overview

FastAPI-based REST API for the Movie Recommendation System. Provides endpoints for movie search, recommendations, and discovery using AI-powered vector embeddings.

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Running the API

```bash
# Option 1: Using the run script
./api/run.sh

# Option 2: Using uvicorn directly
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Option 3: Using Python
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Access Documentation

Once the server is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Endpoints

### General

#### `GET /`
Root endpoint with API information

**Response:**
```json
{
  "name": "Movie Recommendation API",
  "version": "2.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

#### `GET /health`
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "database": "connected"
}
```

### Movies

#### `GET /api/movies/{movie_id}`
Get movie details by internal database ID

**Parameters:**
- `movie_id` (path, required): Internal database movie ID

**Example:**
```bash
curl http://localhost:8000/api/movies/1
```

**Response:**
```json
{
  "id": 1,
  "external_id": 12345,
  "imdb_code": "tt1234567",
  "title": "Movie Title",
  "year": 2020,
  "rating": 7.5,
  "genres": ["Action", "Thriller"],
  "description_full": "Movie description...",
  "similarity_score": null
}
```

#### `GET /api/movies/external/{external_id}`
Get movie details by YTS external ID

**Parameters:**
- `external_id` (path, required): YTS external movie ID

**Example:**
```bash
curl http://localhost:8000/api/movies/external/12345
```

### Search

#### `GET /api/search`
Search movies by title or description using full-text search

**Parameters:**
- `query` (query, required): Search query string
- `limit` (query, optional): Maximum number of results (1-100, default: 10)

**Example:**
```bash
curl "http://localhost:8000/api/search?query=action%20thriller&limit=5"
```

**Response:**
```json
{
  "total": 5,
  "movies": [
    {
      "id": 1,
      "title": "Action Movie",
      "year": 2020,
      "rating": 7.5,
      "genres": ["Action", "Thriller"]
    }
  ]
}
```

### Recommendations

#### `GET /api/recommendations/movie/{movie_id}`
Get movie recommendations based on a movie ID using vector similarity

**Parameters:**
- `movie_id` (path, required): Internal database movie ID
- `limit` (query, optional): Maximum number of recommendations (1-100, default: 10)
- `distance_metric` (query, optional): Distance metric - `cosine`, `l2`, or `inner_product` (default: `cosine`)

**Example:**
```bash
curl "http://localhost:8000/api/recommendations/movie/1?limit=5&distance_metric=cosine"
```

**Response:**
```json
{
  "total": 5,
  "movies": [
    {
      "id": 2,
      "title": "Similar Movie",
      "year": 2019,
      "rating": 7.8,
      "genres": ["Action", "Thriller"],
      "similarity_score": 0.85
    }
  ],
  "distance_metric": "cosine"
}
```

#### `GET /api/recommendations/external/{external_id}`
Get movie recommendations based on YTS external ID

**Parameters:**
- `external_id` (path, required): YTS external movie ID
- `limit` (query, optional): Maximum number of recommendations (1-100, default: 10)
- `distance_metric` (query, optional): Distance metric (default: `cosine`)

**Example:**
```bash
curl "http://localhost:8000/api/recommendations/external/12345?limit=10"
```

#### `GET /api/recommendations/genres`
Get movie recommendations based on genres

**Parameters:**
- `genres` (query, required): List of genre names (can specify multiple)
- `limit` (query, optional): Maximum number of recommendations (1-100, default: 10)
- `min_rating` (query, optional): Minimum rating threshold (0-10, default: 6.0)

**Example:**
```bash
curl "http://localhost:8000/api/recommendations/genres?genres=Action&genres=Sci-Fi&limit=10&min_rating=7.0"
```

**Response:**
```json
{
  "total": 10,
  "movies": [
    {
      "id": 3,
      "title": "Sci-Fi Action Movie",
      "year": 2021,
      "rating": 8.2,
      "genres": ["Action", "Sci-Fi"]
    }
  ]
}
```

#### `GET /api/recommendations/text`
Find movies similar to a text description using AI embeddings

**Parameters:**
- `text` (query, required): Text description
- `limit` (query, optional): Maximum number of recommendations (1-100, default: 10)

**Example:**
```bash
curl "http://localhost:8000/api/recommendations/text?text=A%20movie%20about%20space%20exploration&limit=5"
```

**Response:**
```json
{
  "total": 5,
  "movies": [
    {
      "id": 4,
      "title": "Interstellar",
      "year": 2014,
      "rating": 8.6,
      "genres": ["Sci-Fi", "Drama"],
      "similarity_score": 0.92
    }
  ]
}
```

### Discovery

#### `GET /api/trending`
Get trending/popular movies

**Parameters:**
- `limit` (query, optional): Maximum number of movies (1-100, default: 20)
- `min_year` (query, optional): Minimum year threshold (default: 2020)

**Example:**
```bash
curl "http://localhost:8000/api/trending?limit=10&min_year=2022"
```

**Response:**
```json
{
  "total": 10,
  "movies": [
    {
      "id": 5,
      "title": "Trending Movie",
      "year": 2023,
      "rating": 8.0,
      "genres": ["Action", "Adventure"],
      "like_count": 50000
    }
  ]
}
```

#### `GET /api/top-rated`
Get top rated movies

**Parameters:**
- `limit` (query, optional): Maximum number of movies (1-100, default: 20)
- `min_votes` (query, optional): Minimum vote count threshold (default: 100)

**Example:**
```bash
curl "http://localhost:8000/api/top-rated?limit=10&min_votes=1000"
```

**Response:**
```json
{
  "total": 10,
  "movies": [
    {
      "id": 6,
      "title": "Top Rated Movie",
      "year": 2010,
      "rating": 9.0,
      "genres": ["Drama"],
      "like_count": 100000
    }
  ]
}
```

## Response Models

### MovieResponse

```json
{
  "id": 1,
  "external_id": 12345,
  "imdb_code": "tt1234567",
  "title": "Movie Title",
  "title_english": "Movie Title",
  "year": 2020,
  "rating": 7.5,
  "runtime": 120,
  "genres": ["Action", "Thriller"],
  "description_full": "Full description...",
  "description_intro": "Short description...",
  "language": "en",
  "like_count": 5000,
  "small_cover_image": "https://...",
  "medium_cover_image": "https://...",
  "large_cover_image": "https://...",
  "yt_trailer_code": "abc123",
  "cast": [
    {
      "name": "Actor Name",
      "imdb_code": "nm1234567"
    }
  ],
  "torrents_count": 3,
  "similarity_score": 0.85
}
```

### RecommendationResponse

```json
{
  "total": 10,
  "movies": [...],
  "distance_metric": "cosine"
}
```

### ErrorResponse

```json
{
  "error": "Error message",
  "detail": "Detailed error information"
}
```

## Error Codes

- `200` - Success
- `404` - Resource not found
- `422` - Validation error
- `500` - Internal server error
- `503` - Service unavailable

## Python Client Example

```python
import requests

BASE_URL = "http://localhost:8000"

# Get movie details
response = requests.get(f"{BASE_URL}/api/movies/1")
movie = response.json()
print(f"Movie: {movie['title']}")

# Get recommendations
response = requests.get(
    f"{BASE_URL}/api/recommendations/movie/1",
    params={"limit": 5, "distance_metric": "cosine"}
)
recommendations = response.json()
print(f"Found {recommendations['total']} recommendations")

for movie in recommendations['movies']:
    print(f"  - {movie['title']} (Score: {movie['similarity_score']:.3f})")

# Search movies
response = requests.get(
    f"{BASE_URL}/api/search",
    params={"query": "action thriller", "limit": 10}
)
results = response.json()
print(f"Found {results['total']} movies")

# Get trending movies
response = requests.get(
    f"{BASE_URL}/api/trending",
    params={"limit": 10, "min_year": 2022}
)
trending = response.json()
print(f"Trending movies: {trending['total']}")
```

## JavaScript/TypeScript Client Example

```javascript
const BASE_URL = "http://localhost:8000";

// Get movie details
async function getMovie(movieId) {
  const response = await fetch(`${BASE_URL}/api/movies/${movieId}`);
  const movie = await response.json();
  return movie;
}

// Get recommendations
async function getRecommendations(movieId, limit = 10) {
  const response = await fetch(
    `${BASE_URL}/api/recommendations/movie/${movieId}?limit=${limit}&distance_metric=cosine`
  );
  const data = await response.json();
  return data;
}

// Search movies
async function searchMovies(query, limit = 10) {
  const response = await fetch(
    `${BASE_URL}/api/search?query=${encodeURIComponent(query)}&limit=${limit}`
  );
  const data = await response.json();
  return data;
}

// Usage
const movie = await getMovie(1);
console.log(`Movie: ${movie.title}`);

const recommendations = await getRecommendations(1, 5);
console.log(`Found ${recommendations.total} recommendations`);
```

## Production Deployment

### Using Gunicorn

```bash
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

Configure CORS and other settings in production:

```python
# In api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domains
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## Rate Limiting

Consider adding rate limiting for production:

```bash
pip install slowapi
```

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/recommendations/movie/{movie_id}")
@limiter.limit("10/minute")
async def get_recommendations_by_movie_id(...):
    ...
```

## Testing

```bash
# Run tests
pytest tests/test_api.py

# Test with curl
curl http://localhost:8000/health
curl http://localhost:8000/api/movies/1
curl "http://localhost:8000/api/recommendations/movie/1?limit=5"
```

## Support

For issues or questions:
- Check the interactive docs at `/docs`
- Review the code structure in `docs/CODE_STRUCTURE.md`
- Check logs for error details

