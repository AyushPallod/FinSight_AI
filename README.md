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


1. Stopping the Containers
Depending on how cleanly you want to stop the services:

Stop and Remove Containers (Recommended):

powershell
docker compose down
This stops the containers and removes them from the network, but preserves all database data (PostgreSQL/Qdrant) because they are stored in persistent Docker volumes.

Pause/Stop Containers (Without removing them):

powershell
docker compose stop
This temporarily halts the running processes. You can resume them quickly without recreating the container interfaces.

2. Starting the Containers
Start in Detached Mode (Background - Recommended):

powershell
docker compose up -d
This starts all the services defined in your docker-compose.yml file in the background, freeing up your terminal.

Start Containers (If you previously used stop):

powershell
docker compose start
3. Rebuilding after Code Edits
If you make modifications to the backend code, frontend files, or requirements.txt:

Rebuild and Start:
powershell
docker compose up -d --build
This checks if any files have changed, rebuilds the corresponding image layers (utilizing cache where possible), and replaces the running containers with the updated version.
4. Monitoring Logs and Status
Check Service Status & Health Checks:

powershell
docker compose ps
Stream Live Logs for a Specific Service (e.g., Backend):

powershell
docker compose logs -f backend
Stream Live Logs for the Background Worker:

powershell
docker compose logs -f celery-worker

$env:OLLAMA_HOST="0.0.0.0:11434"
ollama serve
