"""
Test Ollama connection and embedding generation
Run this before generating embeddings for all movies
"""
import sys
import os
# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import json
from config import OLLAMA_HOST, OLLAMA_EMBEDDING_MODEL, OLLAMA_TIMEOUT

def test_ollama_connection():
    """Test if Ollama server is running"""
    print("=" * 60)
    print("Testing Ollama Connection")
    print("=" * 60)
    
    print(f"\n1. Testing connection to {OLLAMA_HOST}...")
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            print("   ✅ Ollama server is running")
            
            # List available models
            models = response.json().get('models', [])
            print(f"\n2. Available models ({len(models)}):")
            for model in models:
                print(f"   - {model['name']}")
            
            # Check if our model is available
            print(f"\n3. Checking for model '{OLLAMA_EMBEDDING_MODEL}'...")
            model_names = [m['name'] for m in models]
            if any(OLLAMA_EMBEDDING_MODEL in name for name in model_names):
                print(f"   ✅ Model '{OLLAMA_EMBEDDING_MODEL}' is available")
            else:
                print(f"   ❌ Model '{OLLAMA_EMBEDDING_MODEL}' not found")
                print(f"   Run: ollama pull {OLLAMA_EMBEDDING_MODEL}")
                return False
        else:
            print(f"   ❌ Ollama server returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Cannot connect to Ollama at {OLLAMA_HOST}")
        print("   Make sure Ollama is running:")
        print("   - Run: ollama serve")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    return True


def test_embedding_generation():
    """Test generating an embedding"""
    print("\n" + "=" * 60)
    print("Testing Embedding Generation")
    print("=" * 60)
    
    test_text = "A sci-fi thriller about dreams and reality starring Leonardo DiCaprio"
    
    print(f"\nTest text: '{test_text}'")
    print(f"Model: {OLLAMA_EMBEDDING_MODEL}")
    print(f"Timeout: {OLLAMA_TIMEOUT}s")
    
    try:
        print("\nGenerating embedding...")
        
        payload = {
            "model": OLLAMA_EMBEDDING_MODEL,
            "prompt": test_text
        }
        
        response = requests.post(
            f"{OLLAMA_HOST}/api/embeddings",
            json=payload,
            timeout=OLLAMA_TIMEOUT
        )
        
        if response.status_code == 200:
            embedding = response.json()['embedding']
            print(f"✅ Embedding generated successfully!")
            print(f"   Dimension: {len(embedding)}")
            print(f"   First 5 values: {embedding[:5]}")
            print(f"   Data type: {type(embedding[0])}")
            
            # Verify dimension
            from config import EMBEDDING_DIMENSION
            if len(embedding) == EMBEDDING_DIMENSION:
                print(f"   ✅ Dimension matches expected: {EMBEDDING_DIMENSION}")
            else:
                print(f"   ⚠️  Dimension mismatch! Expected {EMBEDDING_DIMENSION}, got {len(embedding)}")
                print(f"   Update EMBEDDING_DIMENSION in .env to {len(embedding)}")
            
            return True
        else:
            print(f"❌ Ollama API error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ Timeout while generating embedding (>{OLLAMA_TIMEOUT}s)")
        print("   Try increasing OLLAMA_TIMEOUT in .env")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_database_connection():
    """Test database connection and check for pgvector extension"""
    print("\n" + "=" * 60)
    print("Testing Database Connection")
    print("=" * 60)
    
    try:
        from database.db import get_db_manager
        from database.models import Movie, MovieEmbedding
        from sqlalchemy import text
        
        db_manager = get_db_manager()
        
        print("\n1. Testing database connection...")
        with db_manager.get_session() as session:
            # Test basic connection
            result = session.execute(text("SELECT 1")).scalar()
            print("   ✅ Database connection successful")
            
            # Check for pgvector extension
            print("\n2. Checking for pgvector extension...")
            result = session.execute(
                text("SELECT * FROM pg_extension WHERE extname = 'vector'")
            ).fetchone()
            
            if result:
                print("   ✅ pgvector extension is installed")
            else:
                print("   ❌ pgvector extension not found")
                print("   Run in PostgreSQL: CREATE EXTENSION vector;")
                return False
            
            # Check movies table
            print("\n3. Checking movies table...")
            movie_count = session.query(Movie).count()
            print(f"   ✅ Found {movie_count:,} movies in database")
            
            # Check movie_embeddings table
            print("\n4. Checking movie_embeddings table...")
            embedding_count = session.query(MovieEmbedding).count()
            print(f"   ✅ Found {embedding_count:,} embeddings in database")
            
            if movie_count > 0:
                movies_without_embeddings = movie_count - embedding_count
                print(f"\n   Movies without embeddings: {movies_without_embeddings:,}")
                if movies_without_embeddings > 0:
                    print(f"   Run: python generate_embeddings.py")
            
        db_manager.close_all()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🎬 Movie Recommendation System - Connection Tests")
    print("=" * 60)
    
    results = {
        'ollama': False,
        'embedding': False,
        'database': False
    }
    
    # Test Ollama connection
    results['ollama'] = test_ollama_connection()
    
    # Test embedding generation (only if Ollama is working)
    if results['ollama']:
        results['embedding'] = test_embedding_generation()
    
    # Test database connection
    results['database'] = test_database_connection()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Ollama Connection:      {'✅ PASS' if results['ollama'] else '❌ FAIL'}")
    print(f"Embedding Generation:   {'✅ PASS' if results['embedding'] else '❌ FAIL'}")
    print(f"Database Connection:    {'✅ PASS' if results['database'] else '❌ FAIL'}")
    print("=" * 60)
    
    if all(results.values()):
        print("\n🎉 All tests passed! You're ready to generate embeddings.")
        print("\nNext steps:")
        print("1. Generate embeddings: python generate_embeddings.py")
        print("2. Test recommendations: python recommendation_engine.py --trending")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        if not results['ollama']:
            print("\nOllama setup:")
            print("1. Install: brew install ollama (macOS) or visit ollama.com")
            print("2. Start: ollama serve")
            print(f"3. Pull model: ollama pull {OLLAMA_EMBEDDING_MODEL}")
        if not results['database']:
            print("\nDatabase setup:")
            print("1. Check database connection in .env")
            print("2. Install pgvector: CREATE EXTENSION vector;")
            print("3. Run migrations if needed")
    
    print()


if __name__ == "__main__":
    main()

