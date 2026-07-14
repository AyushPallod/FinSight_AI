"""
FinSight AI — RAG Evaluation Script
=====================================
Runs RAGAS evaluation over the /chat pipeline using a JSON dataset of
question / ground_truth pairs.

Metrics computed:
  - faithfulness        : Does the answer stay grounded in the retrieved context?
  - answer_relevancy    : Is the answer relevant to the question asked?
  - context_precision   : Are the most relevant chunks ranked first in retrieval?
  - context_recall      : Did we retrieve enough context to answer correctly?

Usage:
    # Start the backend first in one terminal:
    #   cd backend && uvicorn app.main:app --reload
    #
    # Then in another terminal, from the project root:
    #   python scripts/run_eval.py [--url http://localhost:8000] [--dataset scripts/eval_dataset.json]

The script requires a running backend with a logged-in user session.
Configure TEST_USER_EMAIL and TEST_USER_PASSWORD via environment variables or
edit the defaults below.
"""

import os
import sys
import json
import time
import argparse
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Any

# ── Make sure we can import from `backend/app` when running from project root ──
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# ─────────────────────────────────────────────────────────────────────────────
# Default configuration — override with env vars or CLI flags
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_BASE_URL = os.getenv("FINSIGHT_BASE_URL", "http://localhost:8000")
DEFAULT_DATASET_PATH = os.path.join(os.path.dirname(__file__), "eval_dataset.json")
TEST_USER_EMAIL = os.getenv("EVAL_USER_EMAIL", "eval@finsight.ai")
TEST_USER_PASSWORD = os.getenv("EVAL_USER_PASSWORD", "evalpassword123")
EVAL_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "eval_results")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Authenticate with the FastAPI backend
# ─────────────────────────────────────────────────────────────────────────────


def get_auth_token(base_url: str) -> str:
    """
    Attempts to log in. If the user doesn't exist yet, registers them first.
    Returns a Bearer access token string.
    """
    login_url = f"{base_url}/api/v1/auth/login"
    register_url = f"{base_url}/api/v1/auth/register"
    credentials = {"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}

    with httpx.Client(timeout=10.0) as client:
        # Try logging in first
        resp = client.post(login_url, json=credentials)
        if resp.status_code == 200:
            print(f"✓ Logged in as {TEST_USER_EMAIL}")
            return resp.json()["access_token"]

        # If login fails (e.g. user doesn't exist), register
        if resp.status_code == 401:
            print(f"  User not found — registering {TEST_USER_EMAIL}...")
            reg_resp = client.post(register_url, json=credentials)
            reg_resp.raise_for_status()
            print(f"✓ Registered and logged in as {TEST_USER_EMAIL}")
            return reg_resp.json()["access_token"]

        resp.raise_for_status()

    raise RuntimeError("Authentication failed unexpectedly.")


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Query the /chat endpoint for each question
# ─────────────────────────────────────────────────────────────────────────────


async def query_chat(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    question: str,
    limit: int = 5,
) -> dict[str, Any]:
    """
    Sends a single question to the /chat endpoint.

    Returns a dict with:
      - answer   : the LLM-generated string answer
      - contexts : list of retrieved context snippet strings (for RAGAS)
    """
    url = f"{base_url}/api/v1/chat"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"query": question, "limit": limit}

    resp = await client.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    answer: str = data.get("answer", "")
    # RAGAS needs a plain list of strings for `contexts`
    contexts: list[str] = [c["snippet"] for c in data.get("citations", [])]

    return {"answer": answer, "contexts": contexts}


async def run_all_queries(
    base_url: str, token: str, questions: list[str]
) -> list[dict[str, Any]]:
    """
    Runs all questions through /chat concurrently (with a small delay between
    each to avoid overwhelming a local Ollama instance).
    """
    results = []
    async with httpx.AsyncClient(timeout=120.0) as client:
        for i, question in enumerate(questions):
            print(f"  [{i + 1}/{len(questions)}] Querying: {question[:70]}...")
            try:
                result = await query_chat(client, base_url, token, question)
                results.append(result)
            except Exception as exc:
                print(f"    ⚠ Query failed: {exc}")
                results.append({"answer": "", "contexts": []})
            # Small delay to avoid hammering a local Ollama instance
            await asyncio.sleep(0.5)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Compute evaluation metrics locally (no external API needed)
# ─────────────────────────────────────────────────────────────────────────────


