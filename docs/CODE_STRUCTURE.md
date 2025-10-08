# Code Structure and Architecture

## Overview

The movie recommendation system follows a clean separation of concerns with distinct layers for database operations, business logic, and scripts.

## Directory Structure

```
movie_recommender_system/
├── database/               # Database layer
│   ├── config.py          # Database configuration
│   ├── db.py              # Database manager (connection pooling, sessions)
│   ├── queries.py         # Database query operations (NEW)
│   ├── models.py          # SQLAlchemy ORM models
│   └── database.sql       # Database schema
├── scripts/               # Application scripts
│   ├── recommendation_engine.py  # Recommendation engine (MOVED)
│   ├── fetch_yts_data.py         # Data fetching script
│   ├── generate_embeddings.py   # Embedding generation script
│   └── monitor_progress.py      # Database monitoring script
├── docs/                  # Documentation
└── config.py             # Application configuration
```

## Architecture Layers

### 1. Database Layer (`database/`)

#### `database/db.py` - DatabaseManager
**Purpose:** Manages database connections and sessions

**Responsibilities:**
- Connection pooling
- Session management
- Transaction handling
- pgvector type registration

**Key Methods:**
```python
get_session()      # Context manager for sessions
close_all()        # Close all connections
```

**Example:**
```python
from database.db import get_db_manager

db = get_db_manager()
with db.get_session() as session:
    # Use session here
    pass
```

#### `database/queries.py` - MovieQueries (NEW)
**Purpose:** All database query operations

**Responsibilities:**
- Movie retrieval queries
- Vector similarity search
- Full-text search
- Genre-based queries
- Trending/top-rated queries

**Key Methods:**
```python
get_movie_by_id(session, movie_id)
get_movie_by_external_id(session, external_id)
search_movies(session, query, limit)
find_similar_movies(session, movie_id, limit, distance_metric)
get_movies_by_genres(session, genres, limit, min_rating)
get_trending_movies(session, limit, min_year)
get_top_rated_movies(session, limit, min_votes)
```

**Design Pattern:**
- All methods accept a `session` parameter
- Returns ORM objects (Movie, MovieEmbedding)
- No business logic - pure data access

**Example:**
```python
from database.db import get_db_manager
from database.queries import MovieQueries

db = get_db_manager()
queries = MovieQueries(db)

with db.get_session() as session:
    movie = queries.get_movie_by_id(session, 123)
    similar = queries.find_similar_movies(session, 123, limit=10)
```

#### `database/models.py` - ORM Models
**Purpose:** SQLAlchemy ORM model definitions

**Models:**
- `Movie` - Movie information
- `MovieEmbedding` - Vector embeddings
- `Genre` - Movie genres
- `Cast` - Cast members
- `Torrent` - Torrent information

### 2. Business Logic Layer (`scripts/`)

#### `scripts/recommendation_engine.py` - MovieRecommendationEngine (MOVED)
**Purpose:** High-level recommendation API

**Responsibilities:**
- Coordinate database queries
- Convert ORM objects to dictionaries
- Calculate similarity scores
- Handle Ollama API for text embeddings
- Provide clean public API

**Key Methods:**
```python
get_movie_by_id(movie_id)
get_movie_by_external_id(external_id)
search_movies(query, limit)
recommend_by_movie_id(movie_id, limit, distance_metric)
recommend_by_external_id(external_id, limit, distance_metric)
recommend_by_genres(genres, limit, min_rating)
get_similar_by_text(text, limit)
get_trending_movies(limit, min_year)
get_top_rated_movies(limit, min_votes)
```

**Design Pattern:**
- Uses `MovieQueries` for all database operations
- Manages session lifecycle
- Converts ORM objects to dicts within session context
- Returns plain dictionaries (no ORM objects)

**Example:**
```python
from scripts.recommendation_engine import MovieRecommendationEngine

engine = MovieRecommendationEngine()

# Get recommendations
recs = engine.recommend_by_movie_id(123, limit=10)
for rec in recs:
    print(f"{rec['title']} - Score: {rec['similarity_score']}")

engine.close()
```

## Why This Structure?

### Separation of Concerns

1. **Database Layer** (`database/queries.py`)
   - ✅ Pure data access
   - ✅ No business logic
   - ✅ Reusable across different applications
   - ✅ Easy to test with mock sessions

