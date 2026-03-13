# AI Knowledge System API

![Python](https://img.shields.io/badge/python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-database-blue)
![pgvector](https://img.shields.io/badge/pgvector-vector--search-purple)
![OpenAI](https://img.shields.io/badge/OpenAI-LLM-black)
![pytest](https://img.shields.io/badge/tests-pytest-orange)
![Docker](https://img.shields.io/badge/docker-supported-blue)
![Architecture](https://img.shields.io/badge/architecture-clean--architecture-red)

## Overview
Production-style multi-tenant Retrieval-Augmented Generation (RAG) backend built with FastAPI, PostgreSQL + pgvector, SentenceTransformers embeddings, and OpenAI LLMs.

Organizations can ingest documents and ask questions over their knowledge base using semantic search + LLM generation.

The system tracks queries, token usage, model usage, and estimated cost per organization, and exposes a dashboard API for analytics.

Live demo:
https://YOUR_STREAMLIT_DEMO_LINK

API documentation:
http://localhost:8000/docs

## Index

- [Overview](#overview)
- [Core Features](#core-features)
- [Architecture](#architecture)
- [Pipelines](#pipelines)
- [API Endpoints](#api-endpoints)
- [Tech Stack](#tech-stack)
- [Quickstart](#quickstart)
- [License](#license)

## Core Features

**Multi-tenant architecture**: Each organization operates an isolated workspace with its own documents, queries, and usage analytics.

**API key authentication with hashed storage**: Organizations authenticate using an API key sent via `X-API-Key`. Keys are stored as SHA-256 hashes in the database.

**Retrieval-Augmented Generation (RAG)**: Questions are answered by retrieving semantically relevant document chunks and generating responses with an LLM.

**LLM integration with OpenAI**: Answers are generated using OpenAI models through a pluggable LLM client abstraction.

**Vector search with PostgreSQL + pgvector**: Document embeddings are stored directly in PostgreSQL and queried using cosine similarity.

**Clean Architecture design**: Clear separation between API layer, application use cases, domain entities/interfaces, and infrastructure implementations.

**Pluggable infrastructure via interfaces**: Embedders, retrievers, LLM providers, parsers, and storage implementations can be swapped without modifying business logic.

**Document ingestion pipeline**: Uploaded documents are parsed, chunked, embedded, and stored for semantic retrieval.

**Document deduplication**: Files are identified using a SHA-256 hash to prevent ingesting the same document multiple times.

**Query–chunk traceability**: The chunks used to build each prompt are persisted, enabling RAG debugging and retrieval analysis.

**LLM usage and cost tracking**: Each query records model name, token usage, latency, and estimated cost.

**Local document storage**: Raw document bytes are stored on disk under `storage/{organization_id}/{document_id}.bin`, while document metadata and embeddings are persisted in PostgreSQL.

**Interactive analytics dashboard**: The Streamlit demo displays documents, chunks, queries, token usage, and estimated cost per organization.

**Dockerized vector database**: PostgreSQL with pgvector runs in Docker for reproducible local development.

## Architecture

The system follows a Clean Architecture approach where business logic is isolated from infrastructure concerns.

                 ┌───────────────┐
                 │   Client / UI │
                 │ (Streamlit /  │
                 │  Swagger UI)  │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │     FastAPI   │
                 │     Routers   │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │  Application  │
                 │    Use Cases  │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │     Domain    │
                 │ Entities +    │
                 │  Interfaces   │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Infrastructure│
                 │               │
                 │ PostgreSQL    │
                 │ pgvector      │
                 │ OpenAI        │
                 │ Storage       │
                 │ Embeddings    │
                 └───────────────┘

The domain and application layers are independent of infrastructure, allowing components such as the LLM provider, embedding model, or storage backend to be replaced without modifying business logic.

This structure keeps the system modular, testable, and extensible.

## Pipelines

The system follows an end-to-end ingestion and question-answering pipeline over organization-scoped document data.

### Create organization
```
Organization name
  ↓
Validate name
  ↓
Check organization does not already exist
  ↓
Generate API key
  ↓
Hash API key with SHA-256
  ↓
Persist organization with API key hash
  ↓
Return organization metadata + plain API key
```
### Document ingestion
```
PDF
  ↓
Authenticate organization via API key
  ↓
Parse text
  ↓
Generate SHA-256 document hash
  ↓
Check document is not already ingested for that organization
  ↓
Store document metadata in PostgreSQL
  ↓
Store raw document bytes in local storage
  ↓
Chunk text
  ↓
Generate embeddings
  ↓
Store chunks and embeddings in PostgreSQL + pgvector
```

### Question answering
```
Question
  ↓
Authenticate organization via API key
  ↓
Validate and persist query
  ↓
Generate question embedding
  ↓
Retrieve top-k chunks with pgvector similarity search
  ↓
Build prompt from question + retrieved chunks
  ↓
Call OpenAI LLM
  ↓
Persist final answer
  ↓
Persist LLM usage, latency, and cost
  ↓
Persist query–chunk links
  ↓
Return answer
```
### Analytics dashboard
```
Authenticated organization
  ↓
Retrieve organization metadata from database
  ↓
List documents and chunk counts
  ↓
List queries and associated LLM usage
  ↓
Aggregate token usage and cost
  ↓
Return analytics summary (documents, queries, tokens, cost, models used) for that organization
```
## API Endpoints

| Method | Endpoint           | Headers                 | Request Body                  | Description |
|------|-------------------|------------------------|------------------------------|-------------|
| POST | /organizations    | –                      | { "name": string }           | Create a new organization and generate an API key |
| POST | /ingest-document  | X-API-Key              | file (multipart/form-data)   | Upload and ingest a PDF document |
| POST | /questions        | X-API-Key              | { "question": string }       | Ask a question using Retrieval-Augmented Generation |
| GET  | /dashboard        | X-API-Key              | –                            | Retrieve organization analytics (documents, queries, token usage, cost) |

Authentication for organization-scoped endpoints is performed using the `X-API-Key` header.

Interactive API documentation is available at `/docs` when the FastAPI server is running.

## Tech Stack

| Backend | AI / RAG | Data | Tools |
|--------|----------|------|------|
| Python 3.11 | OpenAI API | PostgreSQL | Docker |
| FastAPI | SentenceTransformers | pgvector | pytest |
| Uvicorn | PyPDF | psycopg | Streamlit |
| SQLAlchemy | | | python-dotenv |
| Alembic | | | |

## Quickstart

### 1. Create and activate a virtual environment
```
python -m venv .venv
```
#### Windows
```
.venv\Scripts\activate
```
#### macOS / Linux
```
source .venv/bin/activate
```

### 2. Install dependencies
```
pip install -r requirements.txt
```

### 3. Configure Docker environment variables

Inside the `docker/` folder, duplicate the Docker env example file and fill in the PostgreSQL values.
```
DB_USER = postgres
DB_PASSWORD = postgres
DB_NAME = ai_knowledge_db
```

### 4. Start PostgreSQL with Docker
```
docker compose up
```

### 5. Configure application environment variables

In the project root, create a `.env` file based on the root `.env.example`.

This file contains the application configuration used by **FastAPI** to connect to PostgreSQL and OpenAI, including:

```
DB_USER = postgres
DB_PASSWORD = postgres
DB_NAME = ai_knowledge_db

DB_HOST = localhost
DB_PORT = 5432

OPENAI_MODEL = 
OPENAI_API_KEY = xxxxxx
```

### 6. Run the API
```
uvicorn app.api.main:app --reload
```

At this point, the system is running with:

- PostgreSQL + pgvector in Docker
- FastAPI application locally


### 7. Test the system

You can test the API in Swagger UI:
```
http://localhost:8000/docs
```

Or run the Streamlit demo:
```
streamlit run streamlit_demo.py
```

## License

This project is released under the MIT License.

