"""
FastAPI application for Movie Recommendation System
Provides REST API endpoints for all recommendation engine features
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel, Field
import logging

from scripts.recommendation_engine import MovieRecommendationEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Movie Recommendation API",
    description="AI-powered movie recommendation system using vector embeddings and PostgreSQL pgvector",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize recommendation engine
engine = MovieRecommendationEngine()


# Pydantic models for request/response
class MovieResponse(BaseModel):
    """Movie response model"""
    id: int
    external_id: int
    imdb_code: Optional[str]
    title: str
    title_english: Optional[str]
    year: int
    rating: Optional[float]
    runtime: Optional[int]
    genres: List[str]
    description_full: Optional[str]
    description_intro: Optional[str]
    language: Optional[str]
    like_count: Optional[int]
    small_cover_image: Optional[str]
    medium_cover_image: Optional[str]
    large_cover_image: Optional[str]
    yt_trailer_code: Optional[str]
    cast: List[dict]
    torrents_count: int
    similarity_score: Optional[float] = None


class RecommendationResponse(BaseModel):
    """Recommendation response with metadata"""
    total: int
    movies: List[MovieResponse]
    distance_metric: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    database: str


# API Endpoints

@app.get("/", tags=["General"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Movie Recommendation API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        movie = engine.get_movie_by_id(1)
        db_status = "connected" if movie else "no_data"
        
        return {
            "status": "healthy",
            "version": "2.0.0",
            "database": db_status
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.get("/api/movies/{movie_id}", response_model=MovieResponse, tags=["Movies"])
async def get_movie(movie_id: int):
    """
    Get movie details by internal database ID
    
    - **movie_id**: Internal database movie ID
    """
    try:
        movie = engine.get_movie_by_id(movie_id)
        if not movie:
            raise HTTPException(status_code=404, detail=f"Movie with ID {movie_id} not found")
        return movie
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting movie {movie_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/movies/external/{external_id}", response_model=MovieResponse, tags=["Movies"])
async def get_movie_by_external_id(external_id: int):
    """
    Get movie details by YTS external ID
    
    - **external_id**: YTS external movie ID
    """
    try:
        movie = engine.get_movie_by_external_id(external_id)
        if not movie:
            raise HTTPException(status_code=404, detail=f"Movie with external ID {external_id} not found")
        return movie
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting movie by external ID {external_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search", response_model=RecommendationResponse, tags=["Search"])
async def search_movies(
    query: str = Query(..., description="Search query string"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results")
):
    """
    Search movies by title or description using full-text search
    
    - **query**: Search query string
    - **limit**: Maximum number of results (1-100)
    """
    try:
        movies = engine.search_movies(query, limit)
        return {
            "total": len(movies),
            "movies": movies
        }
    except Exception as e:
        logger.error(f"Error searching movies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recommendations/movie/{movie_id}", response_model=RecommendationResponse, tags=["Recommendations"])
async def get_recommendations_by_movie_id(
    movie_id: int,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of recommendations"),
    distance_metric: str = Query("cosine", regex="^(cosine|l2|inner_product)$", description="Distance metric")
):
    """
    Get movie recommendations based on a movie ID using vector similarity
    
    - **movie_id**: Internal database movie ID
    - **limit**: Maximum number of recommendations (1-100)
    - **distance_metric**: Distance metric (cosine, l2, inner_product)
    """
    try:
        recommendations = engine.recommend_by_movie_id(movie_id, limit, distance_metric)
        if not recommendations:
            # Check if movie exists
            movie = engine.get_movie_by_id(movie_id)
            if not movie:
                raise HTTPException(status_code=404, detail=f"Movie with ID {movie_id} not found")
            # Movie exists but no recommendations (probably no embedding)
            raise HTTPException(status_code=404, detail=f"No recommendations found for movie {movie_id}. Movie may not have embeddings.")
        
        return {
            "total": len(recommendations),
            "movies": recommendations,
            "distance_metric": distance_metric
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations for movie {movie_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recommendations/external/{external_id}", response_model=RecommendationResponse, tags=["Recommendations"])
async def get_recommendations_by_external_id(
    external_id: int,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of recommendations"),
    distance_metric: str = Query("cosine", regex="^(cosine|l2|inner_product)$", description="Distance metric")
):
    """
    Get movie recommendations based on YTS external ID
    
    - **external_id**: YTS external movie ID
    - **limit**: Maximum number of recommendations (1-100)
    - **distance_metric**: Distance metric (cosine, l2, inner_product)
    """
    try:
        recommendations = engine.recommend_by_external_id(external_id, limit, distance_metric)
        if not recommendations:
            raise HTTPException(status_code=404, detail=f"No recommendations found for external ID {external_id}")
        
        return {
            "total": len(recommendations),
            "movies": recommendations,
            "distance_metric": distance_metric
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations for external ID {external_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recommendations/genres", response_model=RecommendationResponse, tags=["Recommendations"])
async def get_recommendations_by_genres(
    genres: List[str] = Query(..., description="List of genre names"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of recommendations"),
    min_rating: float = Query(6.0, ge=0, le=10, description="Minimum rating threshold")
):
    """
    Get movie recommendations based on genres
    
    - **genres**: List of genre names (e.g., Action, Comedy, Drama)
    - **limit**: Maximum number of recommendations (1-100)
    - **min_rating**: Minimum rating threshold (0-10)
    """
    try:
        recommendations = engine.recommend_by_genres(genres, limit, min_rating)
        return {
            "total": len(recommendations),
            "movies": recommendations
        }
    except Exception as e:
        logger.error(f"Error getting recommendations by genres: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recommendations/text", response_model=RecommendationResponse, tags=["Recommendations"])
async def get_recommendations_by_text(
    text: str = Query(..., description="Text description to find similar movies"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of recommendations")
):
    """
    Find movies similar to a text description using AI embeddings
    
    - **text**: Text description (e.g., "A movie about space exploration")
    - **limit**: Maximum number of recommendations (1-100)
    """
    try:
        recommendations = engine.get_similar_by_text(text, limit)
        return {
            "total": len(recommendations),
            "movies": recommendations
        }
    except Exception as e:
        logger.error(f"Error getting recommendations by text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trending", response_model=RecommendationResponse, tags=["Discovery"])
async def get_trending_movies(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of movies"),
    min_year: int = Query(2020, ge=1900, le=2030, description="Minimum year")
):
    """
    Get trending/popular movies
    
    - **limit**: Maximum number of movies (1-100)
    - **min_year**: Minimum year threshold
    """
    try:
        movies = engine.get_trending_movies(limit, min_year)
        return {
            "total": len(movies),
            "movies": movies
        }
    except Exception as e:
        logger.error(f"Error getting trending movies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/top-rated", response_model=RecommendationResponse, tags=["Discovery"])
async def get_top_rated_movies(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of movies"),
    min_votes: int = Query(100, ge=0, description="Minimum vote count")
):
    """
    Get top rated movies
    
    - **limit**: Maximum number of movies (1-100)
    - **min_votes**: Minimum vote count threshold
    """
    try:
        movies = engine.get_top_rated_movies(limit, min_votes)
        return {
            "total": len(movies),
            "movies": movies
        }
    except Exception as e:
        logger.error(f"Error getting top rated movies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down API...")
    engine.close()
    logger.info("API shutdown complete")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

