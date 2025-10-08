"""
Generate embeddings for movies and store in PostgreSQL vector database
Uses Ollama with nomic-embed-text model for generating embeddings
"""
import sys
import os
# Add parent directory to path so we can import database module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from multiprocessing import Pool, cpu_count, Manager
from tqdm import tqdm
from database.db import get_db_manager
from database.models import Movie, MovieEmbedding, Genre
import numpy as np
import requests
import json
from config import OLLAMA_HOST, OLLAMA_EMBEDDING_MODEL, OLLAMA_TIMEOUT, EMBEDDING_DIMENSION

# Configure logging - only to file
log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(processName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'generate_embeddings.log')),
    ]
)
logger = logging.getLogger(__name__)


class OllamaEmbedding:
    """
    Ollama embedding client for generating embeddings using nomic-embed-text
    """

    def __init__(self, host=None, model=None, timeout=None):
        self.host = host or OLLAMA_HOST
        self.model = model or OLLAMA_EMBEDDING_MODEL
        self.timeout = timeout or OLLAMA_TIMEOUT
        self.embed_url = f"{self.host}/api/embeddings"

        logger.info(f"Initialized Ollama client: {self.host}, model: {self.model}")

        # Test connection
        self._test_connection()

    def _test_connection(self):
        """Test if Ollama server is running"""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Ollama server is running")
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                if any(self.model in name for name in model_names):
                    logger.info(f"✅ Model '{self.model}' is available")
                else:
                    logger.warning(f"⚠️  Model '{self.model}' not found. Available models: {model_names}")
                    logger.warning(f"   Run: ollama pull {self.model}")
            else:
                logger.error(f"❌ Ollama server returned status {response.status_code}")
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Cannot connect to Ollama at {self.host}")
            logger.error("   Make sure Ollama is running: ollama serve")
            raise
        except Exception as e:
            logger.error(f"❌ Error testing Ollama connection: {e}")
            raise

    def encode(self, text, convert_to_numpy=True):
        """
        Generate embedding for text using Ollama

        Args:
            text: Text to embed
            convert_to_numpy: If True, return numpy array, else return list

        Returns:
            Embedding vector as numpy array or list
        """
        try:
            payload = {
                "model": self.model,
                "prompt": text
            }

            response = requests.post(
                self.embed_url,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                embedding = response.json()['embedding']

                if convert_to_numpy:
                    return np.array(embedding, dtype=np.float32)
                return embedding
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"Timeout while generating embedding (>{self.timeout}s)")
            return None
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def get_sentence_embedding_dimension(self):
        """Get the dimension of embeddings"""
        return EMBEDDING_DIMENSION


def create_movie_text(movie):
    """
    Create a text representation of the movie for embedding
    Combines title, genres, description, and other metadata
    """
    parts = []

    # Title (most important)
    if movie.title:
        parts.append(f"Title: {movie.title}")

    # Year
    if movie.year:
        parts.append(f"Year: {movie.year}")

    # Genres (important for recommendations)
    if movie.genres:
        genre_names = [g.name for g in movie.genres]
        parts.append(f"Genres: {', '.join(genre_names)}")

    # Description (rich semantic information)
    if movie.description_full:
        parts.append(f"Description: {movie.description_full}")
    elif movie.description_intro:
        parts.append(f"Description: {movie.description_intro}")

    # Cast (for actor-based recommendations)
    if movie.casts:
        cast_names = [c.name for c in movie.casts[:5]]  # Top 5 cast members
        parts.append(f"Cast: {', '.join(cast_names)}")

    # Language
    if movie.language:
        parts.append(f"Language: {movie.language}")

    # Rating (quality indicator)
    if movie.rating:
        parts.append(f"Rating: {movie.rating}/10")

    return " | ".join(parts)


def generate_embedding_for_movie(movie_id, ollama_client):
    """
    Generate embedding for a single movie
    Returns (movie_id, embedding_vector) or (movie_id, None) on error
    """
    try:
        db_manager = get_db_manager(pool_size=1, max_overflow=2)

        with db_manager.get_session() as session:
            # Fetch movie with relationships
            movie = session.query(Movie).filter_by(id=movie_id).first()

            if not movie:
                logger.warning(f"Movie {movie_id} not found")
                return (movie_id, None)

            # Create text representation
            movie_text = create_movie_text(movie)

            if not movie_text or len(movie_text.strip()) < 10:
                logger.warning(f"Movie {movie_id} has insufficient text for embedding")
                return (movie_id, None)

            # Generate embedding using Ollama
            embedding = ollama_client.encode(movie_text, convert_to_numpy=True)

            if embedding is None:
                return (movie_id, None)

            return (movie_id, embedding)

    except Exception as e:
        logger.error(f"Error generating embedding for movie {movie_id}: {e}")
        return (movie_id, None)
    finally:
        db_manager.close_all()


