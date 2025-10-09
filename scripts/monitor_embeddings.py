#!/usr/bin/env python3
"""
Real-time monitoring of embedding generation progress across all machines
Shows combined progress from the central database
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from datetime import datetime, timedelta
from database.db import get_db_manager
from database.models import Movie, MovieEmbedding

def format_time(seconds):
    """Format seconds into human-readable time"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def main():
    db = get_db_manager()
    
    print("=" * 70)
    print("🎬 Movie Embedding Progress Monitor")
    print("=" * 70)
    print("Monitoring combined progress from all machines...")
    print("Press Ctrl+C to stop\n")
    
    try:
        last_count = 0
        last_time = time.time()
        start_time = time.time()
        rates = []  # Store recent rates for smoothing
        
        while True:
            current_time = time.time()
            
            with db.get_session() as session:
                total_movies = session.query(Movie).count()
                total_embeddings = session.query(MovieEmbedding).count()
                remaining = total_movies - total_embeddings
                progress = (total_embeddings / total_movies) * 100 if total_movies > 0 else 0
                
                # Calculate rate
                time_diff = current_time - last_time
                new_embeddings = total_embeddings - last_count
                
                if time_diff > 0:
                    current_rate = new_embeddings / time_diff
                    rates.append(current_rate)
                    
                    # Keep only last 6 measurements (1 minute of data)
                    if len(rates) > 6:
                        rates.pop(0)
                    
                    # Average rate
                    avg_rate = sum(rates) / len(rates) if rates else 0
                    
                    # Estimate time remaining
                    if avg_rate > 0:
                        eta_seconds = remaining / avg_rate
                        eta_str = format_time(eta_seconds)
                    else:
                        eta_str = "calculating..."
                    
                    # Calculate elapsed time
                    elapsed = current_time - start_time
                    elapsed_str = format_time(elapsed)
                    
                    # Progress bar
                    bar_width = 40
                    filled = int(bar_width * progress / 100)
                    bar = "█" * filled + "░" * (bar_width - filled)
                    
                    # Clear line and print status
                    print(f"\r{bar} {progress:.1f}%", end='')
                    print(f" | {total_embeddings:,}/{total_movies:,}", end='')
                    print(f" | {avg_rate:.1f} emb/s", end='')
                    print(f" | ETA: {eta_str}", end='')
                    print(f" | Elapsed: {elapsed_str}  ", end='', flush=True)
                    
                    last_count = total_embeddings
                    last_time = current_time
                
                # Check if complete
                if remaining == 0:
                    print("\n\n" + "=" * 70)
                    print("✅ All embeddings generated!")
                    print("=" * 70)
                    total_time = current_time - start_time
                    print(f"Total time: {format_time(total_time)}")
                    print(f"Total embeddings: {total_embeddings:,}")
                    if total_time > 0:
                        avg_speed = total_embeddings / total_time
                        print(f"Average speed: {avg_speed:.2f} embeddings/second")
                    break
            
            time.sleep(10)  # Update every 10 seconds
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("Monitoring stopped.")
        print("=" * 70)
        
        # Show final stats
        with db.get_session() as session:
            total_movies = session.query(Movie).count()
            total_embeddings = session.query(MovieEmbedding).count()
            remaining = total_movies - total_embeddings
            progress = (total_embeddings / total_movies) * 100 if total_movies > 0 else 0
            
            print(f"\n📊 Current Status:")
            print(f"   Total movies: {total_movies:,}")
            print(f"   Embeddings generated: {total_embeddings:,}")
            print(f"   Remaining: {remaining:,}")
            print(f"   Progress: {progress:.1f}%")
            
            total_time = time.time() - start_time
            if total_time > 0 and total_embeddings > last_count:
                avg_speed = (total_embeddings - last_count) / total_time
                print(f"   Average speed (this session): {avg_speed:.2f} emb/s")
        
    finally:
        db.close_all()

if __name__ == "__main__":
    main()

