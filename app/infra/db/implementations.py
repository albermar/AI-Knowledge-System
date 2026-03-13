from typing import List
import uuid

from app.domain.types import RetrievedChunk
from app.infra.db.engine import get_db_session
from sqlalchemy.orm import Session

from app.domain.interfaces import DocumentRepositoryInterface, OrganizationRepositoryInterface, QueryRepositoryInterface, ChunkRepositoryInterface, LLMUsageRepositoryInterface, QueryChunkRepositoryInterface
#import orm models as **ORM: 
from app.infra.db.ormmodels import Organization as OrganizationORM, Document as DocumentORM, Query as QueryORM, Chunk as ChunkORM, LLMUsage as LLMUsageORM, QueryChunk as QueryChunkORM 
#import domain entities
from app.domain.entities import Organization, Document, Query, Chunk, LLMUsage, QueryChunk

#✅#
class PostgreSQL_OrganizationRepository(OrganizationRepositoryInterface):
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def _to_entity(self, orm_obj: OrganizationORM) -> Organization:
        return Organization(
            id=orm_obj.id, 
            name=orm_obj.name, 
            created_at=orm_obj.created_at, 
            api_key_hash=orm_obj.api_key_hash
        )
    
    def add(self, organization: Organization) -> None:
        orm_obj = OrganizationORM(
            id=organization.id, 
            name=organization.name, 
            created_at=organization.created_at, 
            api_key_hash=organization.api_key_hash
        )
        self.db_session.add(orm_obj)    
        self.db_session.flush()
        
    def get_by_id (self, id: uuid.UUID) -> Organization | None:
        orm_obj = self.db_session.get(OrganizationORM, id) #get function can return None if not found, which is what we want.
        return None if orm_obj is None else self._to_entity(orm_obj)    
    
    def get_by_name(self, name: str) -> Organization | None:
        orm_obj = (
            self.db_session.query(OrganizationORM)
            .filter_by(name=name)
            .first()
        )
        return None if orm_obj is None else self._to_entity(orm_obj)
    
    def get_by_api_key_hash(self, api_key_hash: str) -> Organization | None:
        orm_obj = (
            self.db_session.query(OrganizationORM)
            .filter_by(api_key_hash=api_key_hash)
            .first()
        )
        return None if orm_obj is None else self._to_entity(orm_obj)
    
    def delete(self, id: uuid.UUID) -> None:
        orm_obj = self.db_session.get(OrganizationORM, id)
        if orm_obj is not None:
            self.db_session.delete(orm_obj)
            self.db_session.flush()

#✅#       
class PostgreSQL_DocumentRepository(DocumentRepositoryInterface):
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    @staticmethod # Because these are just helper functions to convert between ORM and Entity, they don't need access to the instance (self), so we can make them static methods.
    def _to_entity(orm_obj: DocumentORM) -> Document:
        return Document(
            id=orm_obj.id,
            organization_id=orm_obj.organization_id,
            title=orm_obj.title,
            source_type=orm_obj.source_type,
            document_hash=orm_obj.document_hash,
            content=orm_obj.content,
            created_at=orm_obj.created_at
        )
    
    @staticmethod
    def _to_orm(document: Document) -> DocumentORM:
        return DocumentORM(
            id=document.id,
            organization_id=document.organization_id,
            title=document.title,
            source_type=document.source_type,
            document_hash=document.document_hash,
            content=document.content,
            created_at=document.created_at
        )
    
    def add(self, document: Document) -> None:
        orm_obj = self._to_orm(document)
        self.db_session.add(orm_obj)
        self.db_session.flush()

    
    def get_by_hash(self, organization_id: uuid.UUID, document_hash: str) -> Document | None: #double safety with organization_id as a parameter.
        orm_obj = (
            self.db_session.query(DocumentORM).
            filter_by(organization_id = organization_id, document_hash = document_hash)
            .first()
            )        
        return None if orm_obj is None else self._to_entity(orm_obj)
        
    def get_by_id(self, organization_id: uuid.UUID, id: uuid.UUID) -> Document | None: #double safety with organization_id as a parameter.
        #try to return orm object, and if exists return entity object.
        orm_obj = (
            self.db_session.query(DocumentORM)
            .filter_by(id=id, organization_id=organization_id)
            .first()
        )
        return None if orm_obj is None else self._to_entity(orm_obj)
    
    def list_by_organization(self, organization_id: uuid.UUID)  -> List[Document]:
        #fetch orm list with org filter, then convert to entity list.
        orm_objs = (
            self.db_session.query(DocumentORM)
            .filter_by(organization_id=organization_id)
            .all()            
        )
        
        return [self._to_entity(o) for o in orm_objs]

    def delete(self, organization_id: uuid.UUID, id: uuid.UUID) -> None: #double safety with organization_id as a parameter.
        orm_obj = (
            self.db_session.query(DocumentORM)
            .filter_by(id=id, organization_id=organization_id)
            .first()
        )
        if orm_obj is not None:
            self.db_session.delete(orm_obj)
            self.db_session.flush()

