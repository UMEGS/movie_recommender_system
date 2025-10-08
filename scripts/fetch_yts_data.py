"""
YTS Movie Data Fetcher with Multiprocessing
Fetches movie data from YTS API and stores in PostgreSQL database using ORM
"""
import sys
import os
# Add parent directory to path so we can import database module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from multiprocessing import Pool, cpu_count, Manager
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import logging
from tqdm import tqdm
from database.db import get_db_manager

# Configure logging
log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(processName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'fetch_yts_data.log')),
    ]
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


def process_movie_batch(args):
    """
    Process a batch of movie IDs - fetch details and save to DB using ORM
    Each process creates its own database manager instance

    Args:
        args: Tuple of (movie_ids_batch, counter_dict) for real-time progress updates
    """
    movie_ids_batch, counter_dict = args

    import os
    import logging

    process_name = f"Worker-{os.getpid()}"
    process_logger = logging.getLogger(__name__)
    results = {'success': 0, 'failed': 0, 'skipped': 0}

    # Create database manager for this process
    db_manager = get_db_manager(pool_size=2, max_overflow=5)

    try:
        batch_size = len(movie_ids_batch)
        process_logger.debug(f"{process_name}: Processing batch of {batch_size} movies (IDs: {movie_ids_batch[0]}-{movie_ids_batch[-1]})")

        for idx, movie_id in enumerate(movie_ids_batch, 1):
            try:
                # Fetch detailed movie data
                movie_data = fetch_movie_details(movie_id)

                if movie_data:
                    # Save to database using ORM
                    success, movie_db_id, message = db_manager.save_movie(movie_data)

                    if success:
                        if message == "already_exists":
                            # Race condition - another worker saved it first
                            results['skipped'] += 1
                            with counter_dict['lock']:
                                counter_dict['skipped'] += 1
                                counter_dict['completed'] += 1
                            process_logger.debug(f"{process_name}: Movie {movie_id} saved by another worker")
                        else:
                            results['success'] += 1
                            with counter_dict['lock']:
                                counter_dict['success'] += 1
                                counter_dict['completed'] += 1
                            process_logger.info(f"{process_name}: ✓ Saved movie {movie_id}: {movie_data.get('title', 'Unknown')} ({idx}/{batch_size})")
                    else:
                        results['failed'] += 1
                        with counter_dict['lock']:
                            counter_dict['failed'] += 1
                            counter_dict['completed'] += 1
                        process_logger.error(f"{process_name}: Failed to save movie {movie_id}: {message}")
                else:
                    results['failed'] += 1
                    with counter_dict['lock']:
                        counter_dict['failed'] += 1
                        counter_dict['completed'] += 1
                    process_logger.warning(f"{process_name}: No data returned for movie {movie_id}")

                # Small delay to avoid rate limiting
                time.sleep(0.1)

            except Exception as e:
                process_logger.error(f"{process_name}: Error processing movie {movie_id}: {e}")
                results['failed'] += 1
                with counter_dict['lock']:
                    counter_dict['failed'] += 1
                    counter_dict['completed'] += 1

        process_logger.info(f"{process_name}: Batch complete - Success: {results['success']}, Skipped: {results['skipped']}, Failed: {results['failed']}")

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


def fetch_page_ids(page, limit=50):
    """Fetch movie IDs from a single page"""
    try:
        data = fetch_movie_list(page=page, limit=limit)
        if data and data.get('movies'):
            return [movie['id'] for movie in data['movies']]
        return []
    except Exception as e:
        logger.error(f"Error fetching page {page}: {e}")
        return []


