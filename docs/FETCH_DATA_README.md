# YTS Movie Data Fetcher

A high-performance multiprocessing script to fetch movie data from YTS API and store it in PostgreSQL database.

## Features

- ✅ **Multiprocessing**: Uses Python's ProcessPoolExecutor for true parallel processing
- ✅ **Fast**: Processes multiple movies simultaneously, bypassing Python's GIL
- ✅ **Complete Data**: Fetches movies, genres, cast, and torrents
- ✅ **Progress Tracking**: Real-time progress bars with tqdm
- ✅ **Error Handling**: Robust error handling and logging
- ✅ **Rate Limiting**: Built-in delays to avoid API rate limits
- ✅ **Resumable**: Uses ON CONFLICT to update existing movies

## Prerequisites

1. **Database Setup**: Make sure your PostgreSQL database is set up with the schema from `database.sql`

2. **Install Dependencies**:
```bash
pip install requests psycopg2-binary tqdm
```

## Usage

### Basic Usage (Fetch All Movies)

```bash
python fetch_yts_data.py
```

This will:
- Fetch all available movies from YTS API
- Use CPU count × 2 workers for parallel processing
- Process movies in batches of 50
- Save everything to the database

### Fetch Limited Pages (For Testing)

```bash
# Fetch only first 10 pages (~500 movies)
python fetch_yts_data.py --max-pages 10
```

### Custom Configuration

```bash
# Custom workers and batch size
python fetch_yts_data.py --workers 16 --batch-size 100

# Fetch 50 pages with 20 workers
python fetch_yts_data.py --max-pages 50 --workers 20 --batch-size 50
```

## Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--max-pages` | Maximum number of pages to fetch from list API | All pages |
| `--batch-size` | Number of movies to process in each batch | 50 |
| `--workers` | Number of parallel workers | CPU count × 2 |

## How It Works

1. **Collect Movie IDs**: 
   - Fetches movie list from `/list_movies.json` API
   - Collects all movie IDs (or up to max-pages)

2. **Parallel Processing**:
   - Splits movie IDs into batches
   - Each worker process handles one batch at a time
   - For each movie: fetches detailed data from `/movie_details.json`

3. **Database Storage**:
   - Saves movie information to `movies` table
   - Saves genres to `genres` and links via `movie_genres`
   - Saves cast to `casts` and links via `movie_casts`
   - Saves torrents to `torrents` table
   - Uses `ON CONFLICT` to update existing records

## Performance

- **Single-threaded**: ~2-5 movies/second
- **Multiprocessing (8 workers)**: ~20-40 movies/second
- **Multiprocessing (16 workers)**: ~40-80 movies/second

For ~70,000 movies:
- With 16 workers: ~15-30 minutes
- With 8 workers: ~30-60 minutes

## Database Schema

The script populates these tables:
- `movies` - Main movie information
- `genres` - Genre names
- `movie_genres` - Movie-genre relationships
- `casts` - Cast member information
- `movie_casts` - Movie-cast relationships with character names
- `torrents` - Torrent download information

## Error Handling

- Failed API requests are logged and counted
- Database errors are caught and rolled back
- Progress continues even if individual movies fail
- Final summary shows success/failure counts

## Logging

The script logs:
- Progress information
- Errors and warnings
- Final statistics (total processed, success rate, time elapsed)

## Example Output

```
============================================================
YTS Movie Data Fetcher Started
============================================================
2025-10-08 - MainProcess - INFO - Total movies available: 70613
2025-10-08 - MainProcess - INFO - Collected 70613 movie IDs
2025-10-08 - MainProcess - INFO - Processing 70613 movies in 1413 batches
2025-10-08 - MainProcess - INFO - Using 16 parallel workers

Processing batches: 100%|████████████| 1413/1413 [25:30<00:00, Success: 69845, Failed: 768]

============================================================
YTS Movie Data Fetcher Completed
Total movies processed: 70613
Successfully saved: 69845
Failed: 768
Time elapsed: 1530.45 seconds
Average speed: 46.14 movies/second
============================================================
```

## Tips for Maximum Speed

1. **Increase Workers**: Use more workers if you have good internet and CPU
   ```bash
   python fetch_yts_data.py --workers 20
   ```

2. **Larger Batches**: Increase batch size for fewer database connections
   ```bash
   python fetch_yts_data.py --batch-size 100
   ```

3. **Database Connection Pool**: The script uses connection pooling automatically

4. **Network**: Ensure stable, fast internet connection

5. **Test First**: Run with `--max-pages 5` to test before full run

## Troubleshooting

### "Too many connections" error
- Reduce `--workers` parameter
- Check database max_connections setting

### Slow performance
- Check internet connection speed
- Reduce workers if CPU is bottleneck
- Increase workers if network is bottleneck

### API rate limiting
- The script includes built-in delays (0.1-0.2s)
- If you get rate limited, reduce workers

## Resume Interrupted Runs

The script uses `ON CONFLICT` clauses, so you can safely re-run it:
- Existing movies will be updated
- New movies will be inserted
- No duplicates will be created

Just run the same command again!

