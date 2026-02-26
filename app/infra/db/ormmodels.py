
'''
0 Wiring
    Organization 1 -- N Document
    Organization 1 -- N Query
    
    Document 1 -- N Chunks
    Query M -- N Chunks    (a query can have many chunks but also a chunk could be parte of other different queries)
        Relational table (QueryChunk) links them
        
    Query 1 -- N LLMUsage
'''
# 1 Create all classes with __tablename__
# 2 Attribute inventory (names only)
# 3 define the attributes that links an element with another db (usually ids)
# 4 Define Primary Keys policy
# 5 Foreign keys + ondelete rules (for every link_id decide which table+column it references and what should happen on delete)
# 6 define Types + nullability + defaults

from sqlalchemy.dialects.postgresql import UUID

class Organization:  
    __tablename__ = "organizations"
    id: PK UUID
    name: String
    created_at: Datetime

class Document:
    __tablename__ = "documents"
    id: PK UUID
    title: String
    source_type: String
    content: Text
    created_at: Datetime
    
    organization_id: FK  <- organizations.id, ondelete = "CASCADE" 
    #if an organization is deleted, all the documents should die too.

class Query:  
    __tablename__ = "queries"
    id: PK UUID
    question: Text
    answer: Text nullable=True
    latency_ms: Integer nullable=True
    created_at: Datetime
    
    organization_id: FK organizations.id, ondelete = "CASCADE" 
    

class Chunk:  
    __tablename__ = "chunks"
    id: PK UUID
    chunk_index: Integer
    content: Text
    token_count: Integer nullable=True
    created_at: Datetime
    
    document_id:  FK documents.id, ondelete = "CASCADE" UUID
    organization_id: FK organizations.id ondelete = "CASCADE" UUID

class LLMUsage:
    __tablename__ = "llm_usage"
    id: PK UUID
    model_name: String
    prompt_tokens: Integer
    completion_tokens: Integer
    total_tokens: Integer
    estimated_cost_usd: Float
    created_at: Datetime 
    
    query_id: FK queries.id ondelete = "CASCADE" UUID

class QueryChunk:  
    __tablename__ = "query_chunks"
    similarity_score: Float nullable=True
    rank: Integer nullable=True
    
    query_id: PK FK queries.id ondelete = "CASCADE" UUID
    chunk_id: PK FK chunks.id ondelete = "CASCADE" UUID
