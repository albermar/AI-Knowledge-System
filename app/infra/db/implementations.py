from sqlalchemy.orm import Session

from app.domain.interfaces import DocumentRepositoryInterface, OrganizationRepositoryInterface, QueryRepositoryInterface, ChunkRepositoryInterface, LLMUsageRepositoryInterface, QueryChunkRepositoryInterface
from app.infra.db.ormmodels import Organization, Document, Query, Chunk, LLMUsage, QueryChunk

class PostgreSQL_OrganizationRepositoryInterface(OrganizationRepositoryInterface):
    def __init__(self, db_session: Session):
        self.db_session = db_session

class PostgreSQL_DocumentRepositoryInterface(DocumentRepositoryInterface):
    def __init__(self, db_session: Session):
        self.db_session = db_session

class PostgreSQL_ChunkRepositoryInterface(ChunkRepositoryInterface):
    def __init__(self, db_session: Session):
        self.db_session = db_session