from sqlalchemy import (
    Column, Integer, String, Float, Text, BigInteger, ForeignKey,
    DateTime, Boolean, Numeric, TIMESTAMP
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class Movie(Base):
    __tablename__ = "movies"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    external_id = Column(Integer, unique=True, nullable=False)
    imdb_code = Column(Text)
    title = Column(Text, nullable=False)
    title_english = Column(Text)
    title_long = Column(Text)
    slug = Column(Text, unique=True)
    year = Column(Integer)
    rating = Column(Numeric(3, 1))
    runtime = Column(Integer)
    description_intro = Column(Text)
    description_full = Column(Text)
    yt_trailer_code = Column(Text)
    language = Column(Text)
    mpa_rating = Column(Text)
    like_count = Column(Integer, default=0)
    background_image = Column(Text)
    background_image_original = Column(Text)
    small_cover_image = Column(Text)
    medium_cover_image = Column(Text)
    large_cover_image = Column(Text)
    date_uploaded = Column(TIMESTAMP)
    date_uploaded_unix = Column(BigInteger)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    embedding = relationship("MovieEmbedding", uselist=False, back_populates="movie", cascade="all, delete-orphan")
    genres = relationship("Genre", secondary="movie_genres", back_populates="movies")
    casts = relationship("Cast", secondary="movie_casts", back_populates="movies")
    torrents = relationship("Torrent", back_populates="movie", cascade="all, delete-orphan")


class MovieEmbedding(Base):
    __tablename__ = "movie_embeddings"

    movie_id = Column(BigInteger, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True)
    embedding = Column(Vector(768))  # Nomic-embed-text uses 768 dims

    movie = relationship("Movie", back_populates="embedding")


class Genre(Base):
    __tablename__ = "genres"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, unique=True, nullable=False)

    movies = relationship("Movie", secondary="movie_genres", back_populates="genres")


class MovieGenre(Base):
    __tablename__ = "movie_genres"

    movie_id = Column(BigInteger, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True)
    genre_id = Column(Integer, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True)


class Cast(Base):
    __tablename__ = "casts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    imdb_code = Column(Text)
    url_small_image = Column(Text)

    movies = relationship("Movie", secondary="movie_casts", back_populates="casts")


class MovieCast(Base):
    __tablename__ = "movie_casts"

    movie_id = Column(BigInteger, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True)
    cast_id = Column(Integer, ForeignKey("casts.id", ondelete="CASCADE"), primary_key=True)
    character_name = Column(Text)


class Torrent(Base):
    __tablename__ = "torrents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    movie_id = Column(BigInteger, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    url = Column(Text)
    hash = Column(Text)
    quality = Column(Text)
    type = Column(Text)
    is_repack = Column(Boolean)
    video_codec = Column(Text)
    bit_depth = Column(Text)
    audio_channels = Column(Text)
    seeds = Column(Integer)
    peers = Column(Integer)
    size = Column(Text)
    size_bytes = Column(BigInteger)
    date_uploaded = Column(TIMESTAMP)
    date_uploaded_unix = Column(BigInteger)

    movie = relationship("Movie", back_populates="torrents")
