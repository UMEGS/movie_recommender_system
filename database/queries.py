"""
Database query operations for movie recommendation system
Separates database queries from business logic
"""
import logging
from typing import List, Dict, Optional, Tuple
from sqlalchemy import text, func
from database.models import Movie, MovieEmbedding, Genre
import numpy as np

logger = logging.getLogger(__name__)


class MovieQueries:
    """
    Handles all database query operations for movies
    Separated from DatabaseManager to keep concerns separate
    """
    
    def __init__(self, db_manager):
        """
        Initialize with a database manager instance
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager
    
    def get_movie_by_id(self, session, movie_id: int) -> Optional[Movie]:
        """
        Get movie by internal database ID

        Args:
            session: SQLAlchemy session
            movie_id: Internal database movie ID

        Returns:
            Movie object or None
        """
        return session.query(Movie).filter_by(id=movie_id).first()

    def get_movie_by_external_id(self, session, external_id: int) -> Optional[Movie]:
        """
        Get movie by YTS external ID

        Args:
            session: SQLAlchemy session
            external_id: YTS external movie ID

        Returns:
            Movie object or None
        """
        return session.query(Movie).filter_by(external_id=external_id).first()

    def search_movies(self, session, query: str, limit: int = 10) -> List[Movie]:
        """
        Search movies by title or description using full-text search

        Args:
            session: SQLAlchemy session
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of Movie objects
        """
        movies = session.query(Movie).filter(
            text("search_vector @@ plainto_tsquery('english', :query)")
        ).params(query=query).limit(limit).all()
        return movies

    def get_movie_embedding(self, session, movie_id: int) -> Optional[MovieEmbedding]:
        """
        Get embedding for a movie

        Args:
            session: SQLAlchemy session
            movie_id: Internal database movie ID

        Returns:
            MovieEmbedding object or None
        """
        return session.query(MovieEmbedding).filter_by(movie_id=movie_id).first()
    
    def find_similar_movies(self, session, movie_id: int, limit: int = 10,
                           distance_metric: str = 'cosine') -> List[Tuple[int, float]]:
        """
        Find similar movies using vector similarity search

        Args:
            session: SQLAlchemy session
            movie_id: Internal database movie ID
            limit: Maximum number of results
            distance_metric: 'cosine', 'l2', or 'inner_product'

        Returns:
            List of tuples (movie_id, distance)
        """
        # Get the embedding for the input movie
        movie_embedding = session.query(MovieEmbedding).filter_by(
            movie_id=movie_id
        ).first()

        if not movie_embedding:
            logger.warning(f"No embedding found for movie {movie_id}")
            return []

        # Choose the appropriate distance method
        if distance_metric == 'cosine':
            distance_expr = MovieEmbedding.embedding.cosine_distance(movie_embedding.embedding)
        elif distance_metric == 'l2':
            distance_expr = MovieEmbedding.embedding.l2_distance(movie_embedding.embedding)
        elif distance_metric == 'inner_product':
            distance_expr = MovieEmbedding.embedding.max_inner_product(movie_embedding.embedding)
        else:
            raise ValueError(f"Unknown distance metric: {distance_metric}")

        # Build the query using ORM
        # Query specific columns instead of the whole Movie object to avoid issues with parameter binding
        query = session.query(
            Movie.id,
            distance_expr.label('distance')
        ).join(
            MovieEmbedding, Movie.id == MovieEmbedding.movie_id
        ).filter(
            Movie.id != movie_id
        ).order_by(
            'distance'
        ).limit(limit)

        results = query.all()
        return [(movie_id, distance) for movie_id, distance in results]
    
    def get_movies_by_genres(self, session, genres: List[str], limit: int = 10,
                            min_rating: float = 6.0) -> List[Movie]:
        """
        Get movies by genres

        Args:
            session: SQLAlchemy session
            genres: List of genre names
            limit: Maximum number of results
            min_rating: Minimum rating threshold

        Returns:
            List of Movie objects
        """
        movies = session.query(Movie).join(
            Movie.genres
        ).filter(
            Genre.name.in_(genres),
            Movie.rating >= min_rating
        ).order_by(
            Movie.rating.desc()
        ).limit(limit).all()
        return movies

    def get_trending_movies(self, session, limit: int = 20, min_year: int = 2020) -> List[Movie]:
        """
        Get trending/popular movies

        Args:
            session: SQLAlchemy session
            limit: Maximum number of results
            min_year: Minimum year threshold

        Returns:
            List of Movie objects
        """
        movies = session.query(Movie).filter(
            Movie.year >= min_year,
            Movie.rating >= 6.0
        ).order_by(
            Movie.like_count.desc(),
            Movie.rating.desc()
        ).limit(limit).all()
        return movies

    def get_top_rated_movies(self, session, limit: int = 20, min_votes: int = 100) -> List[Movie]:
        """
        Get top rated movies

        Args:
            session: SQLAlchemy session
            limit: Maximum number of results
            min_votes: Minimum vote count threshold

        Returns:
            List of Movie objects
        """
        movies = session.query(Movie).filter(
            Movie.rating >= 7.0,
            Movie.like_count >= min_votes
        ).order_by(
            Movie.rating.desc()
        ).limit(limit).all()
        return movies

    def get_movies_by_year_range(self, session, start_year: int, end_year: int,
                                 limit: int = 20) -> List[Movie]:
        """
        Get movies within a year range

        Args:
            session: SQLAlchemy session
            start_year: Start year (inclusive)
            end_year: End year (inclusive)
            limit: Maximum number of results

        Returns:
            List of Movie objects
        """
        movies = session.query(Movie).filter(
            Movie.year >= start_year,
            Movie.year <= end_year
        ).order_by(
            Movie.rating.desc()
        ).limit(limit).all()
        return movies
    
    def get_movie_count(self) -> int:
        """Get total number of movies in database"""
        with self.db_manager.get_session() as session:
            return session.query(Movie).count()
    
    def get_embedding_count(self) -> int:
        """Get total number of embeddings in database"""
        with self.db_manager.get_session() as session:
            return session.query(MovieEmbedding).count()

