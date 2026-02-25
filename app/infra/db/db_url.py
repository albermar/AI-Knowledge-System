import os

from dotenv import load_dotenv
load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def build_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.strip():
        return database_url

    user = _require("POSTGRES_USER")
    password = _require("POSTGRES_PASSWORD")
    db_name = _require("POSTGRES_DB")
    host = _require("POSTGRES_HOST")
    port = _require("POSTGRES_PORT")

    # extra safety: validate port is an int
    try:
        int(port)
    except ValueError as e:
        raise RuntimeError(f"POSTGRES_PORT must be an integer, got: {port!r}") from e

    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"