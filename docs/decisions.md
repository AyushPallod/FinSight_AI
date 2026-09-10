# Engineering Decisions


This document captures the key engineering decisions made while building FinSight AI. It is intended to demonstrate the thoughtful trade‑offs and design rationale.

1️⃣ Hybrid Retrieval Architecture
* What I did: Implemented a dual‑retrieval pipeline that combines BM25 classic lexical search with dense vector search using the BGE‑M3 model. Results from both rankers are fused with Reciprocal Rank Fusion (RRF).
* Why: BM25 guarantees high recall on exact keyword matches, while dense embeddings capture semantic similarity. The fusion dramatically improves answer relevance for complex financial language.
* Alternatives considered: Pure dense‑only retrieval (simpler, but suffered on domain‑specific jargon) and pure BM25 (missed semantic matches). The hybrid approach gave the best F1/Recall on our internal test set.


2️⃣ Containerised Micro‑service Architecture (Docker‑Compose)
* What I did: Split the system into 9 isolated services (FastAPI, Postgres, Redis, Celery workers, Qdrant, Ollama, Prometheus, Grafana, Nginx) and orchestrated them with Docker‑Compose.
* Why: Guarantees reproducible environments across dev, CI, and production, enables independent scaling (e.g., spin up extra Celery workers for heavy ingestion) and isolates failures.
* Alternatives considered: Monolithic deployment using a single Dockerfile or a Kubernetes cluster. Monolith reduced operational overhead but limited scalability; Kubernetes added unnecessary complexity for a single‑node deployment.


3️⃣ Asynchronous Background Processing with Celery + Redis
* What I did: Off‑loaded PDF ingestion, OCR, chunking, PII scrubbing, and embedding generation to Celery workers backed by Redis.
* Why: Keeps the FastAPI request‑response path fast (<200 ms) and provides reliable task retry semantics. The system can handle concurrent uploads without blocking the UI.
* Alternatives considered: Direct synchronous processing in the API (simple but blocked threads) and using Python's asyncio with a custom worker pool (more code complexity). Celery offered battle‑tested reliability.


4️⃣ RAGAS‑Based Quality Evaluation
* What I did: Integrated the RAGAS framework to compute Faithfulness, Answer Relevancy, Context Precision, and Context Recall after each query; exported these as Prometheus gauges.
* Why: Provides a quantitative, continuous feedback loop for model performance, allowing the team to set SLOs and detect regressions early.
* Alternatives considered: Manual human evaluation (high fidelity but not scalable) and using only perplexity/likelihood metrics (poor correlation with downstream relevance). RAGAS gave a balanced, automated metric suite.


5️⃣ Full Observability Stack (Prometheus + Grafana)
* What I did: Instrumented FastAPI with prometheus_fastapi_instrumentator, added custom gauges for RAGAS scores, and built two Grafana dashboards (System Health & AI Quality).
* Why: Enables real‑time monitoring of latency percentiles (p50‑p99), error rates, cache hit‑miss ratios, and AI quality trends—critical for an MLOps‑focused role.
* Alternatives considered: Using third‑party SaaS observability (Datadog, New Relic) which would incur cost and vendor lock‑in; or logging‑only approach (harder to set alerts). Open‑source stack kept costs low and gave full control.


6️⃣ Nginx Reverse Proxy with Self‑Signed HTTPS (Development)
* What I did: Configured Nginx to terminate TLS and proxy traffic to the FastAPI backend, generating a self‑signed certificate via generate_certs.py.
* Why: Demonstrates production‑grade security posture and allows the UI to be served over HTTPS, satisfying compliance checks.
* Alternatives considered: Direct exposure of FastAPI over HTTP (simpler but insecure) and using a managed TLS service (adds external dependency). Nginx gave fine‑grained control while staying fully self‑hosted.


7️⃣ PII Scrubbing & Content Safety Guardrails
* What I did: Ran a spaCy NER pipeline on extracted text to mask personal identifiers before indexing, and added prompt‑injection detection using custom regex patterns.
* Why: Meets regulatory compliance for handling confidential financial documents and does data sanitisation.
* Alternatives considered: Relying solely on model‑level safety (LLM‑based redaction) – less reliable; or skipping redaction entirely (fastest) – unacceptable for a financial‑data product.



🔥 Hardest Decision & Rejected Alternative
* Decision: Whether to use a managed cloud LLM API (e.g., OpenAI GPT‑4) or a local Ollama LLM for the generation component.
* Chosen path: Local Ollama LLM.
* Reasoning: It's on‑premise, secure AI for financial data, with strict latency SLAs. By keeping inference in‑house we avoid data‑exfiltration, achieve consistent sub‑second response times, and eliminate unpredictable cloud costs.
Rejected alternative: Integrating a cloud‑hosted LLM. It would have reduced engineering effort (no model serving infra) and offered higher model quality out‑of‑the‑box. However, the associated data‑privacy concerns, cost‑escalation at scale, and network latency violations made it untenable for a production‑grade, compliance‑sensitive solution.


---

Alignment With the JD of TRIOLOGY
* MLOps expertise: Full CI/CD with Docker‑Compose, Prometheus‑Grafana monitoring, and automated RAGAS evaluation.
* Scalable architecture: Micro‑services, async processing, and secure TLS termination.
* Data security: PII scrubbing, on‑premise LLM, strict access controls.
* Observability: Real‑time metrics, alerting, and dashboarding.
* Performance focus: Hybrid retrieval for high relevance, latency tracking, and background workers for heavy workloads.


These decisions collectively demonstrate a production‑ready, secure, and observable AI system ready to meet the expectations outlined in the job description.