#✅#
class PostgreSQL_ChunkRepository(ChunkRepositoryInterface):  
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    @staticmethod
    def _to_entity(orm_obj: ChunkORM) -> Chunk:
        return Chunk(
            document_id=orm_obj.document_id,
            organization_id=orm_obj.organization_id,
            chunk_index=orm_obj.chunk_index,
            content=orm_obj.content,
            token_count=orm_obj.token_count,
            id=orm_obj.id,
            created_at=orm_obj.created_at, 
            embedding=[float(x) for x in orm_obj.embedding])
        
    @staticmethod
    def _to_orm(chunk: Chunk) -> ChunkORM:
        return ChunkORM(
            document_id=chunk.document_id,
            organization_id=chunk.organization_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            token_count=chunk.token_count,
            id=chunk.id,
            created_at=chunk.created_at,
            embedding=chunk.embedding
        )
        
    def add_many(self, chunks: List[Chunk]) -> None:
        # create orm objects from entities, then bulk save.
        orm_objs = [self._to_orm(c) for c in chunks]        
        self.db_session.add_all(orm_objs)
        self.db_session.flush()
    def get_by_document(self, organization_id: uuid.UUID, document_id: uuid.UUID) -> List[Chunk]: #double safety with organization_id as a parameter.
        orm_objs = (
            self.db_session.query(ChunkORM)
            .filter_by(document_id=document_id, organization_id=organization_id)
            .order_by(ChunkORM.chunk_index) # Ensure consistent order by chunk_index
            .all()
        )
        return [self._to_entity(o) for o in orm_objs]
    
    def vector_search(self, organization_id: uuid.UUID, embedded_question: list[float], top_k: int = 5) -> list[RetrievedChunk]:
        distance_expression = ChunkORM.embedding.cosine_distance(embedded_question)
        
        rows = (
        self.db_session.query(
            ChunkORM, 
            distance_expression.label("distance")
            )
        .filter(ChunkORM.organization_id == organization_id)
        .order_by(distance_expression)
        .limit(top_k)
        .all()
        )
        
        #build retrieved chunks with chunk id, content, chunk index and similarity score:
        retrieved_chunks = []

        for orm_obj, distance in rows:
            raw_similarity = 1.0 - float(distance)
            similarity_score = max(0.0, min(1.0, raw_similarity))

            retrieved_chunks.append(
                RetrievedChunk(
                    chunk_id=orm_obj.id,
                    content=orm_obj.content,
                    chunk_index=orm_obj.chunk_index,
                    similarity_score=similarity_score,
                )
            )

        return retrieved_chunks

    def count_by_document_id(self, organization_id: uuid.UUID, document_id: uuid.UUID) -> int:
        count = (
            self.db_session.query(ChunkORM)
            .filter_by(document_id=document_id, organization_id=organization_id)
            .count()
        )
        return count

