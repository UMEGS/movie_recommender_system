"""
Monitor the progress of data fetching in real-time
Shows statistics from the database using ORM
"""
import sys
import os
# Add parent directory to path so we can import database module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_db_manager
from database.models import Movie, Genre, Cast, Torrent, MovieGenre
from sqlalchemy import func, desc
import time
from datetime import datetime, timedelta

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

def get_stats():
    """Get current statistics from database using ORM"""
    try:
        db_manager = get_db_manager()

        with db_manager.get_session() as session:
            stats = {}

            # Total movies
            stats['total_movies'] = session.query(Movie).count()

            # Movies with details (have description)
            stats['movies_with_details'] = session.query(Movie).filter(
                Movie.description_full.isnot(None),
                Movie.description_full != ''
            ).count()

            # Total genres
            stats['total_genres'] = session.query(Genre).count()

            # Total cast members
            stats['total_cast'] = session.query(Cast).count()

            # Total torrents
            stats['total_torrents'] = session.query(Torrent).count()

            # Recently added movies (last 5 minutes)
            five_minutes_ago = datetime.now() - timedelta(minutes=5)
            stats['recent_movies'] = session.query(Movie).filter(
                Movie.created_at > five_minutes_ago
            ).count()

            # Top 5 genres by movie count
            top_genres = session.query(
                Genre.name,
                func.count(MovieGenre.movie_id).label('count')
            ).join(
                MovieGenre, Genre.id == MovieGenre.genre_id
            ).group_by(
                Genre.name
            ).order_by(
                desc('count')
            ).limit(5).all()

            stats['top_genres'] = top_genres

            # Latest movies added
            latest_movies = session.query(
                Movie.title,
                Movie.year,
                Movie.rating,
                Movie.created_at
            ).order_by(
                desc(Movie.created_at)
            ).limit(5).all()

            stats['latest_movies'] = latest_movies

            return stats

    except Exception as e:
        return {'error': str(e)}

def display_stats(stats):
    """Display statistics in a nice format"""
    clear_screen()
    
    print("=" * 70)
    print("🎬 YTS MOVIE DATABASE - LIVE MONITOR")
    print("=" * 70)
    print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    if 'error' in stats:
        print(f"\n❌ Error: {stats['error']}")
        return
    
    print("\n📊 OVERALL STATISTICS")
    print("-" * 70)
    print(f"Total Movies:              {stats['total_movies']:,}")
    print(f"Movies with Full Details:  {stats['movies_with_details']:,}")
    print(f"Total Genres:              {stats['total_genres']:,}")
    print(f"Total Cast Members:        {stats['total_cast']:,}")
    print(f"Total Torrents:            {stats['total_torrents']:,}")
    print(f"Movies Added (Last 5 min): {stats['recent_movies']:,}")
    
    if stats['total_movies'] > 0:
        completion = (stats['movies_with_details'] / stats['total_movies']) * 100
        print(f"\nCompletion Rate:           {completion:.1f}%")
    
    print("\n🎭 TOP 5 GENRES")
    print("-" * 70)
    for genre, count in stats['top_genres']:
        print(f"  {genre:20s} {count:,} movies")
    
    print("\n🆕 LATEST MOVIES ADDED")
    print("-" * 70)
    for title, year, rating, created_at in stats['latest_movies']:
        time_str = created_at.strftime('%H:%M:%S') if created_at else 'N/A'
        print(f"  [{time_str}] {title[:40]:40s} ({year}) ⭐ {rating}")
    
    print("\n" + "=" * 70)
    print("Press Ctrl+C to exit")
    print("=" * 70)

def monitor(refresh_interval=5):
    """Monitor database in real-time"""
    try:
        while True:
            stats = get_stats()
            display_stats(stats)
            time.sleep(refresh_interval)
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor YTS database progress')
    parser.add_argument('--interval', type=int, default=5,
                       help='Refresh interval in seconds (default: 5)')
    
    args = parser.parse_args()
    
    print("Starting monitor...")
    print(f"Refresh interval: {args.interval} seconds")
    time.sleep(2)
    
    monitor(refresh_interval=args.interval)