2. **Business Logic Layer** (`scripts/recommendation_engine.py`)
   - ✅ Coordinates multiple queries
   - ✅ Handles data transformation
   - ✅ Provides clean API
   - ✅ Independent of database implementation

### Benefits

1. **Maintainability**
   - Database queries in one place
   - Easy to find and modify queries
   - Clear responsibility boundaries

2. **Testability**
   - Can test queries independently
   - Can mock database layer for business logic tests
   - Clear interfaces

3. **Reusability**
   - `MovieQueries` can be used by other scripts
   - Database operations are not tied to recommendation engine
   - Easy to add new features

4. **Scalability**
   - Easy to add new query methods
   - Easy to optimize specific queries
   - Can add caching layer between queries and engine

## Session Management Pattern

### ❌ Old Pattern (Problematic)
```python
# Query creates its own session
def get_movie(movie_id):
    with db.get_session() as session:
        return session.query(Movie).filter_by(id=movie_id).first()

# Problem: Movie object is detached when accessed outside session
movie = get_movie(123)
print(movie.title)  # DetachedInstanceError!
```

### ✅ New Pattern (Correct)
```python
# Query accepts session parameter
def get_movie(session, movie_id):
    return session.query(Movie).filter_by(id=movie_id).first()

# Caller manages session lifecycle
with db.get_session() as session:
    movie = get_movie(session, 123)
    print(movie.title)  # Works! Still in session
    movie_dict = convert_to_dict(movie)  # Convert while in session

# Use dict outside session
print(movie_dict['title'])  # Works! Plain dict
```

## Import Paths

### ✅ Correct Imports
```python
# For scripts and applications
from scripts.recommendation_engine import MovieRecommendationEngine

# For database operations
from database.db import get_db_manager
from database.queries import MovieQueries
from database.models import Movie, MovieEmbedding

# For configuration
from config import DB_CONFIG, OLLAMA_HOST
```

### ❌ Old Imports (Deprecated)
```python
# Don't use these anymore
from recommendation_engine import MovieRecommendationEngine  # File moved!
```

## CLI Usage

All scripts are now in the `scripts/` folder:

```bash
# Recommendation engine
python scripts/recommendation_engine.py --movie-id 123 --limit 10

# Fetch data
python scripts/fetch_yts_data.py --max-pages 10

# Generate embeddings
python scripts/generate_embeddings.py --workers 4

# Monitor progress
python scripts/monitor_progress.py --interval 2
```

## Python API Usage

```python
from scripts.recommendation_engine import MovieRecommendationEngine

# Initialize
engine = MovieRecommendationEngine()

# Get recommendations by movie ID
recs = engine.recommend_by_movie_id(123, limit=10, distance_metric='cosine')

# Search movies
results = engine.search_movies("action thriller", limit=20)

# Get trending movies
trending = engine.get_trending_movies(limit=20, min_year=2020)

# Get recommendations by genres
genre_recs = engine.recommend_by_genres(['Action', 'Sci-Fi'], limit=10)

# Find similar movies by text description
text_recs = engine.get_similar_by_text("A movie about space exploration", limit=10)

# Always close when done
engine.close()
```

## Adding New Features

### Adding a New Query

1. Add method to `database/queries.py`:
```python
def get_movies_by_director(self, session, director_name: str, limit: int = 10):
    """Get movies by director name"""
    return session.query(Movie).filter(
        Movie.director == director_name
    ).limit(limit).all()
```

2. Add method to `scripts/recommendation_engine.py`:
```python
def get_movies_by_director(self, director_name: str, limit: int = 10) -> List[Dict]:
    """Get movies by director"""
    with self.db_manager.get_session() as session:
        movies = self.queries.get_movies_by_director(session, director_name, limit)
        return [self._movie_to_dict(m, session) for m in movies]
```

3. Use it:
```python
engine = MovieRecommendationEngine()
movies = engine.get_movies_by_director("Christopher Nolan", limit=10)
```

## Summary

The new structure provides:
- ✅ Clear separation between database and business logic
- ✅ Proper session management (no DetachedInstanceError)
- ✅ Reusable query layer
- ✅ Clean public API
- ✅ Easy to test and maintain
- ✅ Scalable architecture

