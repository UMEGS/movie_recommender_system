# Ollama Batch Inference Guide

## Overview

Ollama's embedding API **does not support true batch inference** (multiple texts in one request), but you can achieve high throughput using **concurrent requests**.

## Ollama API Limitations

### ❌ What Doesn't Work

```python
# This won't work - Ollama doesn't support batch inputs
response = requests.post(
    "http://localhost:11434/api/embeddings",
    json={
        "model": "nomic-embed-text",
        "input": ["text1", "text2", "text3"]  # ❌ Not supported
    }
)
```

### ✅ What Works

```python
# Single text per request
response = requests.post(
    "http://localhost:11434/api/embeddings",
    json={
        "model": "nomic-embed-text",
        "prompt": "single text here"  # ✅ Supported
    }
)
```

## Batch Processing Strategies

### 1. Sequential Processing (Slowest)

**Current basic approach:**

```python
for movie in movies:
    response = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": OLLAMA_EMBEDDING_MODEL, "prompt": text}
    )
    embedding = response.json()['embedding']
```

**Performance:**
- ⏱️ ~1-2 seconds per embedding
- 📊 ~30-60 embeddings/minute
- 🐌 Very slow for large datasets

### 2. Multiprocessing (Current Implementation)

**Your current approach in `generate_embeddings.py`:**

```python
from multiprocessing import Pool

def process_batch(batch):
    for movie in batch:
        # Each process handles multiple movies
        response = requests.post(...)

with Pool(processes=workers) as pool:
    pool.map(process_batch, batches)
```

**Performance:**
- ⏱️ ~0.2-0.5 seconds per embedding (with 10 workers)
- 📊 ~120-300 embeddings/minute
- ✅ Good for CPU-bound parallelism

**Pros:**
- ✅ True parallelism (bypasses GIL)
- ✅ Works well with multiple CPU cores
- ✅ Already implemented

**Cons:**
- ❌ Higher memory usage (multiple processes)
- ❌ More complex state management
- ❌ Overhead from process creation

### 3. Async/Await (Recommended for I/O)

**New approach in `generate_embeddings_async.py`:**

```python
import asyncio
import aiohttp

async def generate_embedding(session, text):
    async with session.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": OLLAMA_EMBEDDING_MODEL, "prompt": text}
    ) as response:
        data = await response.json()
        return data['embedding']

async def generate_batch(movies):
    async with aiohttp.ClientSession() as session:
        tasks = [generate_embedding(session, text) for text in texts]
        return await asyncio.gather(*tasks)
```

**Performance:**
- ⏱️ ~0.1-0.3 seconds per embedding (with 10 concurrent)
- 📊 ~200-600 embeddings/minute
- 🚀 Best for I/O-bound operations

**Pros:**
- ✅ Lower memory usage (single process)
- ✅ Better for I/O-bound tasks
- ✅ Simpler state management
- ✅ More efficient resource usage

**Cons:**
- ❌ Doesn't bypass GIL (but doesn't matter for I/O)
- ❌ Requires async/await syntax

### 4. Threading (Alternative)

```python
from concurrent.futures import ThreadPoolExecutor

def generate_embedding(text):
    response = requests.post(...)
    return response.json()['embedding']

with ThreadPoolExecutor(max_workers=10) as executor:
    embeddings = list(executor.map(generate_embedding, texts))
```

**Performance:**
- ⏱️ ~0.2-0.4 seconds per embedding
- 📊 ~150-300 embeddings/minute
- ✅ Good middle ground

**Pros:**
- ✅ Simpler than multiprocessing
- ✅ Lower memory usage
- ✅ Works with regular functions

**Cons:**
- ❌ GIL limitations (but OK for I/O)
- ❌ Not as efficient as async for pure I/O

## Performance Comparison

| Method | Speed | Memory | Complexity | Best For |
|--------|-------|--------|------------|----------|
| Sequential | 🐌 30-60/min | ✅ Low | ✅ Simple | Small datasets |
| Multiprocessing | ⚡ 120-300/min | ❌ High | ⚠️ Medium | CPU-bound |
| Async/Await | 🚀 200-600/min | ✅ Low | ⚠️ Medium | I/O-bound |
| Threading | ⚡ 150-300/min | ✅ Low | ✅ Simple | Mixed workload |

## Usage Examples

### Current Multiprocessing Version

```bash
# Your current implementation
python scripts/generate_embeddings.py --workers 10 --batch-size 100
```

### New Async Version

