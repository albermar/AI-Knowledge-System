
from dataclasses import dataclass
import uuid

from app.application.dto import AskQuestionResult
from app.domain.entities import Document,Chunk, LLMUsage, Organization, Query, QueryChunk
from app.domain.interfaces import ChunkRepositoryInterface, ChunkerInterface, DocumentRepositoryInterface, DocumentStorageInterface, LLMUsageRepositoryInterface, OrganizationRepositoryInterface, PDFParserInterface, QueryChunkRepositoryInterface, QueryRepositoryInterface

import hashlib

from app.application.exceptions import (
    LLMUsagePersistenceError,
    NoRelevantChunksFoundError,
    QueryChunkPersistenceError,
    QueryPersistenceError,
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
    InvalidOrganizationNameError, 
    EmptyQuestionError
)
from app.domain.types import LLMResponse, RetrievedChunk

from app.domain.interfaces import PromptBuilderInterface, RetrieverInterface, EmbedderInterface, LLMInterface


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
    query_repo: QueryRepositoryInterface #to persist the question and answer
    llm_usage_repo: LLMUsageRepositoryInterface #to persist the LLM usage data
    query_chunk_repo: QueryChunkRepositoryInterface #to persist the relationship between query and chunks used in the prompt. This is useful for analytics and future features, but not strictly necessary for the basic functionality.
    
    retriever: RetrieverInterface
    prompt_builder: PromptBuilderInterface # with the text question + retrieved relevant chunks, composes the final prompt
    llm_client: LLMInterface #Calls the LLM and receives an answer. 
    
    
    def execute(self, organization_id: uuid.UUID, question: str) -> AskQuestionResult:
        # 1. Validating the organization exists.
        if self.org_repo.get_by_id(organization_id) is None:
            raise OrganizationNotFoundError("Organization not found")
        
        # 2. Validate question
        clean_question = (question or "").strip()
        if not clean_question:
            raise EmptyQuestionError("Question cannot be empty.")
        
        # 3. Persist query as soon as the request is valid.
        try:
            query = Query(
                organization_id=organization_id, 
                question=clean_question, 
                answer = None, 
                latency_ms = None
                )
            self.query_repo.add(query)
        except Exception as e:
            raise QueryPersistenceError(f"Failed to persist query: {str(e)}") from e 
        
        #4. Retrieve relevant chunks
        try:
            retrieved_chunks: list[RetrievedChunk] = self.retriever.retrieve_best_chunks(organization_id=organization_id, question=clean_question)        
        except Exception as e:
            raise UseCaseError(f"Failed to retrieve relevant chunks: {str(e)}") from e
        
        if not retrieved_chunks:
            raise NoRelevantChunksFoundError("No relevant chunks found for the question.") 
        
        # 5. Build prompt from question + retrieved chunks      
        try:  
            prompt: str = self.prompt_builder.build_prompt(clean_question, retrieved_chunks)
        except Exception as e:
            raise UseCaseError(f"Failed to build prompt: {str(e)}") from e
        
        # 6. Call the LLM        
        try:
            llm_response: LLMResponse = self.llm_client.call(prompt)
        except Exception as e:
            raise UseCaseError(f"LLM call failed: {str(e)}") from e
        
        # 7. Persist final answer into query
        try:
            answered_query = query.mark_answered(answer=llm_response.generated_answer, latency_ms=llm_response.latency_ms)
            self.query_repo.update(answered_query)
            query = answered_query  
        except Exception as e:
            raise QueryPersistenceError(f"Failed to update query with answer: {str(e)}") from e
        
        # 8 Persist LLM usage
        try:
            usage = LLMUsage(
                query_id=query.id, 
                model_name=llm_response.model_name, 
                prompt_tokens = llm_response.prompt_tokens, 
                completion_tokens = llm_response.completion_tokens,                
                total_tokens = llm_response.total_tokens,
                estimated_cost_usd = llm_response.estimated_cost_usd
                )
            self.llm_usage_repo.add(usage)
        except Exception as e:
            raise LLMUsagePersistenceError(f"Failed to persist LLM usage: {str(e)}") from e
        
        # 9. Persist query-chunk relationships for analytics, auditability, and future features.
        try:
            query_chunks = []
            for i, rchunk in enumerate(retrieved_chunks):
                qc = QueryChunk(
                    query_id=query.id, 
                    chunk_id= rchunk.chunk_id,
                    similarity_score=rchunk.similarity_score, 
                    rank= i+1 #rank starts at 1
                    )
                query_chunks.append(qc)
            self.query_chunk_repo.add_links(query_chunks)
        except Exception as e:
            raise QueryChunkPersistenceError(f"Failed to persist query-chunk relationships: {str(e)}") from e
        
        # 10. Return the answer and relevant metadata.
        return AskQuestionResult(
            query_id=query.id,
            question=query.question,
            answer=query.answer,
            model_name=usage.model_name,
            latency_ms=query.latency_ms,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            estimated_cost_usd=usage.estimated_cost_usd
        )
    
        
        
