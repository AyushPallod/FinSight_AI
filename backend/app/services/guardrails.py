"""
FinSight AI — Guardrails Module
================================
Two independent safety layers:

1. PromptInjectionDetector
   Scans user queries for known prompt-injection patterns (e.g. "ignore
   previous instructions") and raises an HTTPException(400) if detected.
   Applied as a guard at the top of the /chat endpoint.

2. PIIScrubber
   Regex-based scrubber that redacts PII from text before it is embedded
   and stored in the vector database. Handles:
     - Email addresses             → [REDACTED_EMAIL]
     - Phone numbers (Indian + international formats) → [REDACTED_PHONE]
     - Indian PAN card numbers     → [REDACTED_PAN]
     - Indian Aadhaar numbers      → [REDACTED_AADHAAR]
   Applied inside the Celery ingestion task after chunking and before indexing.
"""

import logging
import re
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Prompt Injection Detector
# ─────────────────────────────────────────────────────────────────────────────

# Each pattern is a compiled regex that matches a family of injection attempts.
# We use IGNORECASE so capitalisation tricks don't bypass the check.
_INJECTION_PATTERNS: list[re.Pattern] = [
    # Classic "forget / ignore" instructions
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(the\s+)?(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"forget\s+(all\s+)?previous\s+(instructions?|context)", re.IGNORECASE),
    # Role-switching attempts (allow legitimate financial/analyst role requests)
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(
        # Matches "act as X" but NOT when X is a financial/assistant role.
        # The lookahead must account for an optional article (a/an) before the role.
        r"act\s+as\s+(?!(?:a\s+|an\s+)?(?:financial|analyst|assistant|advisor|expert|tutor))",
        re.IGNORECASE,
    ),
    re.compile(r"pretend\s+(?:you\s+are|to\s+be)\s+", re.IGNORECASE),
    re.compile(r"roleplay\s+as\s+", re.IGNORECASE),
    re.compile(r"switch\s+(?:to\s+)?(?:developer|jailbreak|unrestricted)\s+mode", re.IGNORECASE),
    # "DAN" and classic jailbreak keywords
    re.compile(r"\bdo\s+anything\s+now\b", re.IGNORECASE),
    re.compile(r"\bdan\s+mode\b", re.IGNORECASE),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    # Instruction overwrite attempts
    re.compile(r"new\s+(system\s+)?instructions?:", re.IGNORECASE),
    re.compile(r"override\s+(the\s+)?(system\s+)?(prompt|instructions?)", re.IGNORECASE),
    re.compile(r"your\s+(real|true|actual)\s+instructions?\s+are", re.IGNORECASE),
    # Prompt delimiter injection
    re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE),
    re.compile(r"\[INST\]|\[/INST\]", re.IGNORECASE),
    re.compile(r"###\s*instruction", re.IGNORECASE),
]

_INJECTION_ERROR_MSG = (
    "Your query contains patterns associated with prompt injection attacks "
    "and cannot be processed. Please rephrase your financial question."
)


def detect_prompt_injection(query: str) -> None:
    """
    Check a user query for prompt injection patterns.

    Raises:
        HTTPException(400): if any injection pattern is matched.
    """
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(query):
            logger.warning(
                f"Prompt injection detected. Pattern: '{pattern.pattern}' | "
                f"Query preview: '{query[:80]}'"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_INJECTION_ERROR_MSG,
            )


# ─────────────────────────────────────────────────────────────────────────────
# 2.  PII Scrubber
# ─────────────────────────────────────────────────────────────────────────────

# Each entry is (compiled_regex, replacement_string).
# Order matters: more specific patterns should come before generic ones.
_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    # --- Email addresses ---
    # Matches: user@domain.com, user.name+tag@sub.domain.co.in
    (
        re.compile(
            r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
            re.IGNORECASE,
        ),
        "[REDACTED_EMAIL]",
    ),
    # --- Indian Aadhaar numbers ---
    # 12-digit number, optionally separated by spaces or hyphens in groups of 4
    # e.g.  1234 5678 9012  or  1234-5678-9012  or  123456789012
    (
        re.compile(
            r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",
        ),
        "[REDACTED_AADHAAR]",
    ),
    # --- Indian PAN card numbers ---
    # Format: 5 uppercase letters + 4 digits + 1 uppercase letter
    # e.g.  ABCDE1234F
    (
        re.compile(
            r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
        ),
        "[REDACTED_PAN]",
    ),
    # --- Phone numbers (Indian + international) ---
    # Covers:
    #   +91-9876543210  +91 98765 43210  0091-9876543210
    #   +1-800-555-0100  +44 20 7946 0958
    #   Plain 10-digit Indian mobile: 9876543210
    (
        re.compile(
            r"""
            (?:
                (?:\+|00)      # international prefix  +  or  00
                \d{1,3}        # country code (1-3 digits)
                [\s\-]?        # optional separator
            )?
            (?:\(?\d{2,4}\)?[\s\-]?)?   # optional area code with optional parens
            \d{3,5}            # first digit block
            [\s\-]?
            \d{3,5}            # second digit block
            (?:[\s\-]?\d{2,4})?  # optional trailing block
            \b
            """,
            re.VERBOSE,
        ),
        "[REDACTED_PHONE]",
    ),
]


def scrub_pii(text: str) -> str:
    """
    Scan ``text`` for PII patterns and replace each match with a labelled
    placeholder.  Returns the scrubbed string.

    Patterns applied (in order):
      1. Email addresses
      2. Aadhaar numbers
      3. PAN numbers
      4. Phone numbers
    """
    for pattern, replacement in _PII_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            logger.info(
                f"PII scrubber: redacting {len(matches)} occurrence(s) "
                f"of type '{replacement}'"
            )
        text = pattern.sub(replacement, text)
    return text


def scrub_chunks(chunks: list[dict]) -> list[dict]:
    """
    Apply PII scrubbing to the ``text`` field of each chunk dict in-place.
    Returns the same list (mutated) for convenience.

    This is the function called from the Celery ingestion task.
    """
    for chunk in chunks:
        original = chunk.get("text", "")
        scrubbed = scrub_pii(original)
        if scrubbed != original:
            logger.info(
                f"PII found and redacted in chunk {chunk.get('chunk_index')} "
                f"of document '{chunk.get('source_filename')}'"
            )
        chunk["text"] = scrubbed
    return chunks
