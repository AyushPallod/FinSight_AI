# FinSight AI

FinSight AI is a production-grade Retrieval-Augmented Generation (RAG) platform designed for financial document intelligence. It ingests complex financial documents (like 10-K/10-Q filings, transcripts, and reports), generates semantic embeddings, performs hybrid search, and provides LLM-grounded answers with page-level citations.

## Tech Stack
- **Frontend:** React, TypeScript, Tailwind CSS (v4), Vite
- **Backend:** FastAPI (Python 3.10+)
- **Database:** PostgreSQL (Users, Documents, Chat history metadata)
- **Vector DB:** Qdrant
- **Caching/Queue:** Redis & Celery
- **LLM/Embeddings:** Llama 3.2 via Ollama, BAAI BGE-M3
- **Monitoring & Observability:** Prometheus & Grafana

## Directory Structure
```
FinSight/
├── backend/            # FastAPI Backend Application
│   ├── app/            # Source code
│   └── requirements.txt
├── frontend/           # React + TypeScript + Tailwind CSS Frontend
├── docker/             # Docker deployment configurations
├── docs/               # Architecture diagrams and documentation
└── README.md
```

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js & npm
- Docker (for Qdrant, Postgres, Redis)
- Ollama running locally with `llama3.2` model pulled:
  ```bash
  ollama run llama3.2
  ```

### Development Setup

Detailed setup guides for backend and frontend will be added as implementation progresses.
