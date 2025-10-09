# Timeout Troubleshooting Guide

## Problem

Embeddings are timing out with errors like:
```
ERROR - Timeout generating embedding for movie 52128
```

## Root Cause

**Too many concurrent requests** overwhelming Ollama server. When you set `--concurrent 10`, it tries to generate 10 embeddings simultaneously, which can overload the system.

## Solutions

### 1. Reduce Concurrent Requests (Recommended)

Start with **lower concurrency** and increase gradually:

```bash
# Start with 3 concurrent requests
python scripts/generate_embeddings_async.py --concurrent 3 --batch-size 2000

# If no timeouts, try 5
python scripts/generate_embeddings_async.py --concurrent 5 --batch-size 2000

# If still no timeouts, try 7
python scripts/generate_embeddings_async.py --concurrent 7 --batch-size 2000
```

### 2. Optimal Settings by System

| System | Concurrent | Expected Speed |
|--------|------------|----------------|
| **MacBook M1/M2** | 3-5 | 2-4 emb/s |
| **MacBook Intel** | 2-3 | 1-2 emb/s |
| **Linux with GPU** | 8-15 | 5-10 emb/s |
| **Linux CPU only** | 3-5 | 2-4 emb/s |
| **Remote Ollama** | 10-20 | Varies |

### 3. Check Ollama Performance

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Test single embedding speed
time curl -X POST http://localhost:11434/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "nomic-embed-text", "prompt": "test"}' > /dev/null

# Should complete in 1-3 seconds
```

### 4. Monitor System Resources

```bash
# Monitor CPU/Memory while running
top

# Check Ollama process
ps aux | grep ollama
```

## Recommended Workflow

### Step 1: Find Your Optimal Concurrency

```bash
# Test with 3 concurrent, 100 movies
python scripts/generate_embeddings_async.py --concurrent 3 --limit 100

# Check logs for timeouts
tail -f logs/generate_embeddings_async.log | grep -i timeout

# If no timeouts, increase to 5
python scripts/generate_embeddings_async.py --concurrent 5 --limit 100
```

### Step 2: Run Full Dataset

Once you find the optimal concurrency (no timeouts):

```bash
# Run with your optimal setting
python scripts/generate_embeddings_async.py --concurrent 5 --batch-size 2000
```

## Understanding the Numbers

### Your Current Run

```
📖 Loading movie data: 100%|████| 28099/28099 [00:38<00:00, 724.06movie/s]
✓ Loaded 28099 movies

Generating embeddings: 0%|  | 1/28099 [02:01<947:58:53, 121.46s/movie, ✓=0, ⊘=0, ✗=1]
```

**Analysis:**
- ✅ Loading: Fast (724 movies/second)
- ❌ Generating: Very slow (121 seconds per embedding)
- ❌ Multiple timeouts immediately

**Problem:** 10 concurrent requests is too many for your system.

### Expected Performance

With optimal settings:

```
📖 Loading movie data: 100%|████| 28099/28099 [00:38<00:00, 724.06movie/s]
✓ Loaded 28099 movies

Generating embeddings: 10%|█| 2810/28099 [15:30<2:20:00, 3.0movie/s, ✓=2805, ⊘=5, ✗=0]
```

**Good signs:**
- ✅ 3-5 embeddings per second
- ✅ Few or no timeouts (✗=0)
- ✅ Steady progress

## Retry Logic (Now Implemented)

The script now automatically retries timeouts:
- **1st attempt:** 120 second timeout
- **2nd attempt:** 240 second timeout (if 1st times out)
- **3rd attempt:** 360 second timeout (if 2nd times out)

This helps with occasional timeouts, but won't fix systematic overload.

## Quick Fixes

### If You're Getting Timeouts

```bash
# Stop the current run (Ctrl+C)

# Restart with lower concurrency
python scripts/generate_embeddings_async.py --concurrent 3 --batch-size 2000
```

### If It's Still Too Slow

```bash
# Use the multiprocessing version instead
python scripts/generate_embeddings.py --workers 5 --batch-size 100
```

## Performance Estimates

### For 28,099 movies (your current dataset)

| Concurrent | Speed | Total Time |
|------------|-------|------------|
| 1 | 0.5 emb/s | ~15.6 hours |
| 3 | 1.5 emb/s | ~5.2 hours |
| 5 | 2.5 emb/s | ~3.1 hours |
| 10 | 5.0 emb/s | ~1.6 hours (if no timeouts) |

**Reality:** If you get timeouts with 10 concurrent, you'll actually be slower than using 3-5 concurrent without timeouts.

## Best Practice

**Start conservative, increase gradually:**

```bash
# Day 1: Test with 3 concurrent
python scripts/generate_embeddings_async.py --concurrent 3 --limit 1000

# If successful, run overnight with 3 concurrent
python scripts/generate_embeddings_async.py --concurrent 3

# Day 2: If you want faster, try 5 concurrent
python scripts/generate_embeddings_async.py --concurrent 5
```

## Comparison: Async vs Multiprocessing

### Async (Current)
```bash
python scripts/generate_embeddings_async.py --concurrent 3
```
- ✅ Lower memory usage
- ✅ Better for remote Ollama
- ⚠️ Sensitive to concurrency settings

### Multiprocessing (Alternative)
```bash
python scripts/generate_embeddings.py --workers 5
```
- ✅ More stable
- ✅ Better CPU utilization
- ⚠️ Higher memory usage

**Try both and see which works better for your system!**

## Summary

**Your issue:** `--concurrent 10` is too high for your system.

**Solution:** Use `--concurrent 3` or `--concurrent 5`

**Command:**
```bash
python scripts/generate_embeddings_async.py --concurrent 3 --batch-size 2000
```

This should give you steady progress without timeouts! 🚀

