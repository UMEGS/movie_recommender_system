# ORM Implementation - YTS Movie Data Fetcher

## Overview

The YTS Movie Data Fetcher has been refactored to use **SQLAlchemy ORM** for all database operations. This provides better code organization, type safety, and maintainability.

## Architecture

### Database Layer (`database/`)

All database operations are now centralized in the `database/` module:

```
database/
├── models.py      # SQLAlchemy ORM models
├── db.py          # Database manager and operations
└── config.py      # Database configuration
```

### Key Components

#### 1. **Models (`database/models.py`)**

Defines SQLAlchemy ORM models for all tables:

- `Movie` - Main movie information
- `Genre` - Genre names
- `Cast` - Cast member information
- `Torrent` - Torrent download data
- `MovieGenre` - Movie-genre relationships
- `MovieCast` - Movie-cast relationships with character names
- `MovieEmbedding` - Vector embeddings for recommendations

**Example Model:**
```python
class Movie(Base):
    __tablename__ = "movies"
    
    id = Column(BigInteger, primary_key=True)
    external_id = Column(Integer, unique=True, nullable=False)
    title = Column(Text, nullable=False)
    rating = Column(Numeric(3, 1))
    # ... more fields
    
    # Relationships
    genres = relationship("Genre", secondary="movie_genres")
    casts = relationship("Cast", secondary="movie_casts")
    torrents = relationship("Torrent", cascade="all, delete-orphan")
```

#### 2. **Database Manager (`database/db.py`)**

Centralized database operations with connection pooling:

**Key Methods:**

- `get_session()` - Context manager for database sessions
- `movie_exists(external_id)` - Check if movie already exists
- `get_or_create_genre(session, genre_name)` - Get or create genre
- `get_or_create_cast(session, cast_data)` - Get or create cast member
- `save_movie(movie_data)` - Save complete movie with all relationships
- `get_stats()` - Get database statistics

**Example Usage:**
```python
from database.db import get_db_manager

db_manager = get_db_manager()

# Check if movie exists
if db_manager.movie_exists(12345):
    print("Movie already exists!")

# Save movie
success, movie_id, message = db_manager.save_movie(movie_data)
if success:
    print(f"Movie saved with ID: {movie_id}")
```

#### 3. **Fetch Script (`fetch_yts_data.py`)**

Updated to use ORM for all database operations:

**Key Changes:**
- ✅ No raw SQL queries
- ✅ Uses `DatabaseManager` for all operations
- ✅ Checks for existing movies before fetching
- ✅ Each process creates its own database manager
- ✅ Proper connection cleanup

**Process Flow:**
```python
def process_movie_batch(movie_ids_batch):
    # Create DB manager for this process
    db_manager = get_db_manager(pool_size=2, max_overflow=5)
    
    for movie_id in movie_ids_batch:
        # Check if exists (skip if already in DB)
        if db_manager.movie_exists(movie_id):
            continue
        
        # Fetch from API
        movie_data = fetch_movie_details(movie_id)
        
        # Save using ORM
        success, movie_id, message = db_manager.save_movie(movie_data)
    
    # Cleanup
    db_manager.close_all()
```

## Benefits of ORM Approach

### 1. **No Duplicate Inserts**
- `movie_exists()` checks before fetching
- `get_or_create_*()` methods prevent duplicates
- Unique constraints on `external_id` and `slug`

### 2. **Centralized Database Logic**
- All DB operations in `database/db.py`
- Easy to maintain and test
- Consistent error handling

### 3. **Type Safety**
- SQLAlchemy models provide type hints
- IDE autocomplete support
- Catch errors at development time

### 4. **Relationship Management**
- Automatic handling of foreign keys
- Cascade deletes configured
- Easy to query related data

### 5. **Connection Pooling**
- Efficient connection reuse
- Configurable pool size
- Automatic connection cleanup

### 6. **Better Error Handling**
- Session-level transactions
- Automatic rollback on errors
- Detailed error messages

## How Duplicate Prevention Works

### 1. **Before Fetching from API**
```python
if db_manager.movie_exists(movie_id):
    results['skipped'] += 1
    continue  # Skip API call entirely
```

### 2. **During Save Operation**
```python
def save_movie(self, movie_data):
    existing_movie = session.query(Movie).filter_by(
        external_id=external_id
    ).first()
    
    if existing_movie:
        return (True, existing_movie.id, "already_exists")
    
    # Create new movie...
```

