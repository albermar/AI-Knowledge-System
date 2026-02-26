# app/infra/db/models.py

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    String,
    Text,
    DateTime,
    Integer,
    Float,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.db.base import MyBase


# =========================
# Organization (root tenant)
# =========================

class Organization(MyBase):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    documents: Mapped[List["Document"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    queries: Mapped[List["Query"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    llm_usages: Mapped[List["LLMUsage"]] = relationship(back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name})>"


# =========================
# Document (owned by org)
# =========================

class Document(MyBase):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="documents")
    chunks: Mapped[List["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_documents_org_id_created_at", "organization_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title={self.title})>"


# =========================
# Chunk (belongs to document)
# =========================

class Chunk(MyBase):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    document: Mapped["Document"] = relationship(back_populates="chunks")
    query_links: Mapped[List["QueryChunk"]] = relationship(back_populates="chunk", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunks_document_id_chunk_index"),
        Index("ix_chunks_document_id_chunk_index", "document_id", "chunk_index"),
    )

    def __repr__(self) -> str:
        return f"<Chunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"


# =========================
# Query (belongs to org)
# =========================

class Query(MyBase):
    __tablename__ = "queries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="queries")
    query_chunks: Mapped[List["QueryChunk"]] = relationship(back_populates="query", cascade="all, delete-orphan")
    llm_usages: Mapped[List["LLMUsage"]] = relationship(back_populates="query", cascade="all, delete-orphan")

    # Convenience many-to-many (read) via association table
    chunks: Mapped[List["Chunk"]] = relationship("Chunk", secondary="query_chunks", viewonly=True)

    __table_args__ = (
        Index("ix_queries_org_id_created_at", "organization_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Query(id={self.id}, organization_id={self.organization_id})>"


# ==========================================
# QueryChunk (association table + extra data)
# ==========================================

class QueryChunk(MyBase):
    __tablename__ = "query_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)              # 1..k ordering in retrieval
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)    # similarity score, if you store it
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    query: Mapped["Query"] = relationship(back_populates="query_chunks")
    chunk: Mapped["Chunk"] = relationship(back_populates="query_links")

    __table_args__ = (
        UniqueConstraint("query_id", "chunk_id", name="uq_query_chunks_query_id_chunk_id"),
        UniqueConstraint("query_id", "rank", name="uq_query_chunks_query_id_rank"),
        Index("ix_query_chunks_query_id_rank", "query_id", "rank"),
        Index("ix_query_chunks_chunk_id", "chunk_id"),
    )

    def __repr__(self) -> str:
        return f"<QueryChunk(query_id={self.query_id}, chunk_id={self.chunk_id}, rank={self.rank})>"


# =========================
# LLMUsage (cost / telemetry)
# =========================

class LLMUsage(MyBase):
    __tablename__ = "llm_usages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    query_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("queries.id", ondelete="SET NULL"), nullable=True, index=True)

    provider: Mapped[str] = mapped_column(String(50), nullable=False)       # e.g. "openai"
    model: Mapped[str] = mapped_column(String(100), nullable=False)         # e.g. "gpt-4.1-mini"
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True) # store if you calculate costs
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="llm_usages")
    query: Mapped[Optional["Query"]] = relationship(back_populates="llm_usages")

    __table_args__ = (
        Index("ix_llm_usages_org_id_created_at", "organization_id", "created_at"),
        Index("ix_llm_usages_query_id_created_at", "query_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<LLMUsage(id={self.id}, provider={self.provider}, model={self.model}, total_tokens={self.total_tokens})>"