from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy.orm import Session

from app.models.document import Document

# Custom Prometheus metrics definitions for FinSight RAG observability

retrieval_latency_seconds = Histogram(
    "retrieval_latency_seconds",
    "Time spent in hybrid search retrieval (RRF dense + sparse) in seconds",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, float("inf")),
)

llm_generation_latency_seconds = Histogram(
    "llm_generation_latency_seconds",
    "Time spent in local/remote LLM answer generation in seconds",
    buckets=(0.1, 0.5, 1.0, 2.0, 4.0, 8.0, 15.0, 30.0, float("inf")),
)

cache_hits_total = Counter("cache_hits_total", "Total count of Redis search cache hits")

cache_misses_total = Counter(
    "cache_misses_total", "Total count of Redis search cache misses"
)

active_documents_total = Gauge(
    "active_documents_total",
    "Total count of successfully completed (indexed) financial documents",
)


def update_active_documents_gauge(db: Session) -> None:
    """
    Query the database to count all completed documents and update
    the active_documents_total Gauge metric.
    """
    try:
        count = db.query(Document).filter(Document.upload_status == "completed").count()
        active_documents_total.set(count)
    except Exception:
        # Silently catch to prevent app startup issues during migrations or test setup
        pass
