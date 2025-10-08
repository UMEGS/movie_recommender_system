"""
Database connection and session management using SQLAlchemy ORM
All database operations should go through this module
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from datetime import datetime
from config import DB_CONFIG
from database.models import Base, Movie, Genre, Cast, Torrent, MovieGenre, MovieCast
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations using SQLAlchemy ORM"""
    
    def __init__(self, pool_size=10, max_overflow=20):
        """Initialize database engine and session factory"""
        # Create database URL
        db_url = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
        
        # Create engine with connection pooling
        self.engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            echo=False  # Set to True for SQL debugging
        )
        
        # Create session factory
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)
        
        logger.info(f"Database engine created (pool_size={pool_size}, max_overflow={max_overflow})")
    
    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    def close_all(self):
        """Close all connections"""
        self.Session.remove()
        self.engine.dispose()
        logger.info("All database connections closed")
    
    def movie_exists(self, external_id):
        """Check if a movie already exists by external_id"""
        with self.get_session() as session:
            return session.query(Movie).filter_by(external_id=external_id).first() is not None
    
    def get_or_create_genre(self, session, genre_name):
        """Get existing genre or create new one"""
        genre = session.query(Genre).filter_by(name=genre_name).first()
        if not genre:
            genre = Genre(name=genre_name)
            session.add(genre)
            session.flush()  # Get the ID without committing
        return genre
    
    def get_or_create_cast(self, session, cast_data):
        """Get existing cast member or create new one"""
        # Try to find by name and imdb_code
        cast = session.query(Cast).filter_by(
            name=cast_data['name'],
            imdb_code=cast_data.get('imdb_code')
        ).first()
        
        if not cast:
            cast = Cast(
                name=cast_data['name'],
                imdb_code=cast_data.get('imdb_code'),
                url_small_image=cast_data.get('url_small_image')
            )
            session.add(cast)
            session.flush()
        return cast
    
    def save_movie(self, movie_data):
        """
        Save or update a movie with all related data
        Returns (success: bool, movie_id: int or None, message: str)
        """
        try:
            with self.get_session() as session:
                external_id = movie_data.get('id')
                
                # Check if movie already exists
                existing_movie = session.query(Movie).filter_by(external_id=external_id).first()
                
                if existing_movie:
                    logger.debug(f"Movie {external_id} already exists, skipping...")
                    return (True, existing_movie.id, "already_exists")
                
                # Create new movie
                movie = Movie(
                    external_id=external_id,
                    imdb_code=movie_data.get('imdb_code'),
                    title=movie_data.get('title'),
                    title_english=movie_data.get('title_english'),
                    title_long=movie_data.get('title_long'),
                    slug=movie_data.get('slug'),
                    year=movie_data.get('year'),
                    rating=movie_data.get('rating'),
                    runtime=movie_data.get('runtime'),
                    description_intro=movie_data.get('description_intro'),
                    description_full=movie_data.get('description_full'),
                    yt_trailer_code=movie_data.get('yt_trailer_code'),
                    language=movie_data.get('language'),
                    mpa_rating=movie_data.get('mpa_rating'),
                    like_count=movie_data.get('like_count', 0),
                    background_image=movie_data.get('background_image'),
                    background_image_original=movie_data.get('background_image_original'),
                    small_cover_image=movie_data.get('small_cover_image'),
                    medium_cover_image=movie_data.get('medium_cover_image'),
                    large_cover_image=movie_data.get('large_cover_image'),
                    date_uploaded=datetime.fromtimestamp(movie_data['date_uploaded_unix']) if movie_data.get('date_uploaded_unix') else None,
                    date_uploaded_unix=movie_data.get('date_uploaded_unix')
                )
                session.add(movie)
                session.flush()  # Get the movie ID
                
                # Add genres
                if movie_data.get('genres'):
                    for genre_name in movie_data['genres']:
                        genre = self.get_or_create_genre(session, genre_name)
                        if genre not in movie.genres:
                            movie.genres.append(genre)
                
                # Add cast members
                if movie_data.get('cast'):
                    for cast_data in movie_data['cast']:
                        cast = self.get_or_create_cast(session, cast_data)
                        if cast not in movie.casts:
                            movie.casts.append(cast)
                            # Add character name to the association table
                            movie_cast = session.query(MovieCast).filter_by(
                                movie_id=movie.id,
                                cast_id=cast.id
                            ).first()
                            if movie_cast:
                                movie_cast.character_name = cast_data.get('character_name')
                
                # Add torrents
                if movie_data.get('torrents'):
                    for torrent_data in movie_data['torrents']:
                        torrent = Torrent(
                            movie_id=movie.id,
                            url=torrent_data.get('url'),
                            hash=torrent_data.get('hash'),
                            quality=torrent_data.get('quality'),
                            type=torrent_data.get('type'),
                            is_repack=torrent_data.get('is_repack') == '1' if torrent_data.get('is_repack') else False,
                            video_codec=torrent_data.get('video_codec'),
                            bit_depth=torrent_data.get('bit_depth'),
                            audio_channels=torrent_data.get('audio_channels'),
                            seeds=torrent_data.get('seeds', 0),
                            peers=torrent_data.get('peers', 0),
                            size=torrent_data.get('size'),
                            size_bytes=torrent_data.get('size_bytes'),
                            date_uploaded=datetime.fromtimestamp(torrent_data['date_uploaded_unix']) if torrent_data.get('date_uploaded_unix') else None,
                            date_uploaded_unix=torrent_data.get('date_uploaded_unix')
                        )
                        session.add(torrent)
                
                session.flush()
                return (True, movie.id, "created")
                
        except Exception as e:
            logger.error(f"Error saving movie {movie_data.get('id')}: {e}")
            return (False, None, str(e))
    
    def get_movie_count(self):
        """Get total number of movies in database"""
        with self.get_session() as session:
            return session.query(Movie).count()
    
    def get_stats(self):
        """Get database statistics"""
        with self.get_session() as session:
            stats = {
                'total_movies': session.query(Movie).count(),
                'total_genres': session.query(Genre).count(),
                'total_cast': session.query(Cast).count(),
                'total_torrents': session.query(Torrent).count(),
            }
            return stats


# Global database manager instance
db_manager = None


def get_db_manager(pool_size=10, max_overflow=20):
    """Get or create the global database manager"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager(pool_size, max_overflow)
    return db_manager


def close_db():
    """Close the global database manager"""
    global db_manager
    if db_manager:
        db_manager.close_all()
        db_manager = None