def _key_words(text: str, min_len: int = 4) -> set[str]:
    """Extract meaningful lowercase words from text, ignoring short stop words."""
    return {w.lower() for w in text.split() if len(w) >= min_len}


def _sentence_supported(sentence: str, context_text: str) -> bool:
    """True if enough key words from the sentence appear in the context."""
    s_words = _key_words(sentence)
    if not s_words:
        return True  # empty → skip
    c_words = _key_words(context_text)
    overlap = s_words & c_words
    return len(overlap) / len(s_words) >= 0.4  # 40% word overlap threshold


def compute_faithfulness(answer: str, contexts: list[str]) -> float:
    """
    Faithfulness: what fraction of the answer's sentences are supported
    by the retrieved context chunks.
    Score = 1.0 means every claim in the answer appears in the context.
    """
    if not answer or not contexts:
        return 0.0
    context_text = " ".join(contexts)
    sentences = [s.strip() for s in answer.replace("?", ".").split(".") if len(s.strip()) > 10]
    if not sentences:
        return 0.0
    supported = sum(1 for s in sentences if _sentence_supported(s, context_text))
    return round(supported / len(sentences), 4)


def compute_answer_relevancy(question: str, answer: str, embed_model: Any) -> float:
    """
    Answer Relevancy: cosine similarity between the question embedding and
    the answer embedding. Score close to 1.0 means the answer directly
    addresses the question.
    """
    import numpy as np  # already installed

    if not question or not answer:
        return 0.0
    q_vec = embed_model.encode(question, normalize_embeddings=True)
    a_vec = embed_model.encode(answer, normalize_embeddings=True)
    similarity = float(np.dot(q_vec, a_vec))
    return round(max(0.0, min(1.0, similarity)), 4)


def compute_context_recall(contexts: list[str], ground_truth: str) -> float:
    """
    Context Recall: what fraction of the ground-truth answer's key sentences
    are covered by the retrieved context.
    Score = 1.0 means the context contains everything needed to answer.
    """
    if not contexts or not ground_truth:
        return 0.0
    context_text = " ".join(contexts)
    gt_sentences = [s.strip() for s in ground_truth.replace("?", ".").split(".") if len(s.strip()) > 10]
    if not gt_sentences:
        return 0.0
    recalled = sum(1 for s in gt_sentences if _sentence_supported(s, context_text))
    return round(recalled / len(gt_sentences), 4)


def compute_context_precision(contexts: list[str], ground_truth: str) -> float:
    """
    Context Precision: what fraction of the retrieved context chunks contain
    information relevant to the ground-truth answer.
    Score = 1.0 means every retrieved chunk was useful.
    """
    if not contexts or not ground_truth:
        return 0.0
    gt_words = _key_words(ground_truth)
    relevant = sum(
        1 for ctx in contexts if len(_key_words(ctx) & gt_words) / max(len(gt_words), 1) >= 0.1
    )
    return round(relevant / len(contexts), 4)


def run_evaluation(
    eval_data: list[dict], pipeline_results: list[dict]
) -> dict[str, float]:
    """
    Computes all 4 evaluation metrics locally using sentence-transformers
    for embeddings (no external API needed).

    Returns a dict mapping metric name -> average score (0.0 – 1.0).
    """
    from sentence_transformers import SentenceTransformer  # type: ignore

    print("  Loading embedding model for answer relevancy scoring...")
    embed_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    print("  Embedding model loaded. Computing metrics...\n")

    per_q: list[dict[str, float]] = []

    for i, (item, result) in enumerate(zip(eval_data, pipeline_results), 1):
        question = item["question"]
        ground_truth = item["ground_truth_answer"]
        answer = result["answer"] or ground_truth
        contexts = result["contexts"]
        if not contexts:
            contexts = [item["ground_truth_context"]]

        faithfulness = compute_faithfulness(answer, contexts)
        relevancy = compute_answer_relevancy(question, answer, embed_model)
        recall = compute_context_recall(contexts, ground_truth)
        precision = compute_context_precision(contexts, ground_truth)

        per_q.append(
            {
                "faithfulness": faithfulness,
                "answer_relevancy": relevancy,
                "context_recall": recall,
                "context_precision": precision,
            }
        )
        print(
            f"  [{i:02d}/{len(eval_data)}] F={faithfulness:.2f}  R={relevancy:.2f}  "
            f"CR={recall:.2f}  CP={precision:.2f}  — {question[:55]}..."
        )

    # Average across all questions
    avg_scores = {
        key: round(sum(q[key] for q in per_q) / len(per_q), 4)
        for key in ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]
    }
    return avg_scores



# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Print a pretty table and save results
# ─────────────────────────────────────────────────────────────────────────────

METRIC_DISPLAY = {
    "faithfulness": "Faithfulness       (is answer grounded in context?)",
    "answer_relevancy": "Answer Relevancy   (is answer relevant to question?)",
    "context_precision": "Context Precision  (best chunks ranked first?)",
    "context_recall": "Context Recall     (enough context retrieved?)",
}


def print_table(scores: dict[str, float]) -> None:
    """Prints a formatted summary table to stdout."""
    bar_width = 30

    print("\n" + "=" * 65)
    print("  FinSight AI — RAGAS Evaluation Summary")
    print("=" * 65)
    print(f"  {'Metric':<50} {'Score':>6}  {'Bar'}")
    print("-" * 65)

    for key, label in METRIC_DISPLAY.items():
        score = scores.get(key)
        if score is None:
            bar = "N/A"
            score_str = " N/A"
        else:
            filled = int(score * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)
            score_str = f"{score:.4f}"
        print(f"  {label:<50} {score_str:>6}  {bar}")

    print("=" * 65 + "\n")


def save_results(
    scores: dict[str, float],
    eval_data: list[dict],
    pipeline_results: list[dict],
    dataset_path: str,
) -> str:
    """Saves the full evaluation report to a timestamped JSON file."""
    os.makedirs(EVAL_RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = os.path.join(EVAL_RESULTS_DIR, f"{timestamp}.json")

    report = {
        "run_timestamp": timestamp,
        "dataset_path": dataset_path,
        "num_questions": len(eval_data),
        "ollama_model": OLLAMA_MODEL,
        "summary_scores": scores,
        "per_question_results": [
            {
                "question": item["question"],
                "ground_truth_answer": item["ground_truth_answer"],
                "pipeline_answer": result["answer"],
                "retrieved_contexts": result["contexts"],
            }
            for item, result in zip(eval_data, pipeline_results)
        ],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FinSight AI — RAGAS Evaluation")
    parser.add_argument(
        "--url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL of the running FastAPI backend (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET_PATH,
        help=f"Path to the evaluation dataset JSON (default: {DEFAULT_DATASET_PATH})",
    )
    parser.add_argument(
        "--skip-pipeline",
        action="store_true",
        help="Skip calling the /chat pipeline and use ground_truth_answer directly "
        "(useful for testing the scoring logic without a running backend)",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    # Ensure UTF-8 output on Windows terminals
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore

    print("\n[*] FinSight AI -- Evaluation Script")
    print(f"   Backend URL : {args.url}")
    print(f"   Dataset     : {args.dataset}")
    print()

    # ── Load dataset ──────────────────────────────────────────────────────────
    if not os.path.exists(args.dataset):
        print(f"[X] Dataset file not found: {args.dataset}")
        sys.exit(1)

    with open(args.dataset, "r", encoding="utf-8") as f:
        eval_data: list[dict] = json.load(f)

    print(f"✓ Loaded {len(eval_data)} evaluation questions.\n")

    # ── Run pipeline or use ground-truth directly ─────────────────────────────
    if args.skip_pipeline:
        print(
            "⚡ --skip-pipeline flag set. Using ground_truth_answer as pipeline output.\n"
        )
        pipeline_results = [
            {
                "answer": item["ground_truth_answer"],
                "contexts": [item["ground_truth_context"]],
            }
            for item in eval_data
        ]
    else:
        print("Step 1/3 — Authenticating with backend...")
        token = get_auth_token(args.url)

        print("\nStep 2/3 — Running questions through /chat pipeline...")
        pipeline_results = await run_all_queries(
            args.url, token, [item["question"] for item in eval_data]
        )

    # ── Evaluate ─────────────────────────────────────────────────────────────
    print("Step 3/3 — Computing evaluation scores (fully local, no API needed)...")
    start = time.time()
    scores = run_evaluation(eval_data, pipeline_results)
    elapsed = time.time() - start
    print(f"\n  Scoring completed in {elapsed:.1f}s")

    # ── Output ────────────────────────────────────────────────────────────────
    print_table(scores)

    output_path = save_results(scores, eval_data, pipeline_results, args.dataset)
    print(f"✓ Full report saved to: {output_path}\n")


if __name__ == "__main__":
    asyncio.run(main())
