import os
import glob
import json
import time
import uuid
import structlog
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Gauge
from sqlalchemy.orm import Session

from app.core.config import settings
from app.routers import documents, search, chat, auth
from app.core.database import engine, Base, get_db
from app.models.user import User  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.chat import ChatMessage  # noqa: F401
from app.core.metrics import update_active_documents_gauge
from app.core.security import decode_token

# Automatically create database tables (SQLite finsight.db) on startup
Base.metadata.create_all(bind=engine)

# Configure structlog to output clean JSON lines to stdout
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
structlog_logger = structlog.get_logger()

# Define evaluation metrics gauges (scraped via /eval-metrics)
ragas_faithfulness = Gauge(
    "ragas_faithfulness", "Latest RAGAS evaluation faithfulness score"
)
ragas_answer_relevancy = Gauge(
    "ragas_answer_relevancy", "Latest RAGAS evaluation answer relevancy score"
)
ragas_context_precision = Gauge(
    "ragas_context_precision", "Latest RAGAS evaluation context precision score"
)
ragas_context_recall = Gauge(
    "ragas_context_recall", "Latest RAGAS evaluation context recall score"
)

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Instrument the FastAPI app to collect request metrics
Instrumentator().instrument(app)


# LogMiddleware: captures request_id, endpoint, user_id (decoded from JWT), latency, status_code and timestamp
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    path = request.url.path

    # Only intercept and log JSON lines for RAG system endpoints
    is_target = any(
        target in path for target in ["/documents/upload", "/search", "/chat"]
    )
    if not is_target:
        return await call_next(request)

    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()

    # Identify user if access token is present in header
    user_id = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        payload = decode_token(token)
        user_id = payload.get("sub")

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as e:
        status_code = 500
        raise e
    finally:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        structlog_logger.info(
            "request_logged",
            request_id=request_id,
            endpoint=path,
            user_id=user_id if user_id else "anonymous",
            latency_ms=latency_ms,
            status_code=status_code,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


@app.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    # Update active documents count dynamically from SQL db on every scrape
    update_active_documents_gauge(db)
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get(f"{settings.API_V1_STR}/eval-metrics")
def get_eval_metrics():
    # Read the newest JSON result from eval_results folder and update Prometheus gauges
    eval_dir = os.environ.get("EVAL_RESULTS_DIR", "/app/eval_results")
    if not os.path.exists(eval_dir):
        # Fallback for local dev outside Docker
        eval_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "eval_results"
        )
    if os.path.exists(eval_dir):
        files = glob.glob(os.path.join(eval_dir, "*.json"))
        if files:
            latest_file = max(files, key=os.path.getmtime)
            try:
                with open(latest_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    scores = data.get("summary_scores", {})

                    f_val = scores.get("faithfulness")
                    if f_val is not None:
                        ragas_faithfulness.set(f_val)

                    ar_val = scores.get("answer_relevancy")
                    if ar_val is not None:
                        ragas_answer_relevancy.set(ar_val)

                    cp_val = scores.get("context_precision")
                    if cp_val is not None:
                        ragas_context_precision.set(cp_val)

                    cr_val = scores.get("context_recall")
                    if cr_val is not None:
                        ragas_context_recall.set(cr_val)
            except Exception:
                pass

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(documents.router, prefix=settings.API_V1_STR)
app.include_router(search.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR)


@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}


@app.get(f"{settings.API_V1_STR}/health")
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "qdrant_host": settings.QDRANT_HOST,
    }
