from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import os

from .db_url import build_database_url

engine = create_engine(build_database_url(), echo = True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind = engine, autoflush = False, autocommit = False)

def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()