def save_embedding(movie_id, embedding_vector):
    """Save embedding to database"""
    try:
        db_manager = get_db_manager(pool_size=1, max_overflow=2)

        with db_manager.get_session() as session:
            # Check if embedding already exists
            existing = session.query(MovieEmbedding).filter_by(movie_id=movie_id).first()

            if existing:
                # Update existing embedding
                existing.embedding = embedding_vector.tolist()
            else:
                # Create new embedding
                new_embedding = MovieEmbedding(
                    movie_id=movie_id,
                    embedding=embedding_vector.tolist()
                )
                session.add(new_embedding)

            session.commit()
            return True

    except Exception as e:
        logger.error(f"Error saving embedding for movie {movie_id}: {e}")
        return False
    finally:
        db_manager.close_all()


def process_movie_batch(args):
    """
    Process a batch of movies - generate and save embeddings
    Each process creates its own Ollama client

    Args:
        args: Tuple of (movie_ids, counter_dict) for real-time progress updates
    """
    movie_ids, counter_dict = args

    # Create Ollama client for this process
    ollama_client = OllamaEmbedding()

    results = {'success': 0, 'failed': 0, 'skipped': 0}

    for movie_id in movie_ids:
        try:
            # Check if embedding already exists
            db_manager = get_db_manager(pool_size=1, max_overflow=2)
            with db_manager.get_session() as session:
                existing = session.query(MovieEmbedding).filter_by(movie_id=movie_id).first()
                if existing:
                    results['skipped'] += 1
                    with counter_dict['lock']:
                        counter_dict['skipped'] += 1
                        counter_dict['completed'] += 1
                    db_manager.close_all()
                    continue
            db_manager.close_all()

            # Generate embedding
            movie_id, embedding = generate_embedding_for_movie(movie_id, ollama_client)

            if embedding is not None:
                # Save to database
                if save_embedding(movie_id, embedding):
                    results['success'] += 1
                    with counter_dict['lock']:
                        counter_dict['success'] += 1
                        counter_dict['completed'] += 1
                else:
                    results['failed'] += 1
                    with counter_dict['lock']:
                        counter_dict['failed'] += 1
                        counter_dict['completed'] += 1
            else:
                results['failed'] += 1
                with counter_dict['lock']:
                    counter_dict['failed'] += 1
                    counter_dict['completed'] += 1

        except Exception as e:
            logger.error(f"Error processing movie {movie_id}: {e}")
            results['failed'] += 1
            with counter_dict['lock']:
                counter_dict['failed'] += 1
                counter_dict['completed'] += 1

    return results


def get_movies_without_embeddings():
    """Get list of movie IDs that don't have embeddings yet"""
    db_manager = get_db_manager()

    with db_manager.get_session() as session:
        # Find movies without embeddings
        movies_without_embeddings = session.query(Movie.id).outerjoin(
            MovieEmbedding, Movie.id == MovieEmbedding.movie_id
        ).filter(
            MovieEmbedding.movie_id.is_(None)
        ).all()

        movie_ids = [m.id for m in movies_without_embeddings]

    return movie_ids





