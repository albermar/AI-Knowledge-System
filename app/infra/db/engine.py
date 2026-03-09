
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from pgvector.psycopg import register_vector

from app.infra.db.db_url_builder import get_db_url

DATABASE_URL = get_db_url()

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


# Register pgvector type with psycopg
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    register_vector(dbapi_connection)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False, future=True)


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()