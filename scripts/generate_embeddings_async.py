"""
Async version of embedding generation for better performance
Uses asyncio for concurrent requests to Ollama
"""
import asyncio
import aiohttp
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from typing import List, Dict
from tqdm import tqdm
import numpy as np

from database.db import get_db_manager
from database.models import Movie, MovieEmbedding
from config import OLLAMA_HOST, OLLAMA_EMBEDDING_MODEL, OLLAMA_TIMEOUT

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/generate_embeddings_async.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AsyncEmbeddingGenerator:
    """Async embedding generator using aiohttp for concurrent requests"""
    
    def __init__(self, max_concurrent: int = 10):
        """
        Initialize async generator
        
        Args:
            max_concurrent: Maximum number of concurrent requests
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.db_manager = get_db_manager()
    
    def check_existing_embedding(self, movie_id: int) -> bool:
        """
        Check if embedding already exists for a movie

        Args:
            movie_id: Movie ID to check

        Returns:
            True if embedding exists, False otherwise
        """
        with self.db_manager.get_session() as session:
            existing = session.query(MovieEmbedding).filter_by(movie_id=movie_id).first()
            return existing is not None

    async def generate_embedding(self, session: aiohttp.ClientSession,
                                text: str, movie_id: int, skip_existing: bool = True,
                                max_retries: int = 2) -> Dict:
        """
        Generate embedding for a single text using async request with retry logic

        Args:
            session: aiohttp session
            text: Text to generate embedding for
            movie_id: Movie ID for tracking
            skip_existing: Skip if embedding already exists
            max_retries: Maximum number of retries on timeout

        Returns:
            Dict with movie_id, embedding, and status
        """
        # Check if embedding already exists
        if skip_existing:
            if await asyncio.to_thread(self.check_existing_embedding, movie_id):
                return {
                    'movie_id': movie_id,
                    'embedding': None,
                    'status': 'skipped'
                }

        # Retry logic for timeouts
        for attempt in range(max_retries + 1):
            async with self.semaphore:  # Limit concurrent requests
                try:
                    payload = {
                        "model": OLLAMA_EMBEDDING_MODEL,
                        "prompt": text
                    }

                    # Increase timeout for retries
                    timeout = OLLAMA_TIMEOUT * (attempt + 1)

                    async with session.post(
                        f"{OLLAMA_HOST}/api/embeddings",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            embedding = np.array(data['embedding'], dtype=np.float32)
                            if attempt > 0:
                                logger.info(f"Successfully generated embedding for movie {movie_id} on retry {attempt}")
                            return {
                                'movie_id': movie_id,
                                'embedding': embedding,
                                'status': 'success'
                            }
                        else:
                            logger.error(f"Ollama API error for movie {movie_id}: {response.status}")
                            return {
                                'movie_id': movie_id,
                                'embedding': None,
                                'status': 'error'
                            }
                except asyncio.TimeoutError:
                    if attempt < max_retries:
                        logger.warning(f"Timeout for movie {movie_id}, retry {attempt + 1}/{max_retries}")
                        await asyncio.sleep(1)  # Brief pause before retry
                        continue
                    else:
                        logger.error(f"Timeout generating embedding for movie {movie_id} after {max_retries} retries")
                        return {
                            'movie_id': movie_id,
                            'embedding': None,
                            'status': 'timeout'
                        }
                except Exception as e:
                    logger.error(f"Error generating embedding for movie {movie_id}: {e}")
                    return {
                        'movie_id': movie_id,
                        'embedding': None,
                        'status': 'error'
                    }

        # Should not reach here
        return {
            'movie_id': movie_id,
            'embedding': None,
            'status': 'error'
        }
    
    def get_movie_text(self, movie_id: int) -> str:
        """
        Get text for a movie by ID

        Args:
            movie_id: Movie ID

        Returns:
            Text representation of the movie
        """
        with self.db_manager.get_session() as session:
            movie = session.query(Movie).filter_by(id=movie_id).first()
            if not movie:
                return ""

            text_parts = []
            if movie.title:
                text_parts.append(f"Title: {movie.title}")
            if movie.description_full:
                text_parts.append(f"Description: {movie.description_full}")
            if movie.genres:
                genres = ", ".join([g.name for g in movie.genres])
                text_parts.append(f"Genres: {genres}")

            return " ".join(text_parts)

    def get_movies_text_batch(self, movie_ids: List[int], batch_size: int = 1000) -> Dict[int, str]:
        """
        Get text for multiple movies in batches

        Args:
            movie_ids: List of movie IDs
            batch_size: Number of movies to fetch per batch

        Returns:
            Dict mapping movie_id to text
        """
        from database.models import Genre

        movie_texts = {}
        total_batches = (len(movie_ids) + batch_size - 1) // batch_size

        # Process in batches to avoid loading too much into memory
        with tqdm(total=len(movie_ids), desc="📖 Loading movie data", unit="movie") as pbar:
            for i in range(0, len(movie_ids), batch_size):
                batch_ids = movie_ids[i:i + batch_size]

                with self.db_manager.get_session() as session:
                    # Only select the fields we need (much faster)
                    movies = session.query(
                        Movie.id,
                        Movie.title,
                        Movie.description_full
                    ).filter(Movie.id.in_(batch_ids)).all()

                    # Get genres separately (faster than eager loading)
                    movie_genres = {}
                    if movies:
                        movie_ids_in_batch = [m.id for m in movies]
                        genres_query = session.query(
                            Movie.id,
                            Genre.name
                        ).join(
                            Movie.genres
                        ).filter(
                            Movie.id.in_(movie_ids_in_batch)
                        ).all()

                        for movie_id, genre_name in genres_query:
                            if movie_id not in movie_genres:
                                movie_genres[movie_id] = []
                            movie_genres[movie_id].append(genre_name)

                    for movie in movies:
                        text_parts = []
                        if movie.title:
                            text_parts.append(f"Title: {movie.title}")
                        if movie.description_full:
                            text_parts.append(f"Description: {movie.description_full}")
                        if movie.id in movie_genres:
                            genres = ", ".join(movie_genres[movie.id])
                            text_parts.append(f"Genres: {genres}")

                        movie_texts[movie.id] = " ".join(text_parts)

                # Update progress
                pbar.update(len(batch_ids))
                pbar.set_postfix({'batches': f'{(i // batch_size) + 1}/{total_batches}'})

        return movie_texts

    async def generate_batch_from_ids(self, movie_ids: List[int], skip_existing: bool = True, batch_size: int = 1000) -> List[Dict]:
        """
        Generate embeddings for a batch of movies from IDs

        Args:
            movie_ids: List of movie IDs
            skip_existing: Skip movies that already have embeddings
            batch_size: Number of movies to load per batch

        Returns:
            List of results with embeddings
        """
        # Fetch all movie texts in batches with progress bar
        movie_texts = await asyncio.to_thread(self.get_movies_text_batch, movie_ids, batch_size)
        print(f"✓ Loaded {len(movie_texts)} movies\n")

        async with aiohttp.ClientSession() as session:
            tasks = []
            for movie_id in movie_ids:
                text = movie_texts.get(movie_id, "")
                if text:
                    # Create task
                    task = self.generate_embedding(session, text, movie_id, skip_existing)
                    tasks.append(task)

            # Execute all tasks concurrently with progress bar
            results = []
            stats = {'success': 0, 'failed': 0, 'skipped': 0}

            with tqdm(total=len(tasks), desc="Generating embeddings", unit="movie") as pbar:
                for coro in asyncio.as_completed(tasks):
                    result = await coro
                    results.append(result)

                    # Update stats
                    if result['status'] == 'success':
                        stats['success'] += 1
                    elif result['status'] == 'skipped':
                        stats['skipped'] += 1
                    else:
                        stats['failed'] += 1

                    # Update progress bar with stats
                    pbar.update(1)
                    pbar.set_postfix({
                        '✓': stats['success'],
                        '⊘': stats['skipped'],
                        '✗': stats['failed']
                    })

            return results

    async def generate_batch_from_data(self, movie_data: List[Dict], skip_existing: bool = True) -> List[Dict]:
        """
        Generate embeddings for a batch of movies concurrently from prepared data

        Args:
            movie_data: List of dicts with 'movie_id' and 'text' keys
            skip_existing: Skip movies that already have embeddings

        Returns:
            List of results with embeddings
        """
        async with aiohttp.ClientSession() as session:
            tasks = []
            for data in movie_data:
                # Create task
                task = self.generate_embedding(session, data['text'], data['movie_id'], skip_existing)
                tasks.append(task)

            # Execute all tasks concurrently with progress bar
            results = []
            stats = {'success': 0, 'failed': 0, 'skipped': 0}

            with tqdm(total=len(tasks), desc="Generating embeddings", unit="movie") as pbar:
                for coro in asyncio.as_completed(tasks):
                    result = await coro
                    results.append(result)

                    # Update stats
                    if result['status'] == 'success':
                        stats['success'] += 1
                    elif result['status'] == 'skipped':
                        stats['skipped'] += 1
                    else:
                        stats['failed'] += 1

                    # Update progress bar with stats
                    pbar.update(1)
                    pbar.set_postfix({
                        '✓': stats['success'],
                        '⊘': stats['skipped'],
                        '✗': stats['failed']
                    })

            return results
    
    def save_embeddings(self, results: List[Dict]) -> Dict[str, int]:
        """
        Save embeddings to database

        Args:
            results: List of embedding results

        Returns:
            Dict with counts of success/failed/skipped
        """
        stats = {'success': 0, 'failed': 0, 'skipped': 0}

        with self.db_manager.get_session() as session:
            for result in results:
                if result['status'] == 'skipped':
                    stats['skipped'] += 1
                elif result['status'] == 'success' and result['embedding'] is not None:
                    try:
                        # Check if embedding already exists
                        existing = session.query(MovieEmbedding).filter_by(
                            movie_id=result['movie_id']
                        ).first()

                        if existing:
                            # Update existing embedding
                            existing.embedding = result['embedding']
                        else:
                            # Create new embedding
                            embedding = MovieEmbedding(
                                movie_id=result['movie_id'],
                                embedding=result['embedding']
                            )
                            session.add(embedding)

                        session.commit()
                        stats['success'] += 1
                    except Exception as e:
                        logger.error(f"Error saving embedding for movie {result['movie_id']}: {e}")
                        session.rollback()
                        stats['failed'] += 1
                else:
                    stats['failed'] += 1

        return stats
    
    def close(self):
        """Close database connections"""
        self.db_manager.close_all()


async def main():
    """Main async function"""
    import argparse
    import time

    parser = argparse.ArgumentParser(description='Generate embeddings asynchronously using Ollama')
    parser.add_argument('--concurrent', type=int, default=10,
                       help='Maximum concurrent requests (default: 10)')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Number of movies to load per batch (default: 1000)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of movies to process')
    parser.add_argument('--force', action='store_true',
                       help='Force regenerate embeddings even if they already exist')

    args = parser.parse_args()

    # Initialize generator
    generator = AsyncEmbeddingGenerator(max_concurrent=args.concurrent)

    # Skip existing by default (unless --force is used)
    skip_existing = not args.force

    try:
        # Get movie IDs first (fast query)
        with generator.db_manager.get_session() as session:
            if skip_existing:
                # Get only movies without embeddings
                movie_ids = session.query(Movie.id).outerjoin(
                    MovieEmbedding, Movie.id == MovieEmbedding.movie_id
                ).filter(
                    MovieEmbedding.movie_id.is_(None)
                ).all()
                movie_ids = [mid[0] for mid in movie_ids]
            else:
                # Get all movie IDs
                movie_ids = session.query(Movie.id).all()
                movie_ids = [mid[0] for mid in movie_ids]

            if args.limit:
                movie_ids = movie_ids[:args.limit]

            logger.info(f"Found {len(movie_ids)} movies to process")

            if not movie_ids:
                logger.info("No movies to process")
                return

        # Print header
        print("\n" + "="*60)
        print("🧠 Movie Embedding Generator (Async)")
        print("="*60)
        print(f"📊 Total movies to process: {len(movie_ids):,}")
        print(f"⚡ Concurrent requests: {args.concurrent}")
        print(f"📦 Batch size: {args.batch_size:,}")
        print(f"🔄 Skip existing: {'No (--force)' if args.force else 'Yes'}")
        print(f"📝 Detailed logs: logs/generate_embeddings_async.log\n")

        logger.info(f"Processing {len(movie_ids)} movies")
        logger.info(f"Using {args.concurrent} concurrent requests")
        logger.info(f"Batch size: {args.batch_size}")
        logger.info(f"Skip existing: {skip_existing}")

        # Start timer
        start_time = time.time()

        # Generate embeddings from movie IDs
        results = await generator.generate_batch_from_ids(movie_ids, skip_existing=skip_existing, batch_size=args.batch_size)

        # Save embeddings (only saves successful ones, counts are already tracked)
        print("\n💾 Saving embeddings to database...")
        stats = generator.save_embeddings(results)

        elapsed_time = time.time() - start_time

        # Print summary
        print("\n" + "="*60)
        print("✅ Movie Embedding Generator Completed")
        print("="*60)
        print(f"📊 Total movies processed: {stats['success'] + stats['failed'] + stats['skipped']:,}")
        print(f"   ✓  Successfully generated: {stats['success']:,}")
        print(f"   ⊘  Skipped (already exist): {stats['skipped']:,}")
        print(f"   ✗  Failed: {stats['failed']:,}")
        print(f"⏱️  Time elapsed: {elapsed_time:.2f} seconds")
        if stats['success'] > 0:
            print(f"⚡ Average speed: {stats['success'] / elapsed_time:.2f} embeddings/second")
        print("="*60 + "\n")

        logger.info("="*60)
        logger.info("Movie Embedding Generator Completed")
        logger.info(f"Total movies processed: {stats['success'] + stats['failed'] + stats['skipped']:,}")
        logger.info(f"Successfully generated: {stats['success']:,}")
        logger.info(f"Skipped (already exist): {stats['skipped']:,}")
        logger.info(f"Failed: {stats['failed']:,}")
        logger.info(f"Time elapsed: {elapsed_time:.2f} seconds")
        if stats['success'] > 0:
            logger.info(f"Average speed: {stats['success'] / elapsed_time:.2f} embeddings/second")
        logger.info("="*60)

    finally:
        generator.close()


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())

