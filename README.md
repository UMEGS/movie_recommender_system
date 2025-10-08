# 🎬 Movie Recommendation System

AI-powered movie recommendation system using **PostgreSQL with pgvector** for vector similarity search and **Ollama** for generating embeddings. Fetches 70,000+ movies from YTS API and provides semantic search and recommendations.

## ✨ Features

- 🚀 **Fast Data Fetching** - Multiprocessing to fetch 70k+ movies from YTS API
- 🤖 **AI Embeddings** - Uses Ollama's nomic-embed-text for 768-dimensional vectors
- 🔍 **Vector Search** - PostgreSQL pgvector for fast similarity search
- 📊 **Multiple Recommendation Methods** - Movie-to-movie, text-based, genre-based
- ⚙️ **Configuration via .env** - All settings in one place
- 🔄 **Resume Capability** - Skip existing data automatically
- 🎯 **ORM-based** - SQLAlchemy for clean database operations

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Ollama

```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama server
ollama serve

# Pull embedding model
ollama pull nomic-embed-text
```

### 3. Configure Environment

Edit `.env` file with your settings:

```bash
# Database
DB_HOST=your_host
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=postgres

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

### 4. Test Setup

```bash
# Test database connection
python scripts/test_db_connection.py

# Test Ollama connection
python scripts/test_ollama_connection.py
```

### 5. Fetch Movie Data

```bash
# Fetch movies from YTS API (run from project root)
python scripts/fetch_yts_data.py --max-pages 100 --workers 16

# Monitor progress (in another terminal)
python scripts/monitor_progress.py
```

### 6. Generate Embeddings

```bash
# Generate embeddings for all movies (run from project root)
python scripts/generate_embeddings.py
```

### 7. Get Recommendations

```bash
# Get recommendations for a movie (run from project root)
python recommendation_engine.py --movie-id 123 --limit 10

# Search movies by text
python recommendation_engine.py --text "sci-fi thriller about time travel"

# Get trending movies
python recommendation_engine.py --trending
```

## 📁 Project Structure

```
movie_recommender_system/
├── .env                          # Configuration (all settings here!)
├── .env.example                  # Example configuration
├── README.md                     # This file
├── requirements.txt              # Python dependencies
├── config.py                     # Loads config from .env
├── recommendation_engine.py      # Main recommendation API
│
├── database/
│   ├── config.py                 # Database config
│   ├── db.py                     # Database manager with ORM
│   ├── models.py                 # SQLAlchemy models
│   └── database.sql              # Database schema
│
├── scripts/
│   ├── fetch_yts_data.py         # Fetch movies from YTS API
│   ├── generate_embeddings.py    # Generate embeddings with Ollama
│   ├── test_db_connection.py     # Test database
│   ├── test_ollama_connection.py # Test Ollama setup
│   └── monitor_progress.py       # Monitor fetching progress
│
└── docs/
    ├── VECTOR_EMBEDDINGS_GUIDE.md    # Detailed embeddings guide
    ├── QUICK_START_GUIDE.md          # Quick start guide
    └── ...                           # Other documentation
```

## 🎯 Usage Examples

### REST API

Start the FastAPI server:
```bash
./api/run.sh
# or
uvicorn api.main:app --reload
```

Access the interactive documentation at http://localhost:8000/docs

```bash
# Get recommendations
curl "http://localhost:8000/api/recommendations/movie/1?limit=5"

# Search movies
curl "http://localhost:8000/api/search?query=action&limit=10"

# Get trending movies
curl "http://localhost:8000/api/trending?limit=10"
```

### Python API

```python
from scripts.recommendation_engine import MovieRecommendationEngine

engine = MovieRecommendationEngine()

# Get similar movies
recommendations = engine.recommend_by_movie_id(123, limit=10)

# Search by text description
movies = engine.get_similar_by_text(
    "A thriller about artificial intelligence",
    limit=10
)

# Get by genres
movies = engine.recommend_by_genres(
    genres=["Action", "Sci-Fi"],
    limit=10,
    min_rating=7.0
)

# Search movies
results = engine.search_movies("inception", limit=10)

# Get trending
trending = engine.get_trending_movies(limit=20)

engine.close()
```

### Command Line

```bash
# Movie recommendations
python recommendation_engine.py --movie-id 123 --limit 10
python recommendation_engine.py --external-id 12345

# Text-based search
python recommendation_engine.py --text "space exploration sci-fi"

# Genre-based
python recommendation_engine.py --genres Action Sci-Fi

# Search
python recommendation_engine.py --search "inception"

# Trending & Top Rated
python recommendation_engine.py --trending --limit 20
python recommendation_engine.py --top-rated --limit 20
```

## ⚙️ Configuration (.env)

All configuration is in `.env` file:

```bash
# Database Configuration
DB_HOST=161.97.175.211
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=postgres
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# YTS API Configuration
YTS_API_URL=https://yts.mx/api/v2
YTS_BATCH_SIZE=50
YTS_MAX_PAGES=100

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_TIMEOUT=120

# Embedding Configuration
EMBEDDING_DIMENSION=768
EMBEDDING_BATCH_SIZE=100

# Multiprocessing Configuration
MAX_WORKERS=16
FETCH_BATCH_SIZE=50

# Application Settings
LOG_LEVEL=INFO
```

## 🔧 How It Works

### 1. Data Fetching
- Fetches movies from YTS API using multiprocessing
- Stores movies, genres, cast, and torrents in PostgreSQL
- Automatically skips duplicates

### 2. Embedding Generation
- Creates text representation: `"Title: Inception | Year: 2010 | Genres: Action, Sci-Fi | Description: ..."`
- Sends to Ollama's nomic-embed-text model
- Gets back 768-dimensional vector
- Stores in `movie_embeddings` table with pgvector

### 3. Similarity Search
- Uses PostgreSQL pgvector for fast vector similarity
- Supports cosine similarity, L2 distance, inner product
- Returns most similar movies based on embeddings

## 📊 Performance

- **Data Fetching**: 40-80 movies/second
- **Embedding Generation**: 2-5 embeddings/second (CPU), 10-20/sec (GPU)
- **Similarity Search**: <100ms for 70k movies (with indexes)

## 🐛 Troubleshooting

### Ollama Issues

```bash
# Check if Ollama is running
ps aux | grep ollama

# Start Ollama
ollama serve

# Pull model
ollama pull nomic-embed-text
```

### Database Issues

```sql
-- Install pgvector extension
CREATE EXTENSION vector;
```

### Performance Issues

```bash
# Reduce workers if needed
python scripts/generate_embeddings.py --workers 4 --batch-size 50
```

## 📚 Documentation

- **Detailed Embeddings Guide**: `docs/VECTOR_EMBEDDINGS_GUIDE.md`
- **Quick Start Guide**: `docs/QUICK_START_GUIDE.md`
- **Database Schema**: `database/database.sql`

## 🛠️ Tech Stack

- **Python 3.8+**
- **PostgreSQL** with **pgvector** extension
- **Ollama** with **nomic-embed-text** model
- **SQLAlchemy** ORM
- **FastAPI** (for REST API)
- **Multiprocessing** for parallel processing

## 📝 License

MIT License

## 🎉 Summary

✅ Fetch 70k+ movies from YTS API  
✅ Generate AI embeddings with Ollama  
✅ Store vectors in PostgreSQL with pgvector  
✅ Fast similarity search and recommendations  
✅ Multiple recommendation methods  
✅ All configuration via .env  
✅ Resume capability for interrupted processes  

Your movie recommendation system is ready! 🚀🎬

