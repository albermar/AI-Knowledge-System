
from dataclasses import dataclass
import uuid

from app.domain.entities import Document, IngestDocumentResult, Chunk, LLMUsage, NewOrganizationResult, Organization, Query, QueryChunk
from app.domain.interfaces import ChunkRepositoryInterface, ChunkerInterface, DocumentRepositoryInterface, DocumentStorageInterface, LLMUsageRepositoryInterface, OrganizationRepositoryInterface, PDFParserInterface, QueryChunkRepositoryInterface, QueryRepositoryInterface

import hashlib

from app.application.exceptions import (
    UseCaseError,
    DocumentAlreadyExistsError,
    IngestDocumentError,
    EmptyFileError,
    UnsupportedFileTypeError,
    StorageDeleteError, 
    StorageWriteError, 
    ParsingError,
    ChunkingError,
    PersistenceError, 
    DocumentPersistError,
    OrganizationNotFoundError, 
    ChunkPersistenceError, 
    OrganizationAlreadyExistsError, 
    InvalidOrganizationNameError
)


@dataclass
class IngestDocument:
    org_repo: OrganizationRepositoryInterface
    doc_repo: DocumentRepositoryInterface
    chunk_repo: ChunkRepositoryInterface
    storage: DocumentStorageInterface
    parser: PDFParserInterface
    chunker: ChunkerInterface


    def execute(self, organization_id: uuid.UUID, file_content: bytes, filename: str) -> IngestDocumentResult:

        if not file_content:
            raise EmptyFileError("The provided file is empty.")
        
        # Organization must exist
        if self.org_repo.get_by_id(organization_id) is None:
            raise OrganizationNotFoundError("Organization not found")        
        
        # Parse
        try:
            parsed_content = self.parser.parse_pdf(file_content) #can return ValueError if type is not pdf. 
        except Exception as e:
            raise ParsingError(f"Failed to parse PDF: {str(e)}") from e
        
        if not parsed_content or not parsed_content.strip():
            raise ParsingError("Parsed content is empty.")
        
        # Dedup: org + sha256(file bytes)
        document_hash = hashlib.sha256(file_content).hexdigest()
        #print(f"Computed document hash: {document_hash}")
        #print(f"Document with hash {self.doc_repo.get_by_hash(organization_id, document_hash).document_hash}")
        if self.doc_repo.get_by_hash(organization_id, document_hash) is not None:            
            raise DocumentAlreadyExistsError("Document already exists.")
        
        #Persist. DB commit happens in the endpoint.
        file_saved = False
        document: Document | None = None
        try:
            document = Document(
                organization_id=organization_id, 
                title=filename,
                source_type="pdf",
                content=parsed_content,
                document_hash=document_hash
            )
            
            try:
                # DB. Add document metadata and content            
                self.doc_repo.add(document) #save the document metadata + parsed content in the repo (database)
            except Exception as e:
                raise DocumentPersistError(f"Failed to save document metadata: {str(e)}") from e
            
            try: 
                # Storage: Save raw file
                self.storage.save(organization_id= organization_id, document_id=document.id, content=file_content) #save the original file in the storage with the document id as reference.
                file_saved = True
            except Exception as e:
                raise StorageWriteError(f"Failed to save document file: {str(e)}") from e
            
            #Chunking
            try: 
                chunks: list[Chunk] = self.chunker.chunk_text(
                organization_id=organization_id, 
                document_id=document.id, 
                content=parsed_content
                )
            except Exception as e:
                raise ChunkingError(f"Failed to chunk document content: {str(e)}") from e
            
            try:             
                self.chunk_repo.add_many(chunks)
            except Exception as e:
                raise ChunkPersistenceError(f"Failed to save document chunks: {str(e)}") from e
            
            return IngestDocumentResult(
                organization_id=organization_id,
                document_id=document.id,
                chunks_created=len(chunks),
                document_hash=document_hash
            )
            
        except Exception:
            #cleanup storage if it was saved. 
            if file_saved and document is not None:
                try:
                    self.storage.delete(organization_id, document.id)
                except Exception as e:
                    raise StorageDeleteError(f"Failed to delete document file during cleanup: {str(e)}") from e                    
            raise


