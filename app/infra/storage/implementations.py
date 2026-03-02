from app.domain.interfaces import DocumentStorageInterface
from pathlib import Path
from uuid import uuid


class Local_DocumentStorage(DocumentStorageInterface):
    
    def __init__ (self, base_path: str):
        self.base_path = Path(base_path)
    
    def save(self, organization_id: uuid.UUID, document_id: uuid.UUID, content: bytes) -> None:
        ...
    def load(self, organization_id: uuid.UUID, document_id: uuid.UUID) -> bytes:
        ...