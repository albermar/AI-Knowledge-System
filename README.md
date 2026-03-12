# AI-Knowledge-System
Production-grade ai-powered system capable of generating grounded responses to clients using previously updated documents (RAG)

Starting project
# AI Knowledge System API

![Python](https://img.shields.io/badge/python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-database-blue)
![pgvector](https://img.shields.io/badge/pgvector-vector--search-purple)
![OpenAI](https://img.shields.io/badge/OpenAI-LLM-black)
![pytest](https://img.shields.io/badge/tests-pytest-orange)
![Docker](https://img.shields.io/badge/docker-supported-blue)
![Architecture](https://img.shields.io/badge/architecture-clean--architecture-red)

A production-style Retrieval-Augmented Generation (RAG) backend that allows organizations to ingest documents and query them using LLMs.

## Table of Contents

1. [Overview](#1-overview)
2. [Demo](#2-demo)
3. [Key Features](#3-key-features)
4. [Architecture](#4-architecture)
5. [RAG Pipeline](#5-rag-pipeline)
6. [Tech Stack](#6-tech-stack)
7. [Project Structure](#7-project-structure)
8. [API Endpoints](#8-api-endpoints)
9. [Running the Project](#9-running-the-project)
10. [Testing](#10-testing)
11. [Design Decisions](#11-design-decisions)
12. [Future Improvements](#12-future-improvements)

## 1. Overview

**AI Knowledge System API** is a backend service that allows organizations to ingest documents and ask questions about them using a **Retrieval-Augmented Generation (RAG)** pipeline.

The system extracts text from uploaded PDFs, splits the content into semantic chunks, generates embeddings, and stores them for **vector similarity search**. When a user asks a question, the system retrieves the most relevant chunks and builds a contextual prompt for a Large Language Model (LLM) to generate the final answer.

This project is designed as a **production-style backend system** demonstrating:

* Clean Architecture (Domain / Application / Infrastructure separation)
* Multi-tenant document knowledge bases
* Embedding-based semantic search
* LLM integration for contextual question answering
* Persistent query tracking and usage analytics
* Robust error handling and test coverage

The API exposes three core capabilities:

* **Organization management** – create organizations and issue API keys
* **Document ingestion** – upload PDFs that are parsed, chunked, and embedded
* **Question answering** – query the knowledge base using an LLM with retrieved context

The high-level flow of the system is illustrated below:

```text
PDF Upload
   ↓
Parse + Chunk
   ↓
Generate Embeddings
   ↓
Store in PostgreSQL + pgvector
   ↓
Ask Question
   ↓
Retrieve Relevant Chunks
   ↓
Build Prompt
   ↓
LLM Answer
```

**Project highlights**

- Clean Architecture backend
- RAG pipeline with pgvector
- 29 automated tests (pytest)
- Dockerized PostgreSQL environment

## 2. Demo

Below is a minimal example showing how the API can be used end-to-end.

### Step 1 - Create an Organization

```bash
curl -X POST http://localhost:8000/api/organizations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "demo-company"
  }'
```

Example response:

```json
{
  "id": "c9a5c7c2-6c3c-4b1f-9c2d-9d1e5c3d8a45",
  "name": "demo-company",
  "api_key": "xxxxxxxxxxxxxxxxxxxxxxxxx",
  "created_at": "2026-03-12T10:00:00Z"
}
```

Save the returned **API key**. It will be required for all subsequent requests.

---

### Step 2 - Ingest a Document

```bash
curl -X POST http://localhost:8000/api/ingest-document \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@example.pdf"
```

Example response:

```json
{
  "organization_id": "c9a5c7c2-6c3c-4b1f-9c2d-9d1e5c3d8a45",
  "document_id": "4e7c0c5f-9f7d-4a9b-bb9b-4cbe6a8d6f10",
  "document_hash": "c1f8f0e8e2a1c8e6f6c6d3c9e9f7b2c6c1a7d5f0e3a2c9d6f4e1a3b7c8d9e0f",
  "chunks_created": 18
}
```

The system will:

1. Extract text from the PDF
2. Split the document into chunks
3. Generate embeddings
4. Store the chunks for vector search

---

### Step 3 - Ask a Question

```bash
curl -X POST http://localhost:8000/api/questions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "question": "What is this document about?"
  }'
```

Example response:

```json
{
  "query_id": "93f5c551-d617-4a1b-a42a-90ecbf6e0abb",
  "question": "What is this document about?",
  "model_name": "gpt-4.1-mini",
  "prompt_tokens": 1487,
  "completion_tokens": 103,
  "total_tokens": 1590,
  "answer": "The document discusses the importance of obsession as a driver of success in business and life.",
  "latency_ms": 2849,
  "estimated_cost_usd": 0.00076
}
```

The answer is generated using a **Retrieval-Augmented Generation (RAG)** pipeline:

1. Embed the question
2. Retrieve the most relevant chunks from the knowledge base
3. Build a contextual prompt
4. Call the LLM
5. Return the generated answer with usage metadata


## 3. Key Features

### Multi-Tenant Knowledge Base

Each organization has its own isolated document knowledge base.
Requests are authenticated using API keys, ensuring that queries only access documents belonging to the requesting organization.

---

### Retrieval-Augmented Generation (RAG)

The system answers questions using a full **RAG pipeline**:

1. The user question is converted into an embedding.
2. The system performs **vector similarity search** to retrieve the most relevant document chunks.
3. Retrieved chunks are injected into a structured prompt.
4. The prompt is sent to an LLM to generate a contextual answer.

This approach allows the model to answer questions **based only on the ingested documents**, improving reliability and reducing hallucinations.

---

### Clean Architecture

The project follows a **Clean Architecture** approach with strict separation between:

* **Domain layer** — core entities and interfaces
* **Application layer** — use cases and business logic
* **Infrastructure layer** — database, embeddings, storage, LLM clients
* **API layer** — FastAPI routers and request/response schemas

This structure keeps business logic independent from frameworks and external services.

---

### Document Processing Pipeline

When a document is uploaded:

1. The PDF is parsed and converted into plain text.
2. The text is split into overlapping chunks.
3. Each chunk is embedded using a sentence-transformer model.
4. Chunks are stored for future semantic search.

This pipeline enables efficient retrieval of relevant context for questions.

---

### Vector Search for Context Retrieval

Instead of keyword matching, the system performs **semantic search** using embeddings.

This allows questions to match relevant content even if the wording differs from the original document.

---

### Query Tracking and LLM Usage Metrics

Every question asked to the system is persisted with metadata such as:

* prompt tokens
* completion tokens
* total tokens
* model used
* estimated cost
* latency

This makes the system suitable for **monitoring usage and estimating LLM costs**.

---

### Robust Error Handling

The application defines structured domain exceptions for scenarios such as:

* invalid organization
* duplicate document ingestion
* empty questions
* missing relevant chunks
* persistence errors

This improves reliability and keeps API responses predictable.

---

### Testable Architecture

Because the system relies on interfaces and dependency injection, components can easily be replaced with mocks or fakes.

For example:

* a **Fake LLM client** is used during endpoints testing
* repositories can be replaced with in-memory implementations

This enables **fast and reliable unit and integration testing**.


## 4. Architecture

The system is designed following **Clean Architecture principles**, separating business logic from infrastructure and external services.
This makes the system easier to test, extend, and maintain.

The project is divided into four main layers:

* **API Layer** — HTTP endpoints, request validation, and response schemas
* **Application Layer** — use cases that orchestrate business logic
* **Domain Layer** — core entities, interfaces, and domain rules
* **Infrastructure Layer** — database repositories, embeddings, storage, and external services

---

### High-Level Architecture

```
                 ┌──────────────┐
                 │   Client     │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │   FastAPI    │
                 │    Routers   │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │   Use Cases  │
                 │ Ask / Ingest │
                 └──────┬───────┘
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
   ┌───────────┐ ┌────────────┐ ┌─────────────┐
   │ PostgreSQL│ │ Embeddings │ │   Storage   │
   │ + pgvector│ │  Model     │ │   (PDFs)    │
   └───────────┘ └────────────┘ └─────────────┘
                        │
                        ▼
                  ┌─────────┐
                  │  OpenAI │
                  │   LLM   │
                  └─────────┘
```

---

### Layer Responsibilities

#### API Layer

Responsible for handling HTTP requests and responses.

* FastAPI routers
* Pydantic request/response schemas
* Dependency injection
* Authentication via API keys

---

#### Application Layer

Contains **use cases** that orchestrate business operations.

Examples:

* `NewOrganization`
* `IngestDocument`
* `AskQuestion`

Use cases coordinate repositories, services, and external systems.

---

#### Domain Layer

Defines the core concepts of the system:

* Entities (Organization, Document, Chunk, Query)
* Repository interfaces
* LLM and embedding interfaces
* Domain validation rules

The domain layer **does not depend on any framework or database**.

---

#### Infrastructure Layer

Implements the domain interfaces using real technologies.

Examples include:

* PostgreSQL repositories
* SentenceTransformer embeddings
* Local document storage
* OpenAI LLM client
* PDF parsing

Because the infrastructure implements interfaces, it can be swapped without changing business logic.

---

### Benefits of This Architecture

* Clear separation of concerns
* Testable business logic
* Framework independence
* Easier refactoring and scaling
* Replaceable external services (LLM, embeddings, storage)

This structure is commonly used in **production backend systems** where long-term maintainability is critical.

## 5. RAG Pipeline

This project implements a **Retrieval-Augmented Generation (RAG)** pipeline to answer questions based on ingested documents.

Instead of asking the language model directly, the system first retrieves the most relevant document fragments and includes them as context in the prompt. This allows the model to generate answers grounded in the ingested knowledge base.

---

### Pipeline Overview

```text
User Question
      │
      ▼
Embed Question
      │
      ▼
Vector Similarity Search
      │
      ▼
Retrieve Top-K Chunks
      │
      ▼
Build Prompt
      │
      ▼
Call LLM
      │
      ▼
Return Answer
```

---

### Step-by-Step Explanation

#### Step 1 - Question Embedding

The user's question is converted into a numerical vector representation using an embedding model.

This embedding captures the **semantic meaning** of the question.

---

#### Step 2 - Vector Similarity Search

The question embedding is compared against the stored embeddings of all document chunks.

The system retrieves the **Top-K most similar chunks** using vector similarity search.

These chunks represent the most relevant context for answering the question.

---

#### Step 3 - Context Retrieval

The retrieved chunks are collected and formatted as contextual information.

Each chunk contains:

* chunk content
* chunk index
* similarity score

This metadata helps trace which parts of the documents were used to answer the question.

---

#### Step 4 - Prompt Construction

A prompt is constructed using:

* the user question
* the retrieved chunks

Example structure:

```text
You are a helpful assistant.
Answer the user's question using only the provided context.

Question:
<user question>

Context:
<retrieved chunks>

Answer:
```

This forces the model to rely only on the provided document context.

---

#### Step 5 - LLM Answer Generation

The prompt is sent to a language model which generates the final answer.

The system also records metadata such as:

* model name
* prompt tokens
* completion tokens
* total tokens
* latency
* estimated cost

---

### Why RAG?

Retrieval-Augmented Generation has several advantages over direct LLM queries:

* Reduces hallucinations
* Allows models to answer based on private data
* Keeps knowledge bases up to date without retraining models
* Improves transparency by showing retrieved context

This architecture is widely used in **modern AI knowledge systems and document question-answering platforms**.

## 6. Tech Stack

This project combines modern backend technologies with AI tooling to build a production-style **Retrieval-Augmented Generation (RAG)** system.

---

### Backend Framework

* **FastAPI** — High-performance Python web framework for building APIs
* **Pydantic** — Data validation and serialization for request/response models

FastAPI provides automatic OpenAPI documentation and strong typing support.

---

### Database & Persistence

* **PostgreSQL** — Primary relational database
* **SQLAlchemy** — ORM used to interact with the database
* **Alembic** — Database migrations and schema versioning

The database stores:

* organizations
* documents
* document chunks
* queries
* query–chunk relationships
* LLM usage metrics

---

### Embeddings & Semantic Search

* **SentenceTransformers** — Used to generate text embeddings
* **Vector similarity search** — Used to retrieve the most relevant chunks for a query

Embeddings allow the system to perform **semantic search** rather than keyword matching.

---

### Large Language Models

* **OpenAI API** — Used for answer generation
* **LLM client abstraction** — allows replacing the provider if needed

The system records metadata about each LLM call, including tokens, latency, and estimated cost.

---

### Document Processing

* **pypdf** — Extracts text from uploaded PDF documents

Documents are parsed, chunked, embedded, and stored for later retrieval.

---

### Testing

* **Pytest** — Unit and integration testing
* **FastAPI TestClient** — API endpoint testing

Tests cover:

* use cases
* repositories
* API endpoints

---

### Development Tools

* **Python 3.11+**
* **Virtual environments**
* **Environment variables (.env)**

The project is designed to be easy to run locally while following patterns used in real backend services.

---

### Key Design Principles

The tech stack was chosen to support:

* modular architecture
* testability
* replaceable infrastructure
* scalable document processing
* cost-aware LLM integration

## 7. Project Structure

The project is organized following **Clean Architecture principles**, separating business logic from infrastructure and external frameworks.

```text
project-root
│
├── app
│   │
│   ├── api
│   │   ├── dependencies.py
│   │   ├── main.py
│   │   ├── router_1_ingest_document.py
│   │   ├── router_2_add_organization.py
│   │   ├── router_3_ask_question.py
│   │   └── schemas.py
│   │
│   ├── application
│   │   ├── dto.py
│   │   ├── exceptions.py
│   │   ├── use_cases.py
│   │   └── services
│   │       ├── api_key.py
│   │       ├── chunker.py
│   │       └── prompt_builder.py
│   │
│   ├── domain
│   │   ├── entities.py
│   │   ├── interfaces.py
│   │   └── types.py
│   │
│   └── infra
│       ├── db
│       │   ├── base.py
│       │   ├── db_url_builder.py
│       │   ├── engine.py
│       │   ├── implementations.py
│       │   └── ormmodels.py
│       │
│       ├── embedder
│       │   └── implementations.py
│       │
│       ├── llm
│       │   └── implementations.py
│       │
│       ├── parser
│       │   └── implementations.py
│       │
│       ├── retriever
│       │   └── implementations.py
│       │
│       └── storage
│           └── implementations.py
│
├── tests
│   ├── routers
│   │   ├── test_router_1_ingest_document.py
│   │   ├── test_router_2_add_organization.py
│   │   └── test_router_3_ask_question.py
│   │
│   └── use_cases
│       ├── helpers.py
│       ├── test_ask_question.py
│       ├── test_ingest_document.py
│       └── test_new_organization.py
│
├── scripts
│   ├── manual_test_ask_question.py
│   ├── manual_test_ingest.py
│   └── manual_test_vector_search.py
│
├── alembic
│   └── versions
│       ├── 7fd0d63c41f0_init.py
│       ├── 439b654186b2_add_document_hash_to_document.py
│       ├── e0b52fd47e79_add_embedding_to_chunks.py
│       └── eaad2f43ced3_add_api_key_hash_to_organizations.py
│
├── alembic.ini
├── docker-compose.yml
├── requirements.txt
├── .env
└── README.md
```

### Directory Responsibilities

#### `app/domain`
Contains the **core business concepts** of the system.

Includes:
- entities
- repository interfaces
- domain types

The domain layer **does not depend on any framework**.

#### `app/application`
Implements the **business logic of the system** through use cases.

Examples include:
- creating organizations
- ingesting documents
- answering questions

Application services also contain helpers such as chunking, prompt building, and API key hashing.

#### `app/infra`
Contains the **concrete implementations** of the domain interfaces.

Examples:
- PostgreSQL repositories
- embedding models
- LLM clients
- document storage
- PDF parsing
- retrievers

This layer integrates the system with external technologies.

#### `app/api`
Handles **HTTP communication**.

Includes:
- FastAPI routers
- request validation
- response serialization
- dependency injection
- authentication wiring

The API layer is responsible only for translating HTTP requests into application use cases.

#### `tests`
Contains automated tests for the system.

Tests are divided into:

- **router tests** — validate full API behavior end-to-end
- **use case tests** — validate business logic independently of HTTP

This separation helps keep the system reliable and easier to refactor.

## 8. API Endpoints

The API exposes three main endpoints that allow clients to manage organizations, ingest documents, and query the knowledge base.

All protected endpoints require authentication using the `X-API-Key` header.

---

### Create Organization

Creates a new organization and returns an API key that will be used to authenticate future requests.

**Endpoint**

```
POST /api/organizations
```

**Request Body**

```json
{
  "name": "demo-company"
}
```

**Response**

```json
{
  "id": "c9a5c7c2-6c3c-4b1f-9c2d-9d1e5c3d8a45",
  "name": "demo-company",
  "api_key": "xxxxxxxxxxxxxxxxxxxxxxxxx",
  "created_at": "2026-03-12T10:00:00Z"
}
```

The API key must be stored securely by the client and included in future requests.

---

### Ingest Document

Uploads a PDF document and processes it into searchable chunks.

The ingestion pipeline performs:

1. PDF text extraction
2. Document chunking
3. Embedding generation
4. Chunk storage for vector search

**Endpoint**

```
POST /api/ingest-document
```

**Headers**

```
X-API-Key: YOUR_API_KEY
```

**Request**

Multipart form upload:

```
file=@example.pdf
```

**Response**

```json
{
  "organization_id": "c9a5c7c2-6c3c-4b1f-9c2d-9d1e5c3d8a45",
  "document_id": "4e7c0c5f-9f7d-4a9b-bb9b-4cbe6a8d6f10",
  "document_hash": "c1f8f0e8e2a1c8e6f6c6d3c9e9f7b2c6c1a7d5f0e3a2c9d6f4e1a3b7c8d9e0f",
  "chunks_created": 18
}
```

---

### Ask Question

Queries the knowledge base using a Retrieval-Augmented Generation pipeline.

The system retrieves relevant document chunks and sends them to the LLM to generate a contextual answer.

**Endpoint**

```
POST /api/questions
```

**Headers**

```
X-API-Key: YOUR_API_KEY
Content-Type: application/json
```

**Request Body**

```json
{
  "question": "What is this document about?"
}
```

**Response**

```json
{
  "query_id": "93f5c551-d617-4a1b-a42a-90ecbf6e0abb",
  "question": "What is this document about?",
  "model_name": "gpt-4.1-mini",
  "prompt_tokens": 1487,
  "completion_tokens": 103,
  "total_tokens": 1590,
  "answer": "The document discusses the importance of obsession as a driver of success in business and life.",
  "latency_ms": 2849,
  "estimated_cost_usd": 0.00076
}
```

The response includes metadata about the LLM call such as token usage, latency, and estimated cost.

## 9. Running the Project

Follow these steps to run the API locally.

### 9.1 Clone the Repository

```bash
git clone https://github.com/albermar/ai-knowledge-system-rag.git
cd ai-knowledge-system-rag
```

### 9.2 Create a Virtual Environment

```bash
python -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

### 9.3 Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 9.4 Configure Docker Database Environment

Inside the `docker` folder create a `.env` file:

```env
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=ai_knowledge_system
```

---

### 9.5 Start PostgreSQL

From inside the `docker` directory run:

```bash
docker compose up -d
```

This starts a PostgreSQL instance with the **pgvector extension** enabled.

---

### 9.6 Configure Application Environment

In the **project root**, create a `.env` file:

```env
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=ai_knowledge_system
DB_HOST=localhost
DB_PORT=5432

OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
```

---

### 9.7 Run Database Migrations

```bash
alembic upgrade head
```

This will create all required database tables.

---

### 9.8 Start the API Server

```bash
uvicorn app.api.main:app --reload
```

The API will be available at:

```
http://localhost:8000
```

---

### 9.9 Open Interactive API Documentation

FastAPI provides built-in documentation at:

```
http://localhost:8000/docs
```

You can use this interface to test all endpoints directly from the browser.


## 10. Testing

The project includes automated tests to validate both the **business logic** and the **API layer**.

Tests are implemented using **pytest** and **FastAPI TestClient**.

---

### 10.1 Test Structure

Tests are organized according to the architecture layers:

```
tests
│
├── routers
│   ├── test_router_1_ingest_document.py
│   ├── test_router_2_add_organization.py
│   └── test_router_3_ask_question.py
│
└── use_cases
    ├── helpers.py
    ├── test_ask_question.py
    ├── test_ingest_document.py
    └── test_new_organization.py
```

---

### 10.2 Types of Tests

#### Router Tests

Router tests verify the **API endpoints** using FastAPI's `TestClient`.

They ensure:

- correct HTTP status codes
- request validation
- authentication behavior
- integration with the application layer

Example endpoints tested:

- `POST /api/organizations`
- `POST /api/ingest-document`
- `POST /api/questions`

---

#### Use Case Tests

Use case tests validate the **core business logic** independently of the API layer.

They verify:

- document ingestion orchestration
- chunk creation
- query processing
- organization creation
- error handling

This allows testing business logic without requiring HTTP requests.

---

### 10.3 Running Tests

Run all tests using:

```bash
pytest
```

Run tests in quiet mode:

```bash
pytest -q
```

Example output:

```
80 passed in 260.74s (0:04:20) 
```

---

### 10.4 Why This Testing Approach?

The project separates tests into **API-level tests** and **application-layer tests** to ensure:

- reliable behavior of business logic
- correct API integration
- easier refactoring of infrastructure components

This structure mirrors the system architecture and keeps tests maintainable as the project grows.

## 11. Design Decisions
- Clean Architecture to isolate business logic
- Interface-based infrastructure for testability
- pgvector for semantic search without external vector DB
- LLM abstraction to avoid vendor lock-in

## 12. Future Improvements
- Streaming LLM responses
- Async ingestion pipeline
- Hybrid retrieval (BM25 + vector)
- Observability and metrics

## 13. Author

**Alberto Bermejillo Martín-Romo**

Backend & AI Engineer

GitHub  
https://github.com/albermar
