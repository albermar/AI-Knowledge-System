from datetime import datetime

from fastapi import File, UploadFile, Depends
from fastapi import APIRouter
from sqlalchemy.orm import Session 
from app.infra.db.engine import get_db_session

from app.api.schemas import IngestDocumentResponse

from app.infra.db.implementations import PostgreSQL_DocumentRepository, PostgreSQL_OrganizationRepository, PostgreSQL_ChunkRepository
from app.infra.parser.implementations import V1_PDFParser
from app.infra.storage.implementations import Local_DocumentStorage
from app.application.services import V1_Chunker

from app.domain.entities import IngestDocumentResult

router = APIRouter()

@router.post("/ingest-document", response_model = IngestDocumentResponse )
async def ingest_document(file: UploadFile = File(...), db: Session = Depends(get_db_session)):
    
    default_organization_id = "default-organization-id"     #TODO: get from auth or request context later

    file_bytes = await file.read() 
    filename = file.filename or ("new_document_" + datetime.now().strftime("%Y%m%d%H%M%S"))
    
    #Build the use case:
    use_case = IngestDocument(
        org_repo = PostgreSQL_OrganizationRepository(db),   #TODO
        doc_repo = PostgreSQL_DocumentRepository(db),       #TODO
        chunk_repo = PostgreSQL_ChunkRepository(db),        #TODO
        storage = Local_DocumentStorage("./storage"),       #TODO
        parser = V1_PDFParser(),                            #TODO
        chunker = V1_Chunker()                               #TODO            
        )
    
    result = use_case.execute(default_organization_id, file_bytes, filename)    #TODO
    
    return IngestDocumentResponse.from_domain(result)   