@dataclass
class NewOrganization:
    org_repo: OrganizationRepositoryInterface

    def execute(self, name: str) -> NewOrganizationResult:
        
        clean = (name or "").strip()
        if not clean:
            raise InvalidOrganizationNameError("Organization name cannot be empty.")
        
        if len(clean) > 200:
            raise InvalidOrganizationNameError("Organization name cannot exceed 200 characters.")
        
        if self.org_repo.get_by_name(clean) is not None:
            raise OrganizationAlreadyExistsError("Organization with this name already exists.")
        
        new_org = Organization(name=clean)
        
        try:
            self.org_repo.add(new_org)
            return NewOrganizationResult(id=new_org.id, name=new_org.name, created_at=new_org.created_at)
        except Exception as e:
            raise PersistenceError(f"Failed to persist new organization: {str(e)}") from e
        

@dataclass
class AskQuestion:
    '''
    Question
    ↓
    Embed question
    ↓
    Vector search chunks
    ↓
    Build prompt
    ↓
    Call LLM
    ↓
    Store Query + LLMUsage
    ↓
    Return answer
    '''
    org_repo: OrganizationRepositoryInterface
    # doc_repo: DocumentRepositoryInterface #Not necessary for this use case
    # chunk_repo: ChunkRepositoryInterface #reading chunks for vector search --> Insert in the retriever engine interface instead.
    query_repo: QueryRepositoryInterface #to persist the question and answer
    llm_usage_repo: LLMUsageRepositoryInterface #to persist the LLM usage data
    query_chunk_repo: QueryChunkRepositoryInterface #to persist the relationship between query and chunks used in the prompt. This is useful for analytics and future features, but not strictly necessary for the basic functionality.
    
    retriever_engine: RetrieverInterface # embedding the question + vector search retrieving relevant chunks. Double duty. 
    prompt_engine: PromptBuilderInterface # prompt_engine.build_prompt(question, retrieved_chunks) -> prompt
    llm_engine: LLMInterface #llm_engine.call(prompt) -> answer
    
    
    def execute(self, organization_id: uuid.UUID, question: str) -> str:
        # 1. Validating the organization exists.
        # 2. Embedding the question using an embedding model.
        # 3. Performing a vector search on the chunks to find relevant ones.
        # 4. Building a prompt with the question and retrieved chunks.
        # 5. Calling the LLM to get an answer.
        # 6. Storing the query, answer, LLM usage, and query-chunk relationships in the respective repositories.
        # 7. Returning the answer.
        
        if self.org_repo.get_by_id(organization_id) is None:
            raise OrganizationNotFoundError("Organization not found")
        
        clean_question = (question or "").strip()
        if not clean_question:
            raise ERROR("Question cannot be empty.")
        
        embedded_question = self.embedder.embed_question(clean_question)
        
        chunks_ann : list[Chunk] = self.chunk_repo.vector_search(organization_id, embedded_question)
        
        prompt = self.build_prompt(clean_question, chunks_ann)
        
        answer = self.call_llm(prompt)
        
        #Persist query, usage and query-chunk relationships. DB commit happens in the endpoint.
        try:
            query = Query(organization_id=organization_id, question=clean_question, answer=answer)
            self.query_repo.add(query)
            
            usage = LLMUsage(query_id=query.id, model_name="gpt-4", prompt_tokens= self.count_tokens(prompt), answer_tokens=self.count_tokens(answer))
            self.llm_usage_repo.add(usage)
            
            query_chunks = []
            for i, chunk in enumerate(chunks_ann):
                qc = QueryChunk(query_id=query.id, chunk_id=chunk.id, similarity_score=chunk.similarity_score, rank=i+1)
                query_chunks.append(qc)
            self.query_chunk_repo.add_many(query_chunks)
        except Exception as e:
            raise PersistenceError(f"Failed to persist query, usage or query-chunk relationships: {str(e)}") from e
        
        return answer
    
        
        
        
        
        
        
        pass