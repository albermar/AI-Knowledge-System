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

Production-style multi-tenant **Retrieval-Augmented Generation (RAG)** backend built with **FastAPI**, **PostgreSQL + pgvector**, **OpenAI embeddings**, and **OpenAI LLMs**.

Organizations can ingest documents and ask questions over their knowledge base using **semantic search + LLM generation**.

The system tracks **queries, token usage, model usage, latency, and estimated cost per organization**, and exposes a **dashboard API** for analytics and monitoring.

A **Streamlit demo application** is included to allow users to:

- create organizations
- upload documents
- ask questions
- inspect system usage and statistics

Live demo:  
https://ai-knowledge-system-rag.streamlit.app/

API documentation:
https://ai-knowledge-api-a2kk.onrender.com/docs

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

- **Multi-tenant architecture**  
  Each organization operates in an isolated workspace identified by an API key.

- **Document ingestion pipeline**  
  Upload PDF documents that are parsed and processed into smaller chunks.

- **Text chunking**  
  Documents are split into manageable text chunks to improve retrieval accuracy.

- **OpenAI embeddings**  
  Each chunk is converted into a vector representation using **OpenAI embedding models**.

- **Vector storage with pgvector**  
  Embeddings are stored in PostgreSQL using the **pgvector** extension for similarity search.

- **Semantic retrieval**  
  User questions are embedded and matched against stored chunks using **vector similarity search**.

- **Retrieval-Augmented Generation (RAG)**  
  The most relevant chunks are injected into the prompt and answered by an **OpenAI LLM**.

- **Query persistence**  
  Every user query is stored for observability and analytics.

- **Chunk attribution**  
  The system records which chunks were used to generate each answer.

- **LLM usage tracking**  
  Prompt tokens, completion tokens, total tokens, latency, model name, and estimated cost are tracked.

- **Organization analytics endpoint**  
  Aggregated statistics are available per organization (documents, chunks, queries, token usage, cost).

- **Streamlit demo interface**  
  A simple UI allows users to:
  - create organizations
  - upload documents
  - ask questions
  - inspect system statistics

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
Generate embeddings using OpenAI Embeddings API
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
Generate question embedding using OpenAI Embeddings API
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
| FastAPI | OpenAI Embeddings | pgvector | pytest |
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

