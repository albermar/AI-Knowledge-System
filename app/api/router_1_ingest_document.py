from datetime import datetime
import uuid

from fastapi import File, UploadFile, Depends, HTTPException
from fastapi import APIRouter
from sqlalchemy.orm import Session 
from app.infra.db.engine import get_db_session

from app.api.schemas import IngestDocumentResponse

from app.infra.db.implementations import PostgreSQL_DocumentRepository, PostgreSQL_OrganizationRepository, PostgreSQL_ChunkRepository
from app.infra.parser.implementations import V1_PDFParser
from app.infra.storage.implementations import Local_DocumentStorage 
from app.application.services import V1_Chunker

from app.domain.entities import IngestDocumentResult

from app.application.use_cases import IngestDocument

router = APIRouter()

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  #TODO: get from config
DEFAULT_STORAGE_PATH = "./storage" #TODO: get from config

@router.post("/ingest-document", response_model = IngestDocumentResponse )
async def ingest_document(file: UploadFile = File(...), db: Session = Depends(get_db_session)):
    
    default_organization_id = uuid.UUID("00000000-0000-0000-0000-000000000000") #TODO: get from auth context or request header. For now, we use a default one for testing.
    
    # Receive the file, extract content, filename. Validate max size
    file_bytes = await file.read() 
    filename = file.filename or ("doc-" + datetime.now().strftime("%Y%m%d%H%M%S"))
    size = len(file_bytes)
    if size == 0 or size > MAX_FILE_SIZE_BYTES:   #10MB max size for now
        raise HTTPException(status_code=400, detail=f"File is empty or exceeds the maximum allowed size of {MAX_FILE_SIZE_BYTES / (1024 * 1024)} MB.") 
    
    # Build the use case with the necessary dependencies (repositories, storage, parser, chunker)    
    storage = Local_DocumentStorage(DEFAULT_STORAGE_PATH)   #TODO
    use_case = IngestDocument(
        org_repo = PostgreSQL_OrganizationRepository(db),   #TODO
        doc_repo = PostgreSQL_DocumentRepository(db),       #TODO
        chunk_repo = PostgreSQL_ChunkRepository(db),        #TODO
        storage = storage,                                  #TODO
        parser = V1_PDFParser(),                            #TODO
        chunker = V1_Chunker()                              #TODO
    )
    
    try:    
        result = use_case.execute(default_organization_id, file_bytes, filename)    #TODO
        db.commit()
    except Exception as e:
        db.rollback()
        storage.delete_file(filename)        
        raise HTTPException(status_code=500, detail=str(e)) #TODO. Placeholder. Later I will map specific exceptions to specific status codes and messages.
        
    return IngestDocumentResponse.from_domain(result) #is it result visible here? Yes, it's defined in the try block, but since we return immediately after, it's fine.

'''
1. Endpoint tasks and duties
    - ✅ Receive the file, extract the content and filename. Validate max size. 
    - ✅ Build the use case with the necessary dependencies (repositories, storage, parser, chunker)
    - ✅ Execute the use case with the organization_id, file content and filename
    - ✅ Map Exceptions to HTTP errors.
    - ✅ Commit or roll back if any exception happens. If storage succeded after a DB exception, delete file.
    - ✅ Return the response (pydantic) based on the use case result (domain entity)
'''