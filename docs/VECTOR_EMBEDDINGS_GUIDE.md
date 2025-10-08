# 🎯 Vector Embeddings & Recommendation System Guide

## Overview

This system uses **PostgreSQL with pgvector** as a vector database and **Ollama with nomic-embed-text** for generating embeddings. This enables semantic similarity search for movie recommendations.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Movie Data                             │
│  Title + Genres + Description + Cast + Metadata         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Ollama (localhost:11434)                    │
│           Model: nomic-embed-text                        │
│           Generates 768-dimensional vectors              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│         PostgreSQL with pgvector Extension               │
│  movie_embeddings table with VECTOR(768) column         │
│  Indexes: ivfflat for fast similarity search            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│           Recommendation Engine                          │
│  • Cosine similarity search                              │
│  • L2 distance search                                    │
│  • Text-based search                                     │
└─────────────────────────────────────────────────────────┘
```

## Setup

### 1. Install Ollama

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama server
ollama serve
```

### 2. Pull nomic-embed-text Model

```bash
ollama pull nomic-embed-text
```

Verify it's installed:
```bash
ollama list
```

### 3. Configure Environment

Edit `.env` file:

```bash
# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_TIMEOUT=120

# Embedding Configuration
EMBEDDING_DIMENSION=768
EMBEDDING_BATCH_SIZE=100
```

### 4. Verify Ollama is Running

```bash
curl http://localhost:11434/api/tags
```

Should return list of available models.

## Generating Embeddings

### Basic Usage

```bash
# Generate embeddings for all movies without embeddings
python generate_embeddings.py
```

### Advanced Options

```bash
# Custom batch size and workers
python generate_embeddings.py --batch-size 50 --workers 8

# Force regenerate all embeddings
python generate_embeddings.py --force

# Use settings from .env
python generate_embeddings.py
```

### What Gets Embedded?

For each movie, the system creates a text representation combining:

1. **Title** - Movie name
2. **Year** - Release year
3. **Genres** - All genres (Action, Drama, etc.)
4. **Description** - Full description or intro
5. **Cast** - Top 5 cast members
6. **Language** - Movie language
7. **Rating** - IMDb rating

Example:
```
Title: Inception | Year: 2010 | Genres: Action, Sci-Fi, Thriller | 
Description: A thief who steals corporate secrets... | 
Cast: Leonardo DiCaprio, Joseph Gordon-Levitt, Ellen Page | 
Language: en | Rating: 8.8/10
```

This text is sent to Ollama's nomic-embed-text model, which returns a 768-dimensional vector.

### Performance

- **Speed**: ~2-5 embeddings/second (depends on Ollama performance)
- **For 70,000 movies**: ~4-10 hours
- **Parallel processing**: Uses multiprocessing for efficiency

### Progress Monitoring

The script shows real-time progress:

```
============================================================
Movie Embedding Generator Started (Ollama)
============================================================
Using Ollama at: http://localhost:11434
Model: nomic-embed-text
Embedding dimension: 768
Found 70613 movies without embeddings
Processing 70613 movies in 707 batches
Using 8 parallel workers

Generating embeddings: 100%|████████| 707/707 [Success: 69845, Skipped: 0, Failed: 768]

============================================================
Movie Embedding Generator Completed
Total movies processed: 70613
Successfully generated: 69845
Skipped (already exist): 0
Failed: 768
Time elapsed: 14523.45 seconds
Average speed: 4.81 embeddings/second
============================================================
```

## Using the Recommendation Engine

### Python API

```python
from scripts.recommendation_engine import MovieRecommendationEngine

# Initialize engine
engine = MovieRecommendationEngine()

# Get recommendations by movie ID
recommendations = engine.recommend_by_movie_id(movie_id=123, limit=10)

# Get recommendations by external ID (YTS ID)
recommendations = engine.recommend_by_external_id(external_id=12345, limit=10)

# Search movies by title
movies = engine.search_movies("inception", limit=10)

# Find movies similar to text description
movies = engine.get_similar_by_text(
    "A sci-fi thriller about dreams and reality",
    limit=10
)

# Get recommendations by genres
movies = engine.recommend_by_genres(
    genres=["Action", "Sci-Fi"],
    limit=10,
    min_rating=7.0
)

# Get trending movies
trending = engine.get_trending_movies(limit=20, min_year=2020)

# Get top rated movies
top_rated = engine.get_top_rated_movies(limit=20)

# Close connections
engine.close()
```

### Command Line Interface

```bash
# Get recommendations for a movie
python recommendation_engine.py --movie-id 123 --limit 10

# Get recommendations by external ID
python recommendation_engine.py --external-id 12345 --limit 10

# Search movies
python recommendation_engine.py --search "inception" --limit 10

# Find similar movies by text
python recommendation_engine.py --text "sci-fi thriller about time travel" --limit 10

# Get movies by genres
python recommendation_engine.py --genres Action Sci-Fi --limit 10

# Get trending movies
python recommendation_engine.py --trending --limit 20

# Get top rated movies
python recommendation_engine.py --top-rated --limit 20
```

### Example Output

```bash
$ python recommendation_engine.py --external-id 12345 --limit 5

🎬 Recommendations for external ID 12345:

Base movie: Inception (2010)
------------------------------------------------------------
1. Interstellar (2014) - ⭐ 8.6
   Genres: Adventure, Drama, Sci-Fi
   Similarity: 0.892

2. The Matrix (1999) - ⭐ 8.7
   Genres: Action, Sci-Fi
   Similarity: 0.875

3. Shutter Island (2010) - ⭐ 8.2
   Genres: Mystery, Thriller
   Similarity: 0.854

4. The Prestige (2006) - ⭐ 8.5
   Genres: Drama, Mystery, Sci-Fi
   Similarity: 0.847

5. Memento (2000) - ⭐ 8.4
   Genres: Mystery, Thriller
   Similarity: 0.839
```

## How Vector Similarity Works

### 1. Cosine Similarity (Default)

Measures the cosine of the angle between two vectors:
- **Range**: 0 to 1 (1 = identical, 0 = completely different)
- **Best for**: Semantic similarity
- **PostgreSQL operator**: `<=>`

```sql
SELECT * FROM movies m
JOIN movie_embeddings me ON m.id = me.movie_id
ORDER BY me.embedding <=> '[0.1, 0.2, ...]' ASC
LIMIT 10;
```

### 2. L2 Distance (Euclidean)

Measures straight-line distance between vectors:
- **Range**: 0 to ∞ (0 = identical, larger = more different)
- **Best for**: Exact matching
- **PostgreSQL operator**: `<->`

### 3. Inner Product

Measures dot product of vectors:
- **Range**: -∞ to ∞
- **Best for**: Magnitude-aware similarity
- **PostgreSQL operator**: `<#>`

## Database Schema

### movie_embeddings Table

```sql
CREATE TABLE movie_embeddings (
    movie_id BIGINT PRIMARY KEY REFERENCES movies(id) ON DELETE CASCADE,
    embedding VECTOR(768)  -- 768 dimensions for nomic-embed-text
);
```

### Indexes for Fast Search

```sql
-- L2 distance index
CREATE INDEX idx_movie_embeddings_vector
ON movie_embeddings
USING ivfflat (embedding vector_l2_ops)
WITH (lists = 100);

-- Cosine similarity index
CREATE INDEX idx_movie_embeddings_cosine
ON movie_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Note**: The `lists` parameter affects index performance:
- Smaller values (50-100): Faster indexing, slower queries
- Larger values (200-500): Slower indexing, faster queries
- Rule of thumb: `lists = sqrt(total_rows)`

## Configuration (.env)

All settings are in `.env` file:

```bash
# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_TIMEOUT=120

# Embedding Configuration
EMBEDDING_DIMENSION=768
EMBEDDING_BATCH_SIZE=100

# Multiprocessing
MAX_WORKERS=16
```

## Troubleshooting

### Ollama Not Running

**Error**: `Cannot connect to Ollama at http://localhost:11434`

**Solution**:
```bash
# Start Ollama
ollama serve

# Or check if it's running
ps aux | grep ollama
```

### Model Not Found

**Error**: `Model 'nomic-embed-text' not found`

**Solution**:
```bash
ollama pull nomic-embed-text
ollama list  # Verify it's installed
```

### Slow Embedding Generation

**Causes**:
1. Ollama running on CPU (no GPU)
2. Too many parallel workers
3. Large batch sizes

**Solutions**:
```bash
# Reduce workers
python generate_embeddings.py --workers 4

# Reduce batch size
python generate_embeddings.py --batch-size 50

# Check Ollama performance
ollama ps
```

### Out of Memory

**Solution**: Reduce batch size and workers:
```bash
python generate_embeddings.py --batch-size 25 --workers 2
```

### Database Connection Issues

**Error**: `Too many connections`

**Solution**: Reduce workers in `.env`:
```bash
MAX_WORKERS=4
```

## Performance Optimization

### 1. GPU Acceleration

If you have a GPU, Ollama will automatically use it:
```bash
# Check GPU usage
nvidia-smi  # For NVIDIA GPUs
```

### 2. Batch Processing

Larger batches = fewer DB connections:
```bash
python generate_embeddings.py --batch-size 200
```

### 3. Parallel Workers

More workers = faster processing (if you have resources):
```bash
python generate_embeddings.py --workers 16
```

### 4. Resume Capability

If interrupted, just run again:
```bash
python generate_embeddings.py
# Automatically skips movies that already have embeddings
```

## Integration with Your App

### Flask Example

```python
from flask import Flask, jsonify, request
from scripts.recommendation_engine import MovieRecommendationEngine

app = Flask(__name__)
engine = MovieRecommendationEngine()

@app.route('/api/recommendations/<int:movie_id>')
def get_recommendations(movie_id):
    limit = request.args.get('limit', 10, type=int)
    recommendations = engine.recommend_by_movie_id(movie_id, limit)
    return jsonify(recommendations)

@app.route('/api/search')
def search_movies():
    query = request.args.get('q', '')
    limit = request.args.get('limit', 10, type=int)
    results = engine.search_movies(query, limit)
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
```

## Next Steps

1. ✅ Install and start Ollama
2. ✅ Pull nomic-embed-text model
3. ✅ Configure `.env` file
4. ✅ Generate embeddings for all movies
5. ✅ Test recommendation engine
6. ✅ Integrate into your application

## Summary

✅ **Ollama** - Local embedding generation  
✅ **nomic-embed-text** - 768-dimensional embeddings  
✅ **PostgreSQL + pgvector** - Vector database  
✅ **Multiprocessing** - Fast parallel generation  
✅ **Multiple search methods** - Cosine, L2, text-based  
✅ **Resume capability** - Skip existing embeddings  
✅ **Configuration via .env** - Easy customization  

Your recommendation system is ready! 🚀🎬