def main(batch_size=None, max_workers=None, force_regenerate=False):
    """
    Main function to generate embeddings for all movies

    Args:
        batch_size: Number of movies per batch
        max_workers: Number of parallel workers (None = cpu_count)
        force_regenerate: If True, regenerate all embeddings
    """
    import time
    from config import EMBEDDING_BATCH_SIZE, MAX_WORKERS as DEFAULT_WORKERS

    batch_size = batch_size or EMBEDDING_BATCH_SIZE
    max_workers = max_workers or DEFAULT_WORKERS

    start_time = time.time()

    print("\n" + "=" * 60)
    print("🧠 Movie Embedding Generator (Ollama)")
    print("=" * 60)
    print(f"🔗 Using Ollama at: {OLLAMA_HOST}")
    print(f"🤖 Model: {OLLAMA_EMBEDDING_MODEL}")
    print(f"📊 Embedding dimension: {EMBEDDING_DIMENSION}")

    logger.info("=" * 60)
    logger.info("Movie Embedding Generator Started (Ollama)")
    logger.info("=" * 60)
    logger.info(f"Using Ollama at: {OLLAMA_HOST}")
    logger.info(f"Model: {OLLAMA_EMBEDDING_MODEL}")
    logger.info(f"Embedding dimension: {EMBEDDING_DIMENSION}")

    # Get movies that need embeddings
    if force_regenerate:
        db_manager = get_db_manager()
        with db_manager.get_session() as session:
            movie_ids = [m.id for m in session.query(Movie.id).all()]
        db_manager.close_all()
        print(f"🔄 Force regenerate mode: Processing all {len(movie_ids)} movies")
        logger.info(f"Force regenerate mode: Processing all {len(movie_ids)} movies")
    else:
        movie_ids = get_movies_without_embeddings()
        print(f"🔍 Found {len(movie_ids)} movies without embeddings")
        logger.info(f"Found {len(movie_ids)} movies without embeddings")

    if not movie_ids:
        print("\n✅ All movies already have embeddings!")
        logger.info("All movies already have embeddings!")
        return

    # Split into batches
    batches = [movie_ids[i:i + batch_size] for i in range(0, len(movie_ids), batch_size)]

    print(f"\n📊 Processing {len(movie_ids)} movies in {len(batches)} batches")
    print(f"⚙️  Using {max_workers} parallel workers")
    print(f"📝 Detailed logs: logs/generate_embeddings.log\n")

    logger.info(f"Processing {len(movie_ids)} movies in {len(batches)} batches")
    logger.info(f"Using {max_workers} parallel workers")

    # Create shared counter for real-time progress updates
    manager = Manager()
    counter_dict = manager.dict()
    counter_dict['lock'] = manager.Lock()
    counter_dict['completed'] = 0
    counter_dict['success'] = 0
    counter_dict['failed'] = 0
    counter_dict['skipped'] = 0

    # Prepare arguments for workers (batch + counter)
    batch_args = [(batch, counter_dict) for batch in batches]

    with tqdm(total=len(movie_ids), desc="Generating embeddings", unit="movie",
              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}] {postfix}',
              position=0, leave=True) as pbar:

        with Pool(processes=max_workers) as pool:
            # Start async processing
            async_result = pool.map_async(process_movie_batch, batch_args)

            # Poll for progress updates
            last_completed = 0
            while not async_result.ready():
                current_completed = counter_dict['completed']
                if current_completed > last_completed:
                    pbar.update(current_completed - last_completed)
                    pbar.set_postfix({
                        '✓': counter_dict['success'],
                        '⊘': counter_dict['skipped'],
                        '✗': counter_dict['failed']
                    })
                    last_completed = current_completed
                time.sleep(0.1)  # Check every 100ms

            # Final update
            current_completed = counter_dict['completed']
            if current_completed > last_completed:
                pbar.update(current_completed - last_completed)
                pbar.set_postfix({
                    '✓': counter_dict['success'],
                    '⊘': counter_dict['skipped'],
                    '✗': counter_dict['failed']
                })

            # Get final results
            async_result.get()

    total_success = counter_dict['success']
    total_failed = counter_dict['failed']
    total_skipped = counter_dict['skipped']

    elapsed_time = time.time() - start_time

    print("\n" + "=" * 60)
    print("✅ Movie Embedding Generator Completed")
    print("=" * 60)
    print(f"📊 Total movies processed: {total_success + total_failed + total_skipped}")
    print(f"   ✓  Successfully generated: {total_success}")
    print(f"   ⊘  Skipped (already exist): {total_skipped}")
    print(f"   ✗  Failed: {total_failed}")
    print(f"⏱️  Time elapsed: {elapsed_time:.2f} seconds")
    if total_success > 0:
        print(f"⚡ Average speed: {total_success / elapsed_time:.2f} embeddings/second")
    print("=" * 60 + "\n")

    logger.info("=" * 60)
    logger.info("Movie Embedding Generator Completed")
    logger.info(f"Total movies processed: {total_success + total_failed + total_skipped}")
    logger.info(f"Successfully generated: {total_success}")
    logger.info(f"Skipped (already exist): {total_skipped}")
    logger.info(f"Failed: {total_failed}")
    logger.info(f"Time elapsed: {elapsed_time:.2f} seconds")
    if total_success > 0:
        logger.info(f"Average speed: {total_success / elapsed_time:.2f} embeddings/second")
    logger.info("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate embeddings for movies using Ollama')
    parser.add_argument('--batch-size', type=int, default=None,
                       help='Number of movies per batch (default: from .env)')
    parser.add_argument('--workers', type=int, default=None,
                       help='Number of parallel workers (default: from .env)')
    parser.add_argument('--force', action='store_true',
                       help='Force regenerate all embeddings')

    args = parser.parse_args()

    main(
        batch_size=args.batch_size,
        max_workers=args.workers,
        force_regenerate=args.force
    )
