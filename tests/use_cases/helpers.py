

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def make_db_session():
    user = os.environ["DB_USER"] 
    password = os.environ["DB_PASSWORD"]
    host = os.environ["DB_HOST"]
    port = os.environ["DB_PORT"]
    test_db_name = os.environ["DB_TEST_NAME"]
    DATABASE_URL = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{test_db_name}"

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False,
        future=True,
    )
    return SessionLocal()