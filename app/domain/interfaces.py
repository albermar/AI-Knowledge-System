
'''
One interface per ORM table
Organization_Repository
Document_Repository
Query_Repository
Chunk_Repository
QueryChunk_Repository
LLMUsage_Repository

For each, I have to define the operations I need in the use cases. For example, for Query_Repository, I might need:
- create_query(query: Query) -> Query
- get_query_by_id(query_id: uuid.UUID
- list_queries_by_organization(organization_id: uuid.UUID) -> List[Query]
- update_query(query: Query) -> Query
- delete_query(query_id: uuid.UUID) -> None
- etc.

This way, the use cases depend only on these interfaces, and the actual database implementation can be swapped out without affecting the business logic.

The necessary imports to create interfaces are: 
from abc import ABC, abstractmethod

for example: 
class QueryRepository(ABC):
    @abstractmethod

abstractmethod means that the method is declared but not implemented in the base class (the interface). Subclasses that inherit from this abstract base class are required to provide an implementation for this method. If a subclass does not implement all abstract methods, it cannot be instantiated. This is a way to enforce that certain methods must be defined in any concrete class that implements the interface.

'''

from abc import ABC, abstractmethod

import uuid
from typing import List
from app.domain.entities import Organization, Document, Query, Chunk, QueryChunk, LLMUsage

class OrganizationRepositoryInterface(ABC):
    @abstractmethod
    def add(self, organization: Organization) -> None:
        ...    
    @abstractmethod
    def get_by_id(self, id:uuid.UUID) -> Organization | None:
        ...
    @abstractmethod
    def get_by_name(self, name:str)-> Organization | None:
        ...
    @abstractmethod
    def delete(self, id:uuid.UUID) -> None:
        ...

class DocumentRepositoryInterface(ABC):
    @abstractmethod
    def add(self, document: Document) -> None:
        ...    
    @abstractmethod
    def get_by_id(self, organization_id: uuid.UUID, id: uuid.UUID) -> Document | None:#double safety with organization_id as a parameter.
        ...
    @abstractmethod
    def list_by_organization(self, organization_id:uuid.UUID) -> List[Document]:
        ...
    @abstractmethod
    def delete(self, organization_id: uuid.UUID, id: uuid.UUID) -> None: #double safety with organization_id as a parameter.
        ...   

class QueryRepositoryInterface(ABC):
    @abstractmethod
    def add(self, query: Query) -> None:
        ...    
    @abstractmethod
    def get_by_id(self, organization_id:uuid.UUID, id:uuid.UUID) -> Query | None: #double safety with organization_id as a parameter.
        ...
    @abstractmethod
    def list_by_organization(self, organization_id:uuid.UUID) -> List[Query]:
        ...
    @abstractmethod
    def update(self, query: Query) -> None:
        ...

class ChunkRepositoryInterface(ABC):
    #Can add 1 or N bulk. 
    @abstractmethod
    def add_many(self, chunks: List[Chunk]) -> None:
        ...
    @abstractmethod
    def get_by_document(self, organization_id: uuid.UUID, document_id: uuid.UUID) -> List[Chunk]: #double safety with organization_id as a parameter.
        ...
    @abstractmethod
    def get_by_ids_in_order(self, organization_id: uuid.UUID, ids: List[uuid.UUID]) -> List[Chunk]: #double safety with organization_id as a parameter.
        """
        Return chunks in the same order as the input ids. 
        Not found ids are ignored.
        """        
        ...
    @abstractmethod
    def delete_by_document(self, organization_id: uuid.UUID, document_id: uuid.UUID) -> None: #double safety with organization_id as a parameter.
        ...
    
class QueryChunkRepositoryInterface(ABC):
    @abstractmethod
    def add_links(self, links: List[QueryChunk]) -> None:
        ...
    @abstractmethod
    def get_chunks_for_query(self, organization_id: uuid.UUID, query_id: uuid.UUID) -> List[QueryChunk]: #double safety with organization_id as a parameter.
        ...
    @abstractmethod
    def delete_by_query(self, organization_id: uuid.UUID, query_id: uuid.UUID) -> None: #double safety with organization_id as a parameter.
        ...

class LLMUsageRepositoryInterface(ABC):
    @abstractmethod
    def add(self, usage: LLMUsage) -> None:
        ...    
    @abstractmethod
    def list_by_query(self, organization_id: uuid.UUID, query_id: uuid.UUID) -> List[LLMUsage]: #double safety with organization_id as a parameter.
        ...
    @abstractmethod
    def sum_tokens_by_organization(self, organization_id:uuid.UUID) -> int:
        ...
    @abstractmethod
    def sum_cost_by_organization(self, organization_id:uuid.UUID) -> float:
        ...

# --- #

class DocumentStorageInterface(ABC):
    @abstractmethod
    def save(self, organization_id: uuid.UUID, document_id: uuid.UUID, content: bytes) -> None:
        ...
    @abstractmethod
    def load(self, organization_id: uuid.UUID, document_id: uuid.UUID) -> bytes:
        ...

# --- # 
class PDFParserInterface(ABC):
    @abstractmethod
    def parse_pdf(self, file_content: bytes) -> str:
        ...

# --- #

class ChunkerInterface(ABC):
    @abstractmethod
    def chunk_text(self, text: str) -> List[str]:
        ...