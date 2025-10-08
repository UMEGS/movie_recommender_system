"""
Movie Recommendation Engine using PostgreSQL pgvector
Provides fast similarity search for movie recommendations
"""
import logging
from typing import List, Dict, Optional
from database.db import get_db_manager
from database.models import Movie, MovieEmbedding, Genre
from sqlalchemy import text, func
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MovieRecommendationEngine:
    """
    Movie recommendation engine using vector similarity search
    """
    
    def __init__(self):
        self.db_manager = get_db_manager()
    
    def get_movie_by_id(self, movie_id: int) -> Optional[Dict]:
        """Get movie details by internal database ID"""
        with self.db_manager.get_session() as session:
            movie = session.query(Movie).filter_by(id=movie_id).first()
            if movie:
                return self._movie_to_dict(movie)
            return None
    
    def get_movie_by_external_id(self, external_id: int) -> Optional[Dict]:
        """Get movie details by YTS external ID"""
        with self.db_manager.get_session() as session:
            movie = session.query(Movie).filter_by(external_id=external_id).first()
            if movie:
                return self._movie_to_dict(movie)
            return None
    
    def search_movies(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search movies by title or description
        Uses PostgreSQL full-text search
        """
        with self.db_manager.get_session() as session:
            # Use the search_vector column for full-text search
            movies = session.query(Movie).filter(
                text("search_vector @@ plainto_tsquery('english', :query)")
            ).params(query=query).limit(limit).all()
            
            return [self._movie_to_dict(m) for m in movies]
    
    def recommend_by_movie_id(self, movie_id: int, limit: int = 10, 
                              distance_metric: str = 'cosine') -> List[Dict]:
        """
        Get movie recommendations based on a movie ID
        Uses vector similarity search
        
        Args:
            movie_id: Internal database movie ID
            limit: Number of recommendations to return
            distance_metric: 'cosine', 'l2', or 'inner_product'
        
        Returns:
            List of recommended movies with similarity scores
        """
        with self.db_manager.get_session() as session:
            # Get the embedding for the input movie
            movie_embedding = session.query(MovieEmbedding).filter_by(
                movie_id=movie_id
            ).first()
            
            if not movie_embedding:
                logger.warning(f"No embedding found for movie {movie_id}")
                return []
            
            # Choose distance operator based on metric
            if distance_metric == 'cosine':
                distance_op = '<=>'  # Cosine distance
                order = 'ASC'
            elif distance_metric == 'l2':
                distance_op = '<->'  # L2 distance
                order = 'ASC'
            elif distance_metric == 'inner_product':
                distance_op = '<#>'  # Inner product (negative, so DESC for similarity)
                order = 'DESC'
            else:
                raise ValueError(f"Unknown distance metric: {distance_metric}")
            
            # Perform vector similarity search
            # Exclude the input movie itself
            query = text(f"""
                SELECT 
                    m.id,
                    m.external_id,
                    m.title,
                    m.year,
                    m.rating,
                    m.description_full,
                    m.small_cover_image,
                    (me.embedding {distance_op} :target_embedding) as distance
                FROM movies m
                JOIN movie_embeddings me ON m.id = me.movie_id
                WHERE m.id != :movie_id
                ORDER BY distance {order}
                LIMIT :limit
            """)
            
            results = session.execute(
                query,
                {
                    'target_embedding': str(movie_embedding.embedding),
                    'movie_id': movie_id,
                    'limit': limit
                }
            ).fetchall()
            
            recommendations = []
            for row in results:
                movie = session.query(Movie).filter_by(id=row.id).first()
                movie_dict = self._movie_to_dict(movie)
                movie_dict['similarity_score'] = float(1 - row.distance) if distance_metric == 'cosine' else float(row.distance)
                recommendations.append(movie_dict)
            
            return recommendations
    
    def recommend_by_external_id(self, external_id: int, limit: int = 10,
                                  distance_metric: str = 'cosine') -> List[Dict]:
        """
        Get movie recommendations based on YTS external ID
        """
        with self.db_manager.get_session() as session:
            movie = session.query(Movie).filter_by(external_id=external_id).first()
            if not movie:
                logger.warning(f"Movie with external_id {external_id} not found")
                return []
            
            return self.recommend_by_movie_id(movie.id, limit, distance_metric)
    
    def recommend_by_genres(self, genres: List[str], limit: int = 10,
                           min_rating: float = 6.0) -> List[Dict]:
        """
        Get movie recommendations based on genres
        
        Args:
            genres: List of genre names
            limit: Number of recommendations
            min_rating: Minimum rating threshold
        """
        with self.db_manager.get_session() as session:
            # Find movies that match the genres
            movies = session.query(Movie).join(
                Movie.genres
            ).filter(
                Genre.name.in_(genres),
                Movie.rating >= min_rating
            ).order_by(
                Movie.rating.desc()
            ).limit(limit).all()
            
            return [self._movie_to_dict(m) for m in movies]
    
    def get_similar_by_text(self, text: str, limit: int = 10) -> List[Dict]:
        """
        Find movies similar to a text description
        Generates embedding for the text using Ollama and finds similar movies
        """
        try:
            from config import OLLAMA_HOST, OLLAMA_EMBEDDING_MODEL, OLLAMA_TIMEOUT
            import requests

            # Generate embedding using Ollama
            payload = {
                "model": OLLAMA_EMBEDDING_MODEL,
                "prompt": text
            }

            response = requests.post(
                f"{OLLAMA_HOST}/api/embeddings",
                json=payload,
                timeout=OLLAMA_TIMEOUT
            )

            if response.status_code != 200:
                logger.error(f"Ollama API error: {response.status_code}")
                return []

            text_embedding = response.json()['embedding']
            
            with self.db_manager.get_session() as session:
                # Perform vector similarity search
                query = text("""
                    SELECT 
                        m.id,
                        m.external_id,
                        m.title,
                        m.year,
                        m.rating,
                        m.description_full,
                        m.small_cover_image,
                        (me.embedding <=> :target_embedding) as distance
                    FROM movies m
                    JOIN movie_embeddings me ON m.id = me.movie_id
                    ORDER BY distance ASC
                    LIMIT :limit
                """)
                
                results = session.execute(
                    query,
                    {
                        'target_embedding': str(text_embedding),
                        'limit': limit
                    }
                ).fetchall()
                
                recommendations = []
                for row in results:
                    movie = session.query(Movie).filter_by(id=row.id).first()
                    movie_dict = self._movie_to_dict(movie)
                    movie_dict['similarity_score'] = float(1 - row.distance)
                    recommendations.append(movie_dict)
                
                return recommendations

        except Exception as e:
            logger.error(f"Error generating text embedding: {e}")
            return []
    
    def get_trending_movies(self, limit: int = 20, min_year: int = 2020) -> List[Dict]:
        """
        Get trending/popular movies
        Based on rating, like count, and recency
        """
        with self.db_manager.get_session() as session:
            movies = session.query(Movie).filter(
                Movie.year >= min_year,
                Movie.rating >= 6.0
            ).order_by(
                Movie.like_count.desc(),
                Movie.rating.desc()
            ).limit(limit).all()
            
            return [self._movie_to_dict(m) for m in movies]
    
    def get_top_rated_movies(self, limit: int = 20, min_votes: int = 100) -> List[Dict]:
        """Get top rated movies"""
        with self.db_manager.get_session() as session:
            movies = session.query(Movie).filter(
                Movie.rating >= 7.0,
                Movie.like_count >= min_votes
            ).order_by(
                Movie.rating.desc()
            ).limit(limit).all()
            
            return [self._movie_to_dict(m) for m in movies]
    
    def _movie_to_dict(self, movie: Movie) -> Dict:
        """Convert Movie object to dictionary"""
        return {
            'id': movie.id,
            'external_id': movie.external_id,
            'imdb_code': movie.imdb_code,
            'title': movie.title,
            'title_english': movie.title_english,
            'year': movie.year,
            'rating': float(movie.rating) if movie.rating else None,
            'runtime': movie.runtime,
            'genres': [g.name for g in movie.genres] if movie.genres else [],
            'description_full': movie.description_full,
            'description_intro': movie.description_intro,
            'language': movie.language,
            'like_count': movie.like_count,
            'small_cover_image': movie.small_cover_image,
            'medium_cover_image': movie.medium_cover_image,
            'large_cover_image': movie.large_cover_image,
            'yt_trailer_code': movie.yt_trailer_code,
            'cast': [{'name': c.name, 'imdb_code': c.imdb_code} for c in movie.casts[:5]] if movie.casts else [],
            'torrents_count': len(movie.torrents) if movie.torrents else 0
        }
    
    def close(self):
        """Close database connections"""
        self.db_manager.close_all()


# Example usage and CLI
if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Movie Recommendation Engine')
    parser.add_argument('--movie-id', type=int, help='Get recommendations for movie ID')
    parser.add_argument('--external-id', type=int, help='Get recommendations for YTS external ID')
    parser.add_argument('--search', type=str, help='Search movies by title')
    parser.add_argument('--genres', nargs='+', help='Get recommendations by genres')
    parser.add_argument('--text', type=str, help='Find movies similar to text description')
    parser.add_argument('--trending', action='store_true', help='Get trending movies')
    parser.add_argument('--top-rated', action='store_true', help='Get top rated movies')
    parser.add_argument('--limit', type=int, default=10, help='Number of results')
    
    args = parser.parse_args()
    
    engine = MovieRecommendationEngine()
    
    try:
        if args.movie_id:
            print(f"\n🎬 Recommendations for movie ID {args.movie_id}:\n")
            movie = engine.get_movie_by_id(args.movie_id)
            if movie:
                print(f"Base movie: {movie['title']} ({movie['year']})")
                print("-" * 60)
            recommendations = engine.recommend_by_movie_id(args.movie_id, args.limit)
            
        elif args.external_id:
            print(f"\n🎬 Recommendations for external ID {args.external_id}:\n")
            movie = engine.get_movie_by_external_id(args.external_id)
            if movie:
                print(f"Base movie: {movie['title']} ({movie['year']})")
                print("-" * 60)
            recommendations = engine.recommend_by_external_id(args.external_id, args.limit)
            
        elif args.search:
            print(f"\n🔍 Search results for '{args.search}':\n")
            recommendations = engine.search_movies(args.search, args.limit)
            
        elif args.genres:
            print(f"\n🎭 Movies in genres: {', '.join(args.genres)}\n")
            recommendations = engine.recommend_by_genres(args.genres, args.limit)
            
        elif args.text:
            print(f"\n📝 Movies similar to: '{args.text}'\n")
            recommendations = engine.get_similar_by_text(args.text, args.limit)
            
        elif args.trending:
            print("\n🔥 Trending Movies:\n")
            recommendations = engine.get_trending_movies(args.limit)
            
        elif args.top_rated:
            print("\n⭐ Top Rated Movies:\n")
            recommendations = engine.get_top_rated_movies(args.limit)
            
        else:
            parser.print_help()
            exit(0)
        
        # Print results
        for i, movie in enumerate(recommendations, 1):
            print(f"{i}. {movie['title']} ({movie['year']}) - ⭐ {movie['rating']}")
            if movie.get('genres'):
                print(f"   Genres: {', '.join(movie['genres'])}")
            if movie.get('similarity_score'):
                print(f"   Similarity: {movie['similarity_score']:.3f}")
            print()
        
        if not recommendations:
            print("No recommendations found.")
            
    finally:
        engine.close()

