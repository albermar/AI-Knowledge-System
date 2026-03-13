from datetime import datetime
import uuid

from app.api.dependencies import get_current_organization, get_embedder
from app.domain.entities import Organization
from app.application.exceptions import ChunkPersistenceError, ChunkingError, DocumentAlreadyExistsError, DocumentPersistError, EmptyFileError, OrganizationNotFoundError, ParsingError, StorageDeleteError, StorageWriteError
from app.domain.interfaces import EmbedderInterface
from fastapi import File, UploadFile, Depends, HTTPException
from fastapi import APIRouter
from sqlalchemy.orm import Session 
from app.infra.db.engine import get_db_session

from app.api.schemas import IngestDocumentResponse

from app.infra.db.implementations import PostgreSQL_DocumentRepository, PostgreSQL_OrganizationRepository, PostgreSQL_ChunkRepository
#from app.infra.embedder.implementations import SentenceTransformerEmbedder
from app.infra.parser.implementations import V1_PDFParser
from app.infra.storage.implementations import Local_DocumentStorage 
from app.application.services.chunker import V1_Chunker

from app.application.use_cases import IngestDocument

router = APIRouter()

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  #TODO: get from config
DEFAULT_STORAGE_PATH = "./storage" #TODO: get from config


@router.post("/ingest-document", response_model = IngestDocumentResponse )
async def ingest_document(
        file: UploadFile = File(...), 
        organization: Organization = Depends(get_current_organization),
        db: Session = Depends(get_db_session),
        embedder: EmbedderInterface = Depends(get_embedder)
    ):
    
    file_bytes = await file.read() 
    filename = file.filename or ("doc-" + datetime.now().strftime("%Y%m%d%H%M%S"))
    size = len(file_bytes)
    
    if size == 0:
        raise HTTPException(status_code=400, detail="File is empty.")
    if size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds max size ({MAX_FILE_SIZE_BYTES / (1024 * 1024)} MB).",
        )
        
    storage = Local_DocumentStorage(DEFAULT_STORAGE_PATH)
    
    use_case = IngestDocument(
        org_repo = PostgreSQL_OrganizationRepository(db),
        doc_repo = PostgreSQL_DocumentRepository(db),   
        chunk_repo = PostgreSQL_ChunkRepository(db),
        embedder= embedder,
        storage = Local_DocumentStorage(DEFAULT_STORAGE_PATH),
        parser = V1_PDFParser(),
        chunker = V1_Chunker()                              
    )
    result = None
    try:        
        result = use_case.execute(organization.id, file_bytes, filename) #organization.id comes from the get_current_organization dependency, which means that if the API key was invalid or the organization didn't exist, it would have already raised an HTTPException and we wouldn't reach this point.
        db.commit()
        return IngestDocumentResponse.from_domain(result)
    
    except DocumentAlreadyExistsError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except (EmptyFileError, ParsingError) as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except OrganizationNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except (DocumentPersistError, ChunkPersistenceError, StorageWriteError, ChunkingError) as e:
        db.rollback()
        if result is not None:
            try:
                storage.delete(organization.id, result.document_id)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=str(e))
    except StorageDeleteError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Document ingested but failed to clean up storage: {str(e)}")
    except Exception as e:
        db.rollback()
        if result is not None:
            try: 
                storage.delete(organization.id, result.document_id)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
