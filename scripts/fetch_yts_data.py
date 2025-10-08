"""
YTS Movie Data Fetcher with Multiprocessing
Fetches movie data from YTS API and stores in PostgreSQL database using ORM
"""
import requests
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
import time
import logging
from tqdm import tqdm
from database.db import get_db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(processName)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API Configuration
BASE_URL = "https://yts.mx/api/v2"
LIST_MOVIES_URL = f"{BASE_URL}/list_movies.json"
MOVIE_DETAILS_URL = f"{BASE_URL}/movie_details.json"


def fetch_movie_list(page=1, limit=50):
    """Fetch list of movies from YTS API"""
    try:
        params = {
            'page': page,
            'limit': limit,
            'sort_by': 'id',
            'order_by': 'asc'
        }
        response = requests.get(LIST_MOVIES_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data['status'] == 'ok':
            return data['data']
        return None
    except Exception as e:
        logger.error(f"Error fetching movie list page {page}: {e}")
        return None


def fetch_movie_details(movie_id, imdb_code=None):
    """Fetch detailed movie information including cast"""
    try:
        params = {
            'with_images': 'true',
            'with_cast': 'true'
        }

        if imdb_code:
            params['imdb_id'] = imdb_code
        else:
            params['movie_id'] = movie_id

        response = requests.get(MOVIE_DETAILS_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data['status'] == 'ok':
            return data['data']['movie']
        return None
    except Exception as e:
        logger.error(f"Error fetching details for movie {movie_id}: {e}")
        return None


def process_movie_batch(movie_ids_batch):
    """
    Process a batch of movie IDs - fetch details and save to DB using ORM
    Each process creates its own database manager instance
    """
    results = {'success': 0, 'failed': 0, 'skipped': 0}

    # Create database manager for this process
    db_manager = get_db_manager(pool_size=2, max_overflow=5)

    try:
        for movie_id in movie_ids_batch:
            try:
                # Check if movie already exists (skip if it does)
                if db_manager.movie_exists(movie_id):
                    results['skipped'] += 1
                    logger.debug(f"Movie {movie_id} already exists, skipping...")
                    continue

                # Fetch detailed movie data
                movie_data = fetch_movie_details(movie_id)

                if movie_data:
                    # Save to database using ORM
                    success, movie_db_id, message = db_manager.save_movie(movie_data)

                    if success:
                        if message == "already_exists":
                            results['skipped'] += 1
                        else:
                            results['success'] += 1
                    else:
                        results['failed'] += 1
                        logger.error(f"Failed to save movie {movie_id}: {message}")
                else:
                    results['failed'] += 1

                # Small delay to avoid rate limiting
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error processing movie {movie_id}: {e}")
                results['failed'] += 1

    finally:
        # Clean up database connections for this process
        db_manager.close_all()

    return results





def get_total_movie_count():
    """Get total number of movies available from API"""
    try:
        data = fetch_movie_list(page=1, limit=1)
        if data:
            return data.get('movie_count', 0)
        return 0
    except Exception as e:
        logger.error(f"Error getting total movie count: {e}")
        return 0


def collect_all_movie_ids(max_pages=None):
    """Collect all movie IDs from the list API"""
    logger.info("Collecting all movie IDs from YTS API...")

    all_movie_ids = []
    page = 1
    limit = 50

    # Get total count
    total_count = get_total_movie_count()
    logger.info(f"Total movies available: {total_count}")

    if max_pages:
        total_pages = max_pages
    else:
        total_pages = (total_count // limit) + 1

    with tqdm(total=total_pages, desc="Collecting movie IDs") as pbar:
        while True:
            if max_pages and page > max_pages:
                break

            data = fetch_movie_list(page=page, limit=limit)

            if not data or not data.get('movies'):
                break

            for movie in data['movies']:
                all_movie_ids.append(movie['id'])

            pbar.update(1)
            page += 1
            time.sleep(0.2)  # Rate limiting

    logger.info(f"Collected {len(all_movie_ids)} movie IDs")
    return all_movie_ids


def main(max_pages=None, batch_size=50, max_workers=None):
    """
    Main function to fetch and store movie data

    Args:
        max_pages: Maximum number of pages to fetch from list API (None = all)
        batch_size: Number of movies to process in each batch
        max_workers: Number of parallel workers (None = cpu_count * 2)
    """
    start_time = time.time()

    logger.info("=" * 60)
    logger.info("YTS Movie Data Fetcher Started")
    logger.info("=" * 60)

    # Collect all movie IDs
    movie_ids = collect_all_movie_ids(max_pages=max_pages)

    if not movie_ids:
        logger.error("No movie IDs collected. Exiting.")
        return

    # Split into batches
    batches = [movie_ids[i:i + batch_size] for i in range(0, len(movie_ids), batch_size)]

    logger.info(f"Processing {len(movie_ids)} movies in {len(batches)} batches")

    # Determine number of workers
    if max_workers is None:
        max_workers = min(cpu_count() * 2, len(batches))

    logger.info(f"Using {max_workers} parallel workers")

    # Process batches in parallel
    total_success = 0
    total_failed = 0
    total_skipped = 0

    with tqdm(total=len(batches), desc="Processing batches") as pbar:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_movie_batch, batch): batch for batch in batches}

            for future in as_completed(futures):
                try:
                    result = future.result()
                    total_success += result['success']
                    total_failed += result['failed']
                    total_skipped += result['skipped']
                    pbar.update(1)
                    pbar.set_postfix({
                        'Success': total_success,
                        'Skipped': total_skipped,
                        'Failed': total_failed
                    })
                except Exception as e:
                    logger.error(f"Batch processing error: {e}")
                    pbar.update(1)

    elapsed_time = time.time() - start_time

    logger.info("=" * 60)
    logger.info("YTS Movie Data Fetcher Completed")
    logger.info(f"Total movies processed: {total_success + total_failed + total_skipped}")
    logger.info(f"Successfully saved: {total_success}")
    logger.info(f"Skipped (already exist): {total_skipped}")
    logger.info(f"Failed: {total_failed}")
    logger.info(f"Time elapsed: {elapsed_time:.2f} seconds")
    if (total_success + total_failed) > 0:
        logger.info(f"Average speed: {(total_success + total_failed) / elapsed_time:.2f} movies/second")
    logger.info("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Fetch YTS movie data and store in database')
    parser.add_argument('--max-pages', type=int, default=None,
                       help='Maximum number of pages to fetch (default: all)')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Number of movies per batch (default: 50)')
    parser.add_argument('--workers', type=int, default=None,
                       help='Number of parallel workers (default: cpu_count * 2)')

    args = parser.parse_args()

    main(
        max_pages=args.max_pages,
        batch_size=args.batch_size,
        max_workers=args.workers
    )
