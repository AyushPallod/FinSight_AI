# FinSight AI

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**FinSight AI** is an advanced Retrieval-Augmented Generation (RAG) platform designed specifically for processing and analyzing complex financial documents. Utilizing a powerful stack of modern AI and web technologies, FinSight AI allows users to upload financial PDFs, extract critical insights, and chat with an intelligent AI assistant grounded purely on the uploaded documents.

---

## 🎯 Project Highlights (MLOps / GenAI)

**Tech Stack:** FastAPI, Qdrant, Postgres, Redis, Celery, Ollama, Prometheus, Grafana, RAGAS, Docker Compose, GitHub Actions

- Built a production-grade hybrid RAG platform (BM25 + BGE-M3 dense retrieval, RRF fusion) for financial document intelligence, delivering cited answers from 10-K/10-Q filings and earnings transcripts.
- Engineered a 9-service Docker Compose architecture (FastAPI, Postgres, Redis, Celery workers, Qdrant, Ollama, Prometheus, Grafana, Nginx) with async background processing for ingestion/OCR/embedding pipelines.
- Quantified RAG quality with a RAGAS evaluation harness (faithfulness, context precision/recall, answer relevancy) and enforced guardrails for prompt-injection detection and PII redaction pre-indexing.
- Instrumented full observability (Prometheus + Grafana) tracking p50/p95/p99 API latency, retrieval/LLM generation latency, and live quality metrics; shipped via GitHub Actions CI/CD to GPU infrastructure.

---

## 🚀 Key Features

* **Intelligent Document Processing:** Seamlessly upload and chunk financial PDFs for optimal retrieval.
* **Retrieval-Augmented Generation (RAG):** Answers are grounded in your data, preventing hallucinations.
* **Local LLM Integration:** Powered by Ollama (Llama 3), ensuring data privacy and local execution.
* **Advanced Vector Search:** Utilizes Qdrant for highly scalable and lightning-fast semantic search.
* **AI Quality Evaluation:** Built-in RAGAS (Retrieval Augmented Generation Assessment) to continuously measure Faithfulness, Answer Relevancy, and Context Recall.
* **Safety Guardrails:** Real-time protection against prompt injection, toxic content, and jailbreak attempts.
* **Comprehensive Observability:** Deep monitoring with Prometheus and Grafana dashboards for both System Health and AI Quality metrics.
* **Secure Architecture:** Nginx Reverse Proxy with HTTPS support.

---

## 📸 Screenshots

*(Replace the placeholders below with the actual screenshots once taken)*

### System Dashboard (Grafana)
![System Health Dashboard](docs/images/grafana_system_health.png)
*Real-time monitoring of API latency, request rates, error rates, and cache hits.*

### AI Quality Dashboard (Grafana)
![AI Quality Dashboard](docs/images/grafana_ai_quality.png)
*RAGAS evaluation metrics showing Faithfulness and Answer Relevancy of the LLM responses.*

### Nginx HTTPS Landing Page
![HTTPS Proxy](docs/images/nginx_https.png)
*Secure HTTPS reverse proxy routing traffic successfully.*

### Grounded AI Chat
![Grounded Response](docs/images/chat_grounded_response.png)
*Intelligent chat interface providing answers directly cited from uploaded 10-K financial documents.*

---

## 🏗️ Architecture

FinSight AI employs a robust microservices architecture orchestrated with Docker Compose:

1. **Frontend:** React-based UI for seamless user interactions.
2. **Backend:** FastAPI application handling API requests, RAG pipelines, and logic.
3. **Database (PostgreSQL):** Relational store for user and document metadata.
4. **Vector Database (Qdrant):** Stores document embeddings for semantic search.
5. **Cache/Broker (Redis):** Caching layer and message broker for background tasks.
6. **Task Worker (Celery):** Asynchronous background processing (e.g., document chunking and embeddings).
7. **LLM Server (Ollama):** Local inference engine.
8. **Reverse Proxy (Nginx):** API Gateway and HTTPS termination.
9. **Metrics Scraper (Prometheus):** Aggregates telemetry data.
10. **Visualization (Grafana):** Dashboards for system and AI observability.

---

## 🛠️ Setup & Installation

### Prerequisites
* Docker and Docker Compose (Docker Desktop recommended on Windows/Mac)
* Git

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YourUsername/FinSight_AI.git
   cd FinSight_AI
   ```

2. **Generate Self-Signed Certificates (For Local HTTPS):**
   *A Python script is provided to automatically generate local certificates.*
   ```bash
   python generate_certs.py
   ```

3. **Start the Stack:**
   *Spin up all 10 services using Docker Compose.*
   ```bash
   docker compose up --build -d
   ```

4. **Access the Services:**
   * **Main App (HTTPS):** `https://localhost`
   * **API Docs (Swagger):** `https://localhost/docs`
   * **Grafana Dashboards:** `http://localhost:3000` (Login: `admin` / `admin`)
   * **Prometheus:** `http://localhost:9090`

---

## 🛡️ Production Readiness

While this project is configured for a robust local deployment, the following steps are recommended before deploying to a production environment:

1. **SSL Certificates:** Replace the self-signed certificates with a trusted CA like Let's Encrypt. The `nginx.conf` contains comments on how to configure this easily.
2. **Secrets Management:** Change all default passwords and secrets in `.env` or `docker-compose.yml`.
3. **Hardware:** A GPU is highly recommended for the Ollama inference server and embedding generation.

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
