-- apt update
-- apt install -y postgresql-14-pgvector

-- service postgresql restart
-- or, if your container uses the postgres process directly:

-- pkill -f postgres && postgres &

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- ======================================
--  MOVIES TABLE
-- ======================================
CREATE TABLE movies (
    id BIGSERIAL PRIMARY KEY,
    external_id INT UNIQUE,
    imdb_code TEXT,
    title TEXT NOT NULL,
    title_english TEXT,
    title_long TEXT,
    slug TEXT UNIQUE,
    year INT,
    rating NUMERIC(3,1),
    runtime INT,
    description_intro TEXT,
    description_full TEXT,
    yt_trailer_code TEXT,
    language TEXT,
    mpa_rating TEXT,
    like_count INT DEFAULT 0,
    background_image TEXT,
    background_image_original TEXT,
    small_cover_image TEXT,
    medium_cover_image TEXT,
    large_cover_image TEXT,
    date_uploaded TIMESTAMP,
    date_uploaded_unix BIGINT,
    search_vector tsvector, -- for full text search
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for full-text search
CREATE INDEX idx_movies_search ON movies USING gin(search_vector);

-- Trigger to auto-update search vector
CREATE FUNCTION movies_search_trigger() RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    to_tsvector('english',
      coalesce(NEW.title,'') || ' ' ||
      coalesce(NEW.description_full,'') || ' ' ||
      coalesce(NEW.description_intro,'')
    );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_movies_search
BEFORE INSERT OR UPDATE ON movies
FOR EACH ROW EXECUTE FUNCTION movies_search_trigger();


-- ======================================
--  GENRES
-- ======================================
CREATE TABLE genres (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE movie_genres (
    movie_id BIGINT REFERENCES movies(id) ON DELETE CASCADE,
    genre_id INT REFERENCES genres(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, genre_id)
);

-- ======================================
--  CASTS
-- ======================================
CREATE TABLE casts (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    imdb_code TEXT,
    url_small_image TEXT
);

CREATE TABLE movie_casts (
    movie_id BIGINT REFERENCES movies(id) ON DELETE CASCADE,
    cast_id INT REFERENCES casts(id) ON DELETE CASCADE,
    character_name TEXT,
    PRIMARY KEY (movie_id, cast_id)
);

-- ======================================
--  TORRENTS
-- ======================================
CREATE TABLE torrents (
    id SERIAL PRIMARY KEY,
    movie_id BIGINT REFERENCES movies(id) ON DELETE CASCADE,
    url TEXT,
    hash TEXT,
    quality TEXT,
    type TEXT,
    is_repack BOOLEAN,
    video_codec TEXT,
    bit_depth TEXT,
    audio_channels TEXT,
    seeds INT,
    peers INT,
    size TEXT,
    size_bytes BIGINT,
    date_uploaded TIMESTAMP,
    date_uploaded_unix BIGINT
);

-- ======================================
--  EMBEDDINGS (for recommendations)
-- ======================================
-- Table for movie embeddings
CREATE TABLE movie_embeddings (
    movie_id BIGINT PRIMARY KEY REFERENCES movies(id) ON DELETE CASCADE,
    embedding VECTOR(768)  -- 768 dimensions for nomic-embed-text
);

-- Create vector index for fast similarity search
CREATE INDEX idx_movie_embeddings_vector
ON movie_embeddings
USING ivfflat (embedding vector_l2_ops)
WITH (lists = 100);

-- Optional: Also create a basic GIN index for fallback similarity
CREATE INDEX idx_movie_embeddings_cosine
ON movie_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);