class PostgreSQL_QueryRepository(QueryRepositoryInterface):
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    @staticmethod
    def _to_entity(orm_obj: QueryORM) -> Query:
        return Query(
            id=orm_obj.id,
            organization_id=orm_obj.organization_id,
            question=orm_obj.question,
            answer=orm_obj.answer,
            latency_ms=orm_obj.latency_ms,
            created_at=orm_obj.created_at
        )
    
    @staticmethod
    def _to_orm(query: Query) -> QueryORM:
        return QueryORM(
            id=query.id,
            organization_id=query.organization_id,
            question=query.question,
            answer=query.answer,
            latency_ms=query.latency_ms,
            created_at=query.created_at
        )
    
    def add(self, query: Query) -> None:
        orm_obj = self._to_orm(query)
        self.db_session.add(orm_obj)
        self.db_session.flush()
    
    def update(self, query: Query) -> None:
        orm_obj = self.db_session.get(QueryORM, query.id)
        if orm_obj is not None:
            orm_obj.question = query.question
            orm_obj.answer = query.answer
            orm_obj.latency_ms = query.latency_ms
            self.db_session.flush()
    
    def get_by_id(self, organization_id: uuid.UUID, id: uuid.UUID) -> Query | None: #double safety with organization_id as a parameter.
        orm_obj = self.db_session.query(QueryORM).filter_by(id=id, organization_id=organization_id).first()
        if orm_obj is not None:
            return self._to_entity(orm_obj)
        return None
    
    def list_by_organization_id(self, organization_id: uuid.UUID) -> List[Query]:
        orm_objs = self.db_session.query(QueryORM).filter_by(organization_id=organization_id).all()
        return [self._to_entity(o) for o in orm_objs]
    
class PostgreSQL_LLMUsageRepository(LLMUsageRepositoryInterface):
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        
    @staticmethod    
    def _to_entity(orm_obj: LLMUsageORM) -> LLMUsage:
        return LLMUsage(
            id=orm_obj.id,
            query_id=orm_obj.query_id,
            model_name=orm_obj.model_name,
            prompt_tokens=orm_obj.prompt_tokens,
            completion_tokens=orm_obj.completion_tokens,
            total_tokens=orm_obj.total_tokens,
            estimated_cost_usd=orm_obj.estimated_cost_usd,
            created_at=orm_obj.created_at,
        )
        
    @staticmethod
    def _to_orm(llm_usage: LLMUsage) -> LLMUsageORM:
        return LLMUsageORM(
            id=llm_usage.id,
            query_id=llm_usage.query_id,
            model_name=llm_usage.model_name,
            prompt_tokens=llm_usage.prompt_tokens,
            completion_tokens=llm_usage.completion_tokens,
            total_tokens=llm_usage.total_tokens,
            estimated_cost_usd=llm_usage.estimated_cost_usd,
            created_at=llm_usage.created_at,
        )   
    def add(self, llm_usage: LLMUsage) -> None:
        orm_obj = self._to_orm(llm_usage)
        self.db_session.add(orm_obj)
        self.db_session.flush()
    
    #it must return 1, because 1 query = 1 usage
    def get_by_query_id(self, organization_id: uuid.UUID, query_id: uuid.UUID) -> LLMUsage | None: #double safety with organization_id as a parameter.
        orm_obj = (
            self.db_session.query(LLMUsageORM)
            .join(QueryORM, LLMUsageORM.query_id == QueryORM.id)
            .filter(LLMUsageORM.query_id == query_id, QueryORM.organization_id == organization_id)
            .first()
        )
        return None if orm_obj is None else self._to_entity(orm_obj)

class PostgreSQL_QueryChunkRepository(QueryChunkRepositoryInterface):
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    @staticmethod
    def _to_entity(orm_obj: QueryChunkORM) -> QueryChunk:
        return QueryChunk(
            query_id=orm_obj.query_id,
            chunk_id=orm_obj.chunk_id,
            similarity_score=orm_obj.similarity_score,
            rank=orm_obj.rank
        )
        
    @staticmethod
    def _to_orm(query_chunk: QueryChunk) -> QueryChunkORM:
        return QueryChunkORM(
            query_id=query_chunk.query_id,
            chunk_id=query_chunk.chunk_id,
            similarity_score=query_chunk.similarity_score,
            rank=query_chunk.rank
        )
    
    def add_links(self, query_chunks: List[QueryChunk]) -> None:
        orm_objs = [self._to_orm(qc) for qc in query_chunks]
        self.db_session.add_all(orm_objs)
        self.db_session.flush()
    
    def get_by_query_id(self, organization_id: uuid.UUID, query_id: uuid.UUID) -> List[QueryChunk]:
        orm_objs = (
            self.db_session.query(QueryChunkORM)
            .join(ChunkORM, QueryChunkORM.chunk_id == ChunkORM.id)
            .filter(QueryChunkORM.query_id == query_id, ChunkORM.organization_id == organization_id)
            .order_by(QueryChunkORM.rank.asc().nulls_last())
            .all()
        )
        return [self._to_entity(o) for o in orm_objs]   