```bash
# Install aiohttp first
pip install aiohttp

# Run async version
python scripts/generate_embeddings_async.py --concurrent 10 --skip-existing

# Process limited number
python scripts/generate_embeddings_async.py --concurrent 20 --limit 100
```

### Comparison Test

```bash
# Test 100 movies with multiprocessing
time python scripts/generate_embeddings.py --workers 10 --limit 100

# Test 100 movies with async
time python scripts/generate_embeddings_async.py --concurrent 10 --limit 100
```

## Optimal Settings

### For Ollama on Local Machine

**CPU-based (no GPU):**
```bash
# Multiprocessing
python scripts/generate_embeddings.py --workers 4 --batch-size 50

# Async
python scripts/generate_embeddings_async.py --concurrent 8
```

**GPU-based:**
```bash
# Multiprocessing
python scripts/generate_embeddings.py --workers 8 --batch-size 100

# Async
python scripts/generate_embeddings_async.py --concurrent 15
```

### For Ollama on Remote Server

```bash
# Higher concurrency for network I/O
python scripts/generate_embeddings_async.py --concurrent 20
```

## Monitoring Performance

### Check Ollama Resource Usage

```bash
# Monitor Ollama
watch -n 1 'ps aux | grep ollama'

# Check GPU usage (if using GPU)
watch -n 1 nvidia-smi
```

### Benchmark Your Setup

```python
import time
import requests

def benchmark(num_requests=10, concurrent=1):
    start = time.time()
    
    # Your benchmark code here
    
    elapsed = time.time() - start
    rate = num_requests / elapsed
    print(f"Rate: {rate:.2f} embeddings/second")
    print(f"Time per embedding: {elapsed/num_requests:.3f} seconds")
```

## Best Practices

### 1. Start Conservative

```bash
# Start with low concurrency
python scripts/generate_embeddings_async.py --concurrent 5

# Gradually increase
python scripts/generate_embeddings_async.py --concurrent 10
python scripts/generate_embeddings_async.py --concurrent 15
```

### 2. Monitor System Resources

- Watch CPU usage
- Watch memory usage
- Watch Ollama logs
- Check for errors/timeouts

### 3. Handle Failures Gracefully

Both implementations include:
- ✅ Timeout handling
- ✅ Error logging
- ✅ Retry logic (can be added)
- ✅ Progress tracking

### 4. Use Appropriate Batch Sizes

```python
# For multiprocessing
batch_size = total_movies // (workers * 2)  # 2x workers

# For async
concurrent = 10-20  # Based on system capacity
```

## Recommendations

### For Your Use Case (YTS Movies)

**Current Status:**
- ✅ Multiprocessing works well
- ✅ Already implemented
- ✅ Good performance

**Consider Async If:**
- 🔄 You want lower memory usage
- 🔄 You're processing very large datasets
- 🔄 You want simpler code
- 🔄 Ollama is on a remote server

**Stick with Multiprocessing If:**
- ✅ Current performance is acceptable
- ✅ You have plenty of RAM
- ✅ You prefer the current implementation

### Hybrid Approach

You can also combine both:

```python
# Use multiprocessing for CPU-bound tasks
# Use async within each process for I/O

def worker_process(batch):
    asyncio.run(process_batch_async(batch))

with Pool(processes=4) as pool:
    pool.map(worker_process, batches)
```

## Future Improvements

### 1. Add Retry Logic

```python
async def generate_embedding_with_retry(session, text, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await generate_embedding(session, text)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### 2. Add Rate Limiting

```python
from asyncio import Semaphore

semaphore = Semaphore(10)  # Max 10 concurrent requests

async def generate_embedding(session, text):
    async with semaphore:
        # Your code here
```

### 3. Add Caching

```python
# Cache embeddings to avoid regeneration
cache = {}

def get_or_generate_embedding(text):
    if text in cache:
        return cache[text]
    embedding = generate_embedding(text)
    cache[text] = embedding
    return embedding
```

## Summary

**Ollama Batch Inference:**
- ❌ No native batch API
- ✅ Use concurrent requests instead
- ✅ Multiprocessing (current) works well
- ✅ Async/await is more efficient for I/O
- ✅ Both approaches are valid

**Recommendation:**
- Keep your current multiprocessing implementation
- Try the async version for comparison
- Use whichever performs better on your system
- Consider async for remote Ollama servers

**Expected Performance:**
- Sequential: ~30-60 embeddings/minute
- Multiprocessing: ~120-300 embeddings/minute
- Async: ~200-600 embeddings/minute
- Actual performance depends on your hardware and Ollama setup

