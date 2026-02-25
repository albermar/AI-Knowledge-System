import uuid

from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID]				= mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str]					= mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[DateTime]		= mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # relationships
    documents: Mapped[list["Document"]]	    = relationship(back_populates="organization")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID]				= mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID]	= mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    title: Mapped[str]					= mapped_column(String(255), nullable=False)
    source_type: Mapped[str]			= mapped_column(String(32), nullable=False)  # e.g. "pdf", "txt"
    created_at: Mapped[DateTime]		= mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # relationships
    organization: Mapped["Organization"]	= relationship(back_populates="documents")
    chunks: Mapped[list["Chunk"]]			= relationship(back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID]				= mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID]		= mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    # denormalized for fast filtering + tenant safety
    organization_id: Mapped[uuid.UUID]	= mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    chunk_index: Mapped[int]			= mapped_column(Integer, nullable=False)
    text: Mapped[str]					= mapped_column(Text, nullable=False)
    token_count: Mapped[int | None]		= mapped_column(Integer, nullable=True)
    created_at: Mapped[DateTime]		= mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # relationships
    document: Mapped["Document"]			= relationship(back_populates="chunks")
    query_links: Mapped[list["QueryChunk"]]	= relationship(back_populates="chunk", cascade="all, delete-orphan")

    # optional: prevent duplicate chunk_index within same document
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunks_document_chunk_index"),
    )


class Query(Base):
    __tablename__ = "queries"

    id: Mapped[uuid.UUID]				= mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID]	= mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    question: Mapped[str]				= mapped_column(Text, nullable=False)
    answer: Mapped[str | None]			= mapped_column(Text, nullable=True)  # nullable while LLM runs

    latency_ms: Mapped[int | None]		= mapped_column(Integer, nullable=True)
    created_at: Mapped[DateTime]		= mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # relationships
    chunk_links: Mapped[list["QueryChunk"]]	= relationship(back_populates="query", cascade="all, delete-orphan")
    llm_usage: Mapped["LLMUsage | None"]	= relationship(back_populates="query", uselist=False, cascade="all, delete-orphan")


class QueryChunk(Base):
    __tablename__ = "query_chunks"

    # composite primary key = natural identity
    query_id: Mapped[uuid.UUID]			= mapped_column(UUID(as_uuid=True), ForeignKey("queries.id", ondelete="CASCADE"), primary_key=True)
    chunk_id: Mapped[uuid.UUID]			= mapped_column(UUID(as_uuid=True), ForeignKey("chunks.id",  ondelete="CASCADE"), primary_key=True)

    similarity_score: Mapped[float | None]	= mapped_column(Float, nullable=True)
    rank: Mapped[int | None]			= mapped_column(Integer, nullable=True)

    # relationships
    query: Mapped["Query"]				= relationship(back_populates="chunk_links")
    chunk: Mapped["Chunk"]				= relationship(back_populates="query_links")


class LLMUsage(Base):
    __tablename__ = "llm_usage"

    # 1-to-1 with Query: use query_id as PK
    query_id: Mapped[uuid.UUID]			= mapped_column(UUID(as_uuid=True), ForeignKey("queries.id", ondelete="CASCADE"), primary_key=True)

    model_name: Mapped[str]				= mapped_column(String(128), nullable=False)
    prompt_tokens: Mapped[int]			= mapped_column(Integer, nullable=False)
    completion_tokens: Mapped[int]		= mapped_column(Integer, nullable=False)
    total_tokens: Mapped[int]			= mapped_column(Integer, nullable=False)

    # cost tracking
    estimated_cost_usd: Mapped[float]	= mapped_column(Float, nullable=False)

    created_at: Mapped[DateTime]		= mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # relationships
    query: Mapped["Query"]				    = relationship(back_populates="llm_usage")