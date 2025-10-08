"""
Reset Database - Drop all movie data for testing
WARNING: This will delete ALL data from the database!
"""
import sys
import os
# Add parent directory to path so we can import database module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_db_manager
from database.models import Movie, Genre, Cast, Torrent, MovieEmbedding, MovieGenre, MovieCast
from sqlalchemy import text


def confirm_reset():
    """Ask user to confirm before deleting data"""
    print("=" * 60)
    print("⚠️  WARNING: DATABASE RESET")
    print("=" * 60)
    print("\nThis will DELETE ALL data from the following tables:")
    print("  - movies")
    print("  - genres")
    print("  - casts")
    print("  - torrents")
    print("  - movie_embeddings")
    print("  - movie_genres (relationships)")
    print("  - movie_casts (relationships)")
    print("\n" + "=" * 60)
    
    response = input("\nAre you sure you want to continue? Type 'YES' to confirm: ")
    return response.strip() == 'YES'


def get_table_counts(session):
    """Get current row counts for all tables"""
    counts = {}
    counts['movies'] = session.query(Movie).count()
    counts['genres'] = session.query(Genre).count()
    counts['casts'] = session.query(Cast).count()
    counts['torrents'] = session.query(Torrent).count()
    counts['movie_embeddings'] = session.query(MovieEmbedding).count()
    
    # Count relationships
    counts['movie_genres'] = session.execute(text("SELECT COUNT(*) FROM movie_genres")).scalar()
    counts['movie_casts'] = session.execute(text("SELECT COUNT(*) FROM movie_casts")).scalar()
    
    return counts


def reset_database():
    """Delete all data from the database"""
    db_manager = get_db_manager()
    
    try:
        with db_manager.get_session() as session:
            # Show current counts
            print("\n📊 Current Database State:")
            print("-" * 60)
            counts = get_table_counts(session)
            for table, count in counts.items():
                print(f"  {table:20s}: {count:,} rows")
            print("-" * 60)
            
            if sum(counts.values()) == 0:
                print("\n✅ Database is already empty!")
                return
            
            print("\n🗑️  Deleting all data...")
            
            # Delete in correct order (relationships first, then main tables)
            # The CASCADE deletes should handle most of this, but we'll be explicit
            
            # 1. Delete movie_embeddings (references movies)
            deleted = session.query(MovieEmbedding).delete()
            print(f"  ✓ Deleted {deleted:,} movie embeddings")
            
            # 2. Delete torrents (references movies)
            deleted = session.query(Torrent).delete()
            print(f"  ✓ Deleted {deleted:,} torrents")
            
            # 3. Delete movie_casts relationships
            deleted = session.execute(text("DELETE FROM movie_casts")).rowcount
            print(f"  ✓ Deleted {deleted:,} movie-cast relationships")
            
            # 4. Delete movie_genres relationships
            deleted = session.execute(text("DELETE FROM movie_genres")).rowcount
            print(f"  ✓ Deleted {deleted:,} movie-genre relationships")
            
            # 5. Delete movies
            deleted = session.query(Movie).delete()
            print(f"  ✓ Deleted {deleted:,} movies")
            
            # 6. Delete genres
            deleted = session.query(Genre).delete()
            print(f"  ✓ Deleted {deleted:,} genres")
            
            # 7. Delete cast members
            deleted = session.query(Cast).delete()
            print(f"  ✓ Deleted {deleted:,} cast members")
            
            # Commit all deletions
            session.commit()
            
            print("\n✅ Database reset complete!")
            
            # Verify everything is deleted
            print("\n📊 Final Database State:")
            print("-" * 60)
            final_counts = get_table_counts(session)
            for table, count in final_counts.items():
                print(f"  {table:20s}: {count:,} rows")
            print("-" * 60)
            
            if sum(final_counts.values()) == 0:
                print("\n🎉 All data successfully deleted!")
            else:
                print("\n⚠️  Warning: Some data may remain")
                
    except Exception as e:
        print(f"\n❌ Error resetting database: {e}")
        raise
    finally:
        db_manager.close_all()


def reset_sequences():
    """Reset auto-increment sequences (optional)"""
    db_manager = get_db_manager()
    
    try:
        with db_manager.get_session() as session:
            print("\n🔄 Resetting ID sequences...")
            
            # Reset sequences to start from 1 again
            sequences = [
                'movies_id_seq',
                'genres_id_seq',
                'casts_id_seq',
                'torrents_id_seq'
            ]
            
            for seq in sequences:
                try:
                    session.execute(text(f"ALTER SEQUENCE {seq} RESTART WITH 1"))
                    print(f"  ✓ Reset {seq}")
                except Exception as e:
                    print(f"  ⚠️  Could not reset {seq}: {e}")
            
            session.commit()
            print("\n✅ Sequences reset complete!")
            
    except Exception as e:
        print(f"\n⚠️  Error resetting sequences: {e}")
    finally:
        db_manager.close_all()


def main():
    """Main function"""
    print("\n" + "=" * 60)
    print("🗑️  DATABASE RESET SCRIPT")
    print("=" * 60)
    
    # Check if user wants to proceed
    if not confirm_reset():
        print("\n❌ Reset cancelled. No data was deleted.")
        return
    
    # Reset the database
    reset_database()
    
    # Ask if user wants to reset sequences
    print("\n" + "=" * 60)
    response = input("\nDo you want to reset ID sequences? (y/n): ")
    if response.lower() in ['y', 'yes']:
        reset_sequences()
    
    print("\n" + "=" * 60)
    print("✅ Database is ready for fresh data!")
    print("=" * 60)
    print("\nYou can now run:")
    print("  python scripts/fetch_yts_data.py --max-pages 10")
    print("  python scripts/generate_embeddings.py")
    print("\n")


if __name__ == "__main__":
    main()

