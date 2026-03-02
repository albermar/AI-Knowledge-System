
from dataclasses import dataclass
import uuid

from app.domain.entities import Document, IngestDocumentResult
from app.domain.interfaces import ChunkRepositoryInterface, ChunkerInterface, DocumentRepositoryInterface, DocumentStorageInterface, OrganizationRepositoryInterface, PDFParserInterface

import hashlib


@dataclass
class IngestDocument:
    org_repo: OrganizationRepositoryInterface
    doc_repo: DocumentRepositoryInterface
    chunk_repo: ChunkRepositoryInterface
    storage: DocumentStorageInterface
    parser: PDFParserInterface
    chunker: ChunkerInterface


    def execute(self, organization_id: uuid.UUID, file_content: bytes, filename: str) -> IngestDocumentResult:
        #Validate the organization_id (exists)
        
        # search organization in the org repo, if not exists, return error.
        if self.org_repo.get_by_id(organization_id) is None:
            raise ValueError("Organization not found")
        
        #Validate file type. Only PDFs by now. 
        if not file_content.startswith(b'%PDF-'):
            raise ValueError("Invalid file type. Only PDFs are allowed.")
        
        #Parse the Document and extract the text content. 
        try:
            parsed_content = self.parser.parse_pdf(file_content)
        except Exception as e:
            raise ValueError(f"Error parsing PDF: {str(e)}")
        
        #check if the content is empty after parsing. If yes, reject.
        if not parsed_content.strip():
            raise ValueError("Parsed content is empty.")
        
        #check if the document already exists. Unique identifier in the database will be organization_id + document_hash (hash of the file content). If exists, reject. If not, continue.
        document_hash = hashlib.sha256(file_content).hexdigest()        
        
        if self.doc_repo.get_by_hash(organization_id, document_hash) is not None:
            raise ValueError("Document already exists.")
        
        #MILESTONE. The document is ready to be saved in the repo and storage. The document id will be generated here and used as reference in both places.
        
        try:
            #first create document object (domain entity)
            document = Document(organization_id=organization_id, title=filename, source_type="pdf", content=parsed_content, document_hash=document_hash)
            self.doc_repo.add(document) #save the document metadata + parsed content in the repo (database)
            self.storage.save(organization_id= organization_id, document_id=document.id, content=file_content) #save the original file in the storage with the document id as reference.
        
            #Compute chunks. Each chunk must be properly stored in the chunk table. The chunk objects should have a reference to the document id.
            chunks: list = self.chunker.chunk_text(organization_id=organization_id, document_id=document.id, content=parsed_content)
            
            self.chunk_repo.add_many(chunks) #save the chunks in the chunk repo (database)        
            #build the result object.
            
        except Exception as e:            
            return IngestDocumentResult(status = False, document_id=None, number_of_chunks=0) 
        
        return IngestDocumentResult(status = True, document_id=document.id, number_of_chunks=len(chunks))
        
        
        
        
            




'''
2. Use case duties and responsibilities
    - ✅ Validate the organization_id exists
    - ✅ Validate file type (only PDFs by now) and file content (max size, not empty, etc)
    - ✅ Parse the file content to extract content (text)
    - ✅ Check if the parsed content is empty, if yes reject.
    - ✅ Check if the document exists, if yes reject, if not, continue.
    - ✅ Create a new document object (domain entity) and save it both in the repo + storage. The repo will save the metadata + parsed content and the storage will save the original file
    - ✅ Compute chunks. + save chunks in the chunk repo (database)
    - ✅ Return the result (status, nº chunks, document id) 
'''