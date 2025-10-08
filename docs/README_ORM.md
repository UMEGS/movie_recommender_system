# 🎬 YTS Movie Data Fetcher - ORM Edition

A high-performance, ORM-based movie data fetcher using SQLAlchemy, multiprocessing, and intelligent duplicate prevention.

## ✨ Features

- ✅ **SQLAlchemy ORM** - Type-safe database operations
- ✅ **Multiprocessing** - True parallel processing (40-80 movies/second)
- ✅ **Duplicate Prevention** - Multiple layers to avoid re-fetching
- ✅ **Connection Pooling** - Efficient database connection management
- ✅ **Centralized DB Logic** - All operations in `database/` module
- ✅ **Progress Tracking** - Real-time progress bars and monitoring
- ✅ **Automatic Relationships** - Handles genres, cast, torrents automatically
- ✅ **Resume Capability** - Safely restart interrupted fetches

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   YTS API                                │
│  /list_movies.json  |  /movie_details.json              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              fetch_yts_data.py                           │
│  • Collects movie IDs                                    │
│  • Checks for existing movies                            │
│  • Parallel processing with multiprocessing              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│           database/db.py (DatabaseManager)               │
│  • movie_exists() - Check duplicates                     │
│  • save_movie() - Save with relationships                │
│  • get_or_create_genre() - Manage genres                 │
│  • get_or_create_cast() - Manage cast                    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│         database/models.py (SQLAlchemy ORM)              │
│  Movie, Genre, Cast, Torrent, Relationships              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              PostgreSQL Database                         │
│  movies, genres, casts, torrents, relationships          │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `sqlalchemy` - ORM
- `psycopg2-binary` - PostgreSQL adapter
- `requests` - API calls
- `tqdm` - Progress bars

### 2. Test Database Connection

```bash
python test_db_connection.py
```

Expected output:
```
✅ Database connection successful!

Checking tables...
✅ Table 'movies': exists
✅ Table 'genres': exists
✅ Table 'casts': exists
✅ Table 'torrents': exists

📊 Database Statistics:
   Movies: 0
   Genres: 0
   Cast Members: 0
   Torrents: 0
```

### 3. Fetch Movies

#### Test Run (Recommended First)
```bash
python fetch_yts_data.py --max-pages 5
```

#### Full Run
```bash
python fetch_yts_data.py
```

#### Custom Configuration
```bash
python fetch_yts_data.py --workers 16 --batch-size 100
```

### 4. Monitor Progress (Optional)

In a separate terminal:
```bash
python monitor_progress.py
```

## 📊 How It Works

### Step 1: Collect Movie IDs
```python
# Fetches from /list_movies.json
movie_ids = collect_all_movie_ids(max_pages=None)
# Returns: [1, 2, 3, ..., 70613]
```

### Step 2: Check for Existing Movies
```python
# Before fetching details, check if movie exists
if db_manager.movie_exists(movie_id):
    results['skipped'] += 1
    continue  # Skip API call entirely
```

### Step 3: Fetch Details
```python
# Only fetch if movie doesn't exist
movie_data = fetch_movie_details(movie_id)
# Fetches from /movie_details.json with cast and images
```

### Step 4: Save to Database
```python
# Save using ORM - handles all relationships automatically
success, movie_id, message = db_manager.save_movie(movie_data)

# Saves:
# - Movie information
# - Genres (get or create)
# - Cast members (get or create)
# - Torrents
# - All relationships
```

## 🛡️ Duplicate Prevention

### Three Layers of Protection

#### Layer 1: Pre-fetch Check
```python
if db_manager.movie_exists(movie_id):
    continue  # Skip API call
```
**Benefit:** Saves API calls and processing time

#### Layer 2: Save-time Check
```python
existing_movie = session.query(Movie).filter_by(
    external_id=external_id
).first()

if existing_movie:
    return (True, existing_movie.id, "already_exists")
```
**Benefit:** Prevents duplicate inserts

#### Layer 3: Database Constraints
```sql
external_id INT UNIQUE
slug TEXT UNIQUE
```
**Benefit:** Database-level protection

## 📁 Project Structure

```
.
├── fetch_yts_data.py          # Main fetcher script
├── test_db_connection.py      # Test database connection
├── monitor_progress.py        # Real-time monitoring
│
├── database/
│   ├── models.py              # SQLAlchemy ORM models
│   ├── db.py                  # DatabaseManager class
│   └── config.py              # Database configuration
│
├── config.py                  # Application configuration
├── requirements.txt           # Python dependencies
│
└── Documentation/
    ├── ORM_IMPLEMENTATION.md  # ORM details
    ├── REFACTORING_SUMMARY.md # Changes summary
    ├── QUICK_START_GUIDE.md   # Quick start
    └── README_ORM.md          # This file
```

## 🎯 Key Components

### DatabaseManager (`database/db.py`)

Central hub for all database operations:

```python
from database.db import get_db_manager

db_manager = get_db_manager()

# Check if movie exists
if db_manager.movie_exists(12345):
    print("Movie exists!")

# Save movie with all relationships
success, movie_id, message = db_manager.save_movie(movie_data)

# Get statistics
stats = db_manager.get_stats()
print(f"Total movies: {stats['total_movies']}")

# Cleanup
db_manager.close_all()
```

### ORM Models (`database/models.py`)

SQLAlchemy models for all tables:

```python
from database.models import Movie, Genre, Cast, Torrent

# Models automatically handle:
# - Type validation
# - Relationships
# - Foreign keys
# - Cascade deletes
```

## 💡 Usage Examples

### Basic Fetch

```bash
# Fetch first 10 pages (~500 movies)
python fetch_yts_data.py --max-pages 10
```

Output:
```
============================================================
YTS Movie Data Fetcher Started
============================================================
Collecting movie IDs from YTS API...
Total movies available: 70613
Collected 500 movie IDs
Processing 500 movies in 10 batches
Using 16 parallel workers

Processing batches: 100%|████████| 10/10 [Success: 450, Skipped: 50, Failed: 0]

============================================================
YTS Movie Data Fetcher Completed
Total movies processed: 500
Successfully saved: 450
Skipped (already exist): 50
Failed: 0
Time elapsed: 12.34 seconds
Average speed: 36.45 movies/second
============================================================
```

### Resume Interrupted Fetch

If the script stops, just run it again:

```bash
python fetch_yts_data.py
```

**What happens:**
1. Collects all movie IDs from API
2. Checks which movies already exist in DB
3. Only fetches NEW movies
4. Skips existing movies (no duplicates)

### Monitor While Fetching

Terminal 1:
```bash
python fetch_yts_data.py --workers 16
```

Terminal 2:
```bash
python monitor_progress.py --interval 5
```

Monitor shows:
- Total movies in database
- Movies added in last 5 minutes
- Top genres
- Latest movies added
- Real-time statistics

## ⚙️ Configuration

### Command Line Arguments

```bash
python fetch_yts_data.py [OPTIONS]

Options:
  --max-pages INT    Maximum pages to fetch (default: all)
  --batch-size INT   Movies per batch (default: 50)
  --workers INT      Parallel workers (default: CPU count × 2)
```

### Database Configuration (`config.py`)

```python
DB_CONFIG = {
    "host": "your-host",
    "port": 5432,
    "user": "postgres",
    "password": "your-password",
    "dbname": "postgres"
}
```

### Connection Pool Settings

```python
# In your code
db_manager = get_db_manager(
    pool_size=10,      # Base pool size
    max_overflow=20    # Additional connections
)
```

## 🔍 Querying Data

### Using ORM

```python
from database.db import get_db_manager
from database.models import Movie, Genre
from sqlalchemy import desc

db_manager = get_db_manager()

with db_manager.get_session() as session:
    # Get top rated movies
    top_movies = session.query(Movie).filter(
        Movie.rating >= 8.0
    ).order_by(desc(Movie.rating)).limit(10).all()
    
    for movie in top_movies:
        print(f"{movie.title} ({movie.year}) - {movie.rating}⭐")
    
    # Get movies by genre
    action_movies = session.query(Movie).join(
        Movie.genres
    ).filter(
        Genre.name == 'Action'
    ).all()
    
    # Get movie with relationships
    movie = session.query(Movie).filter_by(external_id=12345).first()
    print(f"Genres: {[g.name for g in movie.genres]}")
    print(f"Cast: {[c.name for c in movie.casts]}")
    print(f"Torrents: {len(movie.torrents)}")
```

## 📈 Performance

### Speed Comparison

| Workers | Speed (movies/sec) | Time for 70K movies |
|---------|-------------------|---------------------|
| 4       | 15-25             | 45-75 minutes       |
| 8       | 25-40             | 30-45 minutes       |
| 16      | 40-80             | 15-30 minutes       |
| 24      | 60-100            | 12-20 minutes       |

### Optimization Tips

1. **More workers for I/O-bound tasks:**
   ```bash
   python fetch_yts_data.py --workers 20
   ```

2. **Larger batches for fewer DB connections:**
   ```bash
   python fetch_yts_data.py --batch-size 100
   ```

3. **Skip existing movies automatically:**
   - First run: Fetches all
   - Subsequent runs: Only new movies

## 🐛 Troubleshooting

### Connection Pool Exhausted

**Error:** `QueuePool limit exceeded`

**Solution:** Reduce workers or increase pool size
```bash
python fetch_yts_data.py --workers 8
```

### Slow Performance

**Check:**
1. Internet connection speed
2. Database server performance
3. CPU usage

**Solution:** Adjust worker count
```bash
# Try different values
python fetch_yts_data.py --workers 12
```

### API Rate Limiting

**Solution:** Built-in delays (0.1s per movie)

If still rate limited:
```bash
python fetch_yts_data.py --workers 4 --batch-size 25
```

## 📚 Documentation

- **ORM_IMPLEMENTATION.md** - Detailed ORM documentation
- **REFACTORING_SUMMARY.md** - What changed and why
- **QUICK_START_GUIDE.md** - Step-by-step guide
- **FETCH_DATA_README.md** - Original documentation

## 🎉 Summary

### What You Get

✅ **ORM-based** - Type-safe, maintainable code  
✅ **No duplicates** - Intelligent checking at multiple layers  
✅ **Fast** - Multiprocessing with 40-80 movies/second  
✅ **Resumable** - Safely restart interrupted fetches  
✅ **Monitored** - Real-time progress tracking  
✅ **Complete** - Fetches movies, genres, cast, torrents  
✅ **Production-ready** - Connection pooling, error handling  

### Quick Commands

```bash
# Test
python test_db_connection.py

# Fetch (test)
python fetch_yts_data.py --max-pages 5

# Fetch (full)
python fetch_yts_data.py

# Monitor
python monitor_progress.py
```

Happy fetching! 🚀🎬

