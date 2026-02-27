import os
from dotenv import load_dotenv
load_dotenv() 


def get_db_url() -> str:
    
    if db_url := os.getenv("DATABASE_URL"):
        return db_url 
    
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASSWORD"]
    name = os.environ["DB_NAME"]
    host = os.environ["DB_HOST"]
    port = os.environ["DB_PORT"]
    
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"