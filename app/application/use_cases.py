
from dataclasses import dataclass

from app.domain.entities import IngestDocumentResult
from app.domain.interfaces import ChunkRepositoryInterface, ChunkerInterface, DocumentRepositoryInterface, DocumentStorageInterface, OrganizationRepositoryInterface, PDFParserInterface


@dataclass
class IngestDocument:
    org_repo: OrganizationRepositoryInterface
    doc_repo: DocumentRepositoryInterface
    chunk_repo: ChunkRepositoryInterface
    storage: DocumentStorageInterface
    parser: PDFParserInterface
    chunker: ChunkerInterface


    def execute(self, organization_id: str, file_content: bytes, filename: str) -> IngestDocumentResult:
        pass    

