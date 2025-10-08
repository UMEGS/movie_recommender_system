# Movie Recommendation API

FastAPI-based REST API for AI-powered movie recommendations using vector embeddings.

## 🚀 Quick Start

### Start the API

```bash
# Option 1: Using the run script
./api/run.sh

# Option 2: Using uvicorn directly
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Option 3: From Python
python -m uvicorn api.main:app --reload
```

### Access Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📋 API Endpoints

### General
- `GET /` - API information
- `GET /health` - Health check

### Movies
- `GET /api/movies/{movie_id}` - Get movie by ID
- `GET /api/movies/external/{external_id}` - Get movie by external ID

### Search
- `GET /api/search` - Full-text search

### Recommendations
- `GET /api/recommendations/movie/{movie_id}` - Recommendations by movie ID
- `GET /api/recommendations/external/{external_id}` - Recommendations by external ID
- `GET /api/recommendations/genres` - Recommendations by genres
- `GET /api/recommendations/text` - Recommendations by text description

### Discovery
- `GET /api/trending` - Trending movies
- `GET /api/top-rated` - Top rated movies

## 💡 Examples

### Get Movie Details
```bash
curl http://localhost:8000/api/movies/1
```

### Get Recommendations
```bash
curl "http://localhost:8000/api/recommendations/movie/1?limit=5&distance_metric=cosine"
```

### Search Movies
```bash
curl "http://localhost:8000/api/search?query=action%20thriller&limit=10"
```

### Get Trending Movies
```bash
curl "http://localhost:8000/api/trending?limit=10&min_year=2022"
```

### Recommendations by Text
```bash
curl "http://localhost:8000/api/recommendations/text?text=A%20movie%20about%20space%20exploration&limit=5"
```

## 📚 Full Documentation

See [API_DOCUMENTATION.md](../docs/API_DOCUMENTATION.md) for complete API reference.

## 🏗️ Architecture

The API is built on:
- **FastAPI** - Modern, fast web framework
- **Pydantic** - Data validation
- **MovieRecommendationEngine** - Business logic layer
- **MovieQueries** - Database access layer
- **PostgreSQL + pgvector** - Vector database

## 🔧 Configuration

The API uses the same configuration as the rest of the system:
- Database settings from `.env`
- Ollama settings from `config.py`

## 🧪 Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test recommendations
curl "http://localhost:8000/api/recommendations/movie/1?limit=3"

# Test search
curl "http://localhost:8000/api/search?query=action&limit=5"
```

## 🚢 Production Deployment

### Using Gunicorn

```bash
pip install gunicorn
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

## 📊 Response Format

All endpoints return JSON with consistent structure:

### Success Response
```json
{
  "total": 10,
  "movies": [...],
  "distance_metric": "cosine"
}
```

### Error Response
```json
{
  "error": "Error message",
  "detail": "Detailed information"
}
```

## 🔐 CORS Configuration

CORS is configured to allow all origins by default. For production, update `api/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## 📝 Notes

- All movie IDs in the API are internal database IDs
- Use `/api/movies/external/{external_id}` for YTS external IDs
- Similarity scores range from 0 to 1 (higher is more similar)
- Distance metrics: `cosine` (default), `l2`, `inner_product`

