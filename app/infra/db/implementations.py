from typing import List
import uuid

from app.infra.db.engine import get_db_session
from sqlalchemy.orm import Session

from app.domain.interfaces import DocumentRepositoryInterface, OrganizationRepositoryInterface, QueryRepositoryInterface, ChunkRepositoryInterface, LLMUsageRepositoryInterface, QueryChunkRepositoryInterface
#import orm models as **ORM: 
from app.infra.db.ormmodels import Organization as OrganizationORM, Document as DocumentORM, Query as QueryORM, Chunk as ChunkORM, LLMUsage as LLMUsageORM, QueryChunk as QueryChunkORM 
#import domain entities
from app.domain.entities import Organization, Document, Query, Chunk, LLMUsage, QueryChunk

#✅#
class PostgreSQL_OrganizationRepository(OrganizationRepositoryInterface):
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def _to_entity(self, orm_obj: OrganizationORM) -> Organization:
        return Organization(id=orm_obj.id, name=orm_obj.name, created_at=orm_obj.created_at)
    
    def add(self, organization: Organization) -> None:
        orm_obj = OrganizationORM(id=organization.id, name=organization.name)
        self.db_session.add(orm_obj)        
        
    def get_by_id (self, id: uuid.UUID) -> Organization | None:
        orm_obj = self.db_session.get(OrganizationORM, id) #get function can return None if not found, which is what we want.
        return None if orm_obj is None else self._to_entity(orm_obj)    
    
    def get_by_name(self, name: str) -> Organization | None:
        orm_obj = (
            self.db_session.query(OrganizationORM)
            .filter_by(name=name)
            .first()
        )
        return None if orm_obj is None else self._to_entity(orm_obj)
       
    def delete(self, id: uuid.UUID) -> None:
        orm_obj = self.db_session.get(OrganizationORM, id)
        if orm_obj is not None:
            self.db_session.delete(orm_obj)
        
class PostgreSQL_DocumentRepository(DocumentRepositoryInterface):
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    @staticmethod # Because these are just helper functions to convert between ORM and Entity, they don't need access to the instance (self), so we can make them static methods.
    def _to_entity(orm_obj: DocumentORM) -> Document:
        return Document(
            id=orm_obj.id,
            organization_id=orm_obj.organization_id,
            title=orm_obj.title,
            source_type=orm_obj.source_type,
            document_hash=orm_obj.document_hash,
            content=orm_obj.content,
            created_at=orm_obj.created_at
        )
    
    @staticmethod
    def _to_orm(document: Document) -> DocumentORM:
        return DocumentORM(
            id=document.id,
            organization_id=document.organization_id,
            title=document.title,
            source_type=document.source_type,
            document_hash=document.document_hash,
            content=document.content,
            created_at=document.created_at
        )
    
    def add(self, document: Document) -> None:
        orm_obj = self._to_orm(document)
        self.db_session.add(orm_obj)
    
    def get_by_hash(self, organization_id: uuid.UUID, document_hash: str) -> Document | None: #double safety with organization_id as a parameter.
        orm_obj = (
            self.db_session.query(DocumentORM).
            filter_by(organization_id = organization_id, document_hash = document_hash)
            .first()
            )        
        return None if orm_obj is None else self._to_entity(orm_obj)
        
    def get_by_id(self, organization_id: uuid.UUID, id: uuid.UUID) -> Document | None: #double safety with organization_id as a parameter.
        #try to return orm object, and if exists return entity object.
        orm_obj = (
            self.db_session.query(DocumentORM)
            .filter_by(id=id, organization_id=organization_id)
            .first()
        )
        return None if orm_obj is None else self._to_entity(orm_obj)
    
    def list_by_organization(self, organization_id: uuid.UUID)  -> List[Document]:
        #fetch orm list with org filter, then convert to entity list.
        orm_objs = (
            self.db_session.query(DocumentORM)
            .filter_by(organization_id=organization_id)
            .all()            
        )
        
        return [self._to_entity(o) for o in orm_objs]

    def delete(self, organization_id: uuid.UUID, id: uuid.UUID) -> None: #double safety with organization_id as a parameter.
        orm_obj = (
            self.db_session.query(DocumentORM)
            .filter_by(id=id, organization_id=organization_id)
            .first()
        )
        if orm_obj is not None:
            self.db_session.delete(orm_obj)      

class PostgreSQL_ChunkRepository(ChunkRepositoryInterface):
    def __init__(self, db_session: Session):
        self.db_session = db_session
        
        

#playground for testing the repositories. This code will be deleted later.
if __name__ == "__main__":
    # Example usage
    from app.infra.db.engine import SessionLocal
    db = SessionLocal()
    try:
        org_repo = PostgreSQL_OrganizationRepository(db)
        # add N random organizations
        N = 0
        i = 0
        while N > 0:
            name = f"Organization {i}"
            if(org_repo.get_by_name(name) is not None):                
                i = i+1
                continue
            org = Organization(name=name)
            org_repo.add(org)
            N = N-1
            i = i+1
        db.commit() #commit the transaction to save the organizations in the database.
        
        #delete all organizations
        orgs = db.query(OrganizationORM).all()
        for org in orgs:
            org_repo.delete(org.id)
        db.commit() #commit the transaction to delete the organizations from the database.
        
        #get all organizations and print them
        orgs = db.query(OrganizationORM).all()
        for org in orgs:
            print(org)
        
    finally:
        db.close()
    