# 🚀 Quick Start Guide - YTS Movie Data Fetcher

## Step-by-Step Instructions

### 1️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 2️⃣ Test Database Connection

Before fetching data, verify your database is properly set up:

```bash
python test_db_connection.py
```

You should see:
```
✅ Database connection successful!

Checking tables...
✅ Table 'movies': exists
✅ Table 'genres': exists
✅ Table 'movie_genres': exists
✅ Table 'casts': exists
✅ Table 'movie_casts': exists
✅ Table 'torrents': exists
✅ Table 'movie_embeddings': exists

📊 Current movies in database: 0
```

If any tables are missing, run the SQL schema first:
```bash
psql -h 161.97.175.211 -U postgres -d postgres -f database.sql
```

### 3️⃣ Start Fetching Data

#### Option A: Test Run (Recommended First)
Fetch just 5 pages (~250 movies) to test:

```bash
python fetch_yts_data.py --max-pages 5
```

#### Option B: Full Run
Fetch all movies (~70,000+):

```bash
python fetch_yts_data.py
```

#### Option C: Custom Configuration
```bash
# Fetch 100 pages with 20 workers
python fetch_yts_data.py --max-pages 100 --workers 20 --batch-size 100
```

### 4️⃣ Monitor Progress (Optional)

Open a **second terminal** and run:

```bash
python monitor_progress.py
```

This will show real-time statistics:
- Total movies fetched
- Movies added in last 5 minutes
- Top genres
- Latest movies added
- Completion rate

Press `Ctrl+C` to stop monitoring.

## 📊 What Gets Fetched?

For each movie, the script fetches and stores:

1. **Movie Information**
   - Title, year, rating, runtime
   - Descriptions and synopsis
   - Images (cover, background, screenshots)
   - IMDB code, language, MPA rating
   - Like count, download count

2. **Genres**
   - All genres for each movie
   - Stored in normalized tables

3. **Cast Members**
   - Actor names
   - Character names
   - IMDB codes
   - Profile images

4. **Torrents**
   - Download URLs and hashes
   - Quality (720p, 1080p, 2160p)
   - Video codec, audio channels
   - File sizes
   - Seeds and peers count

## ⚡ Performance Tips

### For Maximum Speed:
```bash
# Use more workers (if you have good internet)
python fetch_yts_data.py --workers 24 --batch-size 100
```

### For Stability:
```bash
# Use fewer workers (if you get connection errors)
python fetch_yts_data.py --workers 8 --batch-size 50
```

### Expected Performance:
- **8 workers**: ~20-40 movies/second
- **16 workers**: ~40-80 movies/second
- **24 workers**: ~60-100 movies/second

### Time Estimates (for ~70,000 movies):
- **8 workers**: 30-60 minutes
- **16 workers**: 15-30 minutes
- **24 workers**: 10-20 minutes

## 🔄 Resume Interrupted Runs

If the script stops or crashes, just run it again:

```bash
python fetch_yts_data.py
```

The script uses `ON CONFLICT` clauses, so:
- ✅ Existing movies will be updated
- ✅ New movies will be inserted
- ✅ No duplicates will be created

## 🐛 Troubleshooting

### Problem: "Too many connections" error

**Solution**: Reduce workers
```bash
python fetch_yts_data.py --workers 4
```

### Problem: Very slow performance

**Possible causes**:
1. Slow internet connection
2. Database server is slow
3. Too many workers (CPU bottleneck)

**Solutions**:
- Check internet speed
- Try different worker counts (8, 12, 16)
- Monitor CPU usage

### Problem: API rate limiting

**Solution**: The script has built-in delays, but if you still get rate limited:
```bash
python fetch_yts_data.py --workers 4 --batch-size 25
```

### Problem: Database connection fails

**Check**:
1. Database credentials in `config.py`
2. Database server is running
3. Firewall allows connection to port 5432

## 📈 Monitoring During Fetch

### Terminal 1: Run the fetcher
```bash
python fetch_yts_data.py
```

### Terminal 2: Monitor progress
```bash
python monitor_progress.py
```

### Terminal 3: Check database directly
```bash
psql -h 161.97.175.211 -U postgres -d postgres

# Then run queries:
SELECT COUNT(*) FROM movies;
SELECT COUNT(*) FROM genres;
SELECT COUNT(*) FROM casts;
```

## 🎯 Example Workflow

```bash
# 1. Test database connection
python test_db_connection.py

# 2. Do a small test run
python fetch_yts_data.py --max-pages 5

# 3. Check results
python monitor_progress.py

# 4. If all looks good, run full fetch
python fetch_yts_data.py --workers 16

# 5. Monitor in another terminal
python monitor_progress.py --interval 10
```

## 📝 Command Reference

### fetch_yts_data.py
```bash
python fetch_yts_data.py [OPTIONS]

Options:
  --max-pages INT    Maximum pages to fetch (default: all)
  --batch-size INT   Movies per batch (default: 50)
  --workers INT      Number of parallel workers (default: CPU count × 2)
```

### monitor_progress.py
```bash
python monitor_progress.py [OPTIONS]

Options:
  --interval INT     Refresh interval in seconds (default: 5)
```

### test_db_connection.py
```bash
python test_db_connection.py
```

## 🎉 After Fetching

Once data is fetched, you can:

1. **Query the database**:
   ```sql
   -- Get top rated movies
   SELECT title, year, rating FROM movies ORDER BY rating DESC LIMIT 10;
   
   -- Get movies by genre
   SELECT m.title, m.year 
   FROM movies m
   JOIN movie_genres mg ON m.id = mg.movie_id
   JOIN genres g ON mg.genre_id = g.id
   WHERE g.name = 'Action'
   ORDER BY m.rating DESC;
   ```

2. **Build recommendation system**: Use the movie embeddings table

3. **Create API endpoints**: Query the data for your application

4. **Generate analytics**: Analyze trends, popular genres, etc.

## 💡 Pro Tips

1. **Start small**: Always test with `--max-pages 5` first
2. **Monitor resources**: Watch CPU and network usage
3. **Use tmux/screen**: For long-running fetches on remote servers
4. **Check logs**: The script logs all errors for debugging
5. **Backup database**: Before running full fetch, backup your DB

## 🆘 Need Help?

Check the logs for detailed error messages. The script logs:
- API request failures
- Database errors
- Processing statistics
- Final summary

Happy fetching! 🎬🚀

