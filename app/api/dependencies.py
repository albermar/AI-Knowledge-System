import os

from app.domain.entities import Organization

from fastapi import Depends, HTTPException, Header
from app.infra.db.engine import get_db_session
from sqlalchemy.orm import Session

from app.infra.db.implementations import PostgreSQL_OrganizationRepository
from app.application.services.api_key import hash_api_key

from app.infra.llm.implementations import OpenAILLMClient

from functools import lru_cache
from app.infra.embedder.implementations import OpenAIEmbedder

def get_current_organization(
        api_key: str = Header(..., alias="X-API-Key"),
        db: Session = Depends(get_db_session)
    ) -> Organization:
    
    org_repo = PostgreSQL_OrganizationRepository(db)
    api_key_hash = hash_api_key(api_key)
    
    organization = org_repo.get_by_api_key_hash(api_key_hash=api_key_hash)
    
    if organization is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return organization



def get_llm_client():
    return OpenAILLMClient()

@lru_cache 
def get_embedder() -> OpenAIEmbedder:
    return OpenAIEmbedder(
        api_key=os.environ["OPENAI_API_KEY"],
        model_name=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        dimensions=int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "384")),
    )