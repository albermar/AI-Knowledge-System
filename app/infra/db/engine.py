
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.infra.db.base import MyBase

from app.infra.db.db_url_builder import get_db_url

DATABASE_URL = get_db_url()

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False, future=True)


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


