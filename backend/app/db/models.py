"""Database tables (CPE-FR-01). See docs/ARCHITECTURE.md section 4 for the ERD.

Foreign keys use ON DELETE CASCADE, so deleting a session removes its messages
and their traits, and deleting a document removes its chunks.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    MetaData,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Size of each embedding vector. Fixed by the embedding model (ADR-0007: nomic-embed-text).
EMBEDDING_DIMENSIONS = 768

# Predictable constraint names, so migrations are the same on every machine.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class ChatSession(Base):
    """One conversation."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    title: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Message(Base):
    """One user or assistant message. ``seq`` is the order inside the session (ADR-0003)."""

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("session_id", "seq"),
        CheckConstraint("seq > 0", name="seq_positive"),
        CheckConstraint("role IN ('user', 'assistant')", name="role"),
        CheckConstraint(
            "status IS NULL OR status IN ('pending', 'answered', 'failed')", name="status"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    seq: Mapped[int]
    role: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    # User messages only: pending until answered.
    status: Mapped[str | None] = mapped_column(Text)
    # Assistant messages only. grounded is null on the conversational route.
    grounded: Mapped[bool | None]
    evaluation_retries: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExtractedTrait(Base):
    """A trait found in the conversation, linked to the user message that triggered it."""

    __tablename__ = "extracted_traits"
    __table_args__ = (
        # Re-running extraction for the same message cannot create duplicates.
        UniqueConstraint("source_message_id", "trait"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    source_message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE")
    )
    trait: Mapped[str] = mapped_column(Text)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    """One corpus file. The unique sha256 stops the same file being ingested twice."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    source: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    licence: Mapped[str | None] = mapped_column(Text)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class VectorMemory(Base):
    """One chunk of a corpus document, with its embedding and full-text search vector."""

    __tablename__ = "vector_memories"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index"),
        CheckConstraint("page_end >= page_start", name="page_order"),
        Index(
            "ix_vector_memories_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_vector_memories_content_tsv", "content_tsv", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int]
    page_start: Mapped[int]
    page_end: Mapped[int]
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int]
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    embedding_model: Mapped[str] = mapped_column(Text)
    # Filled in by PostgreSQL from content; used for keyword search.
    content_tsv: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', content)", persisted=True)
    )