def collect_all_movie_ids(max_pages=None, parallel_pages=10):
    """
    Collect all movie IDs from the list API using parallel requests

    Args:
        max_pages: Maximum number of pages to fetch (None = all)
        parallel_pages: Number of pages to fetch in parallel (default: 10)
    """
    limit = 50

    # Get total count
    total_count = get_total_movie_count()
    print(f"📚 Total movies available: {total_count:,}")

    if max_pages:
        total_pages = max_pages
    else:
        total_pages = (total_count // limit) + 1

    print(f"🔍 Collecting movie IDs from {total_pages} pages...")

    all_movie_ids = []

    # Create list of all page numbers to fetch
    pages_to_fetch = list(range(1, total_pages + 1))

    # Fetch pages in parallel batches
    with tqdm(total=len(pages_to_fetch), desc="Collecting movie IDs", position=0, leave=True) as pbar:
        with ThreadPoolExecutor(max_workers=parallel_pages) as executor:
            # Submit all pages
            future_to_page = {
                executor.submit(fetch_page_ids, page, limit): page
                for page in pages_to_fetch
            }

            # Collect results as they complete
            for future in as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    movie_ids = future.result()
                    all_movie_ids.extend(movie_ids)
                    pbar.update(1)
                except Exception as e:
                    logger.error(f"Error processing page {page}: {e}")
                    pbar.update(1)

    # Sort by ID to maintain order
    all_movie_ids.sort()

    print(f"✓ Collected {len(all_movie_ids):,} movie IDs\n")
    return all_movie_ids


def main(max_pages=None, batch_size=20, max_workers=None, parallel_pages=20):
    """
    Main function to fetch and store movie data

    Args:
        max_pages: Maximum number of pages to fetch from list API (None = all)
        batch_size: Number of movies to process in each batch
        max_workers: Number of parallel workers (None = cpu_count * 2)
        parallel_pages: Number of pages to fetch in parallel during ID collection (default: 20)
    """
    start_time = time.time()

    print("\n" + "=" * 60)
    print("🎬 YTS Movie Data Fetcher")
    print("=" * 60)

    # Collect all movie IDs (now in parallel!)
    movie_ids = collect_all_movie_ids(max_pages=max_pages, parallel_pages=parallel_pages)

    if not movie_ids:
        print("❌ No movie IDs collected. Exiting.")
        return

    # Check which movies already exist in database (batch check - much faster!)
    print(f"🔍 Checking which movies already exist in database...")
    db_manager = get_db_manager()
    existing_ids = db_manager.get_existing_movie_ids(movie_ids)
    db_manager.close_all()

    # Filter out existing movies
    new_movie_ids = [mid for mid in movie_ids if mid not in existing_ids]

    print(f"✓ Found {len(existing_ids):,} existing movies")
    print(f"📥 Need to fetch {len(new_movie_ids):,} new movies")

    if not new_movie_ids:
        print("\n✅ All movies are already in the database! Nothing to fetch.")
        return

    # Split into batches
    batches = [new_movie_ids[i:i + batch_size] for i in range(0, len(new_movie_ids), batch_size)]

    print(f"\n📊 Processing {len(new_movie_ids):,} movies in {len(batches)} batches")

    # Determine number of workers
    if max_workers is None:
        max_workers = min(cpu_count() * 2, len(batches))

    print(f"⚙️  Using {max_workers} parallel workers")
    print(f"⏱️  Estimated time: {(len(new_movie_ids) * 0.15 / max_workers / 60):.1f} minutes")
    print(f"📝 Detailed logs: logs/fetch_yts_data.log\n")

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

    with tqdm(total=len(new_movie_ids), desc="Fetching movies", unit="movie",
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
    print("✅ YTS Movie Data Fetcher Completed")
    print("=" * 60)
    print(f"📊 Total movies checked: {len(movie_ids):,}")
    print(f"💾 Already in database: {len(existing_ids):,}")
    print(f"📥 Attempted to fetch: {len(new_movie_ids):,}")
    print(f"   ✓  Successfully saved: {total_success:,}")
    print(f"   ⊘  Skipped (race condition): {total_skipped:,}")
    print(f"   ✗  Failed: {total_failed:,}")
    print(f"⏱️  Time elapsed: {elapsed_time:.2f} seconds")
    if (total_success + total_failed) > 0:
        print(f"⚡ Average speed: {(total_success + total_failed) / elapsed_time:.2f} movies/second")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Fetch YTS movie data and store in database')
    parser.add_argument('--max-pages', type=int, default=None,
                       help='Maximum number of pages to fetch (default: all)')
    parser.add_argument('--batch-size', type=int, default=20,
                       help='Number of movies per batch - smaller = more frequent updates (default: 20)')
    parser.add_argument('--workers', type=int, default=None,
                       help='Number of parallel workers (default: cpu_count * 2)')
    parser.add_argument('--parallel-pages', type=int, default=20,
                       help='Number of pages to fetch in parallel during ID collection (default: 20)')

    args = parser.parse_args()

    main(
        max_pages=args.max_pages,
        batch_size=args.batch_size,
        max_workers=args.workers,
        parallel_pages=args.parallel_pages
    )