### 3. **Database Constraints**
```sql
-- In database schema
external_id INT UNIQUE
slug TEXT UNIQUE
```

## Usage Examples

### Basic Usage

```bash
# Test database connection
python test_db_connection.py

# Fetch movies (skips existing ones automatically)
python fetch_yts_data.py --max-pages 10

# Monitor progress
python monitor_progress.py
```

### Programmatic Usage

```python
from database.db import get_db_manager

# Initialize
db_manager = get_db_manager()

# Check if movie exists
if not db_manager.movie_exists(12345):
    # Fetch and save
    movie_data = fetch_movie_details(12345)
    success, movie_id, message = db_manager.save_movie(movie_data)
    
    if success:
        print(f"Saved movie {movie_id}")
    else:
        print(f"Error: {message}")

# Get statistics
stats = db_manager.get_stats()
print(f"Total movies: {stats['total_movies']}")

# Cleanup
db_manager.close_all()
```

### Query Examples

```python
from database.db import get_db_manager
from database.models import Movie, Genre

db_manager = get_db_manager()

with db_manager.get_session() as session:
    # Get all action movies
    action_genre = session.query(Genre).filter_by(name='Action').first()
    action_movies = action_genre.movies
    
    # Get movies by rating
    top_movies = session.query(Movie).filter(
        Movie.rating >= 8.0
    ).order_by(Movie.rating.desc()).limit(10).all()
    
    # Get movie with all relationships
    movie = session.query(Movie).filter_by(external_id=12345).first()
    print(f"Title: {movie.title}")
    print(f"Genres: {[g.name for g in movie.genres]}")
    print(f"Cast: {[c.name for c in movie.casts]}")
    print(f"Torrents: {len(movie.torrents)}")
```

## Performance Considerations

### Connection Pooling

```python
# Main process
db_manager = get_db_manager(pool_size=10, max_overflow=20)

# Worker processes (smaller pools)
db_manager = get_db_manager(pool_size=2, max_overflow=5)
```

### Batch Processing

The fetcher processes movies in batches:
- Each batch is handled by a separate process
- Each process has its own connection pool
- Connections are cleaned up after batch completion

### Skipping Existing Movies

```python
# Fast check before API call
if db_manager.movie_exists(movie_id):
    continue  # No API call, no processing
```

This significantly speeds up re-runs:
- First run: Fetches all movies
- Subsequent runs: Only fetches new movies

## Migration from Raw SQL

### Before (Raw SQL)
```python
cursor.execute("""
    INSERT INTO movies (external_id, title, ...)
    VALUES (%s, %s, ...)
    ON CONFLICT (external_id) DO UPDATE ...
""", (movie_id, title, ...))
```

### After (ORM)
```python
success, movie_id, message = db_manager.save_movie(movie_data)
```

## Testing

### Test Database Connection
```bash
python test_db_connection.py
```

Expected output:
```
✅ Database connection successful!

Checking tables...
✅ Table 'movies': exists
✅ Table 'genres': exists
...

📊 Database Statistics:
   Movies: 1,234
   Genres: 25
   Cast Members: 5,678
   Torrents: 3,456
```

## Troubleshooting

### Issue: "Movie already exists" but want to update

**Solution:** The current implementation skips existing movies. To force updates, modify `save_movie()` in `database/db.py` to update instead of skip.

### Issue: Connection pool exhausted

**Solution:** Reduce number of workers or increase pool size:
```bash
python fetch_yts_data.py --workers 4
```

### Issue: Slow queries

**Solution:** Ensure database indexes are created (from `database.sql`):
```sql
CREATE INDEX idx_movies_search ON movies USING gin(search_vector);
CREATE INDEX idx_movie_embeddings_vector ON movie_embeddings ...
```

## Summary

The ORM implementation provides:

✅ **No duplicate inserts** - Checks before fetching and saving  
✅ **Centralized database logic** - All operations in `database/db.py`  
✅ **Type safety** - SQLAlchemy models with proper types  
✅ **Better error handling** - Session-level transactions  
✅ **Connection pooling** - Efficient resource usage  
✅ **Relationship management** - Automatic foreign key handling  
✅ **Easier maintenance** - Clean, organized code  

All database operations now go through the ORM layer, making the codebase more maintainable and robust!

