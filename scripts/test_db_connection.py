"""
Test database connection and verify tables exist using ORM
"""
from database.db import get_db_manager
from sqlalchemy import inspect

def test_connection():
    """Test database connection using ORM"""
    try:
        print("Testing database connection...")
        db_manager = get_db_manager()
        print("✅ Database connection successful!")

        # Check if tables exist
        tables = ['movies', 'genres', 'movie_genres', 'casts', 'movie_casts', 'torrents', 'movie_embeddings']

        print("\nChecking tables...")
        inspector = inspect(db_manager.engine)
        existing_tables = inspector.get_table_names()

        for table in tables:
            exists = table in existing_tables
            status = "✅" if exists else "❌"
            print(f"{status} Table '{table}': {'exists' if exists else 'NOT FOUND'}")

        # Get statistics using ORM
        stats = db_manager.get_stats()
        print(f"\n📊 Database Statistics:")
        print(f"   Movies: {stats['total_movies']:,}")
        print(f"   Genres: {stats['total_genres']:,}")
        print(f"   Cast Members: {stats['total_cast']:,}")
        print(f"   Torrents: {stats['total_torrents']:,}")

        db_manager.close_all()

        return True

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_connection()

