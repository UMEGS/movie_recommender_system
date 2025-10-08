# config.py
"""
Application configuration loaded from .env file
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "dbname": os.getenv("DB_NAME", "postgres")
}

# Database Connection Pool Settings
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 10))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 20))

# YTS API Configuration
YTS_API_URL = os.getenv("YTS_API_URL", "https://yts.mx/api/v2")
YTS_BATCH_SIZE = int(os.getenv("YTS_BATCH_SIZE", 50))
YTS_MAX_PAGES = int(os.getenv("YTS_MAX_PAGES", 100))

# Ollama Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", 120))

# Embedding Configuration
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", 768))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", 100))

# Multiprocessing Configuration
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 16))
FETCH_BATCH_SIZE = int(os.getenv("FETCH_BATCH_SIZE", 50))

# Application Settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Legacy compatibility
BATCH_SIZE = YTS_BATCH_SIZE
MAX_PAGES = YTS_MAX_PAGES
MAX_THREADS = MAX_WORKERS
