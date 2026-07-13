import pytest
from app.services.chunking import chunking_service
from app.services.retrieval import retrieval_service, tokenize
from unittest.mock import patch

# ==========================================
# 1. Chunker Unit Tests
# ==========================================


def test_split_into_sentences():
    # Test standard sentence splitting
    text = "Hello world. This is the second sentence! Is this the third? Yes it is."
    sentences = chunking_service.split_into_sentences(text)
    assert len(sentences) == 4
    assert sentences[0] == "Hello world."
    assert sentences[1] == "This is the second sentence!"
    assert sentences[2] == "Is this the third?"
    assert sentences[3] == "Yes it is."

    # Test abbreviation handling (should not split on known abbreviations)
    text_with_abbrev = "Dr. Smith went to the corp. office. This is e.g. a test."
    sentences_abbrev = chunking_service.split_into_sentences(text_with_abbrev)
    assert len(sentences_abbrev) == 2
    assert sentences_abbrev[0] == "Dr. Smith went to the corp. office."
    assert sentences_abbrev[1] == "This is e.g. a test."

    # Test single-letter initial handling (should not split)
    text_with_initials = "J. P. Morgan released a statement. It was positive."
    sentences_initials = chunking_service.split_into_sentences(text_with_initials)
    assert len(sentences_initials) == 2
    assert sentences_initials[0] == "J. P. Morgan released a statement."
    assert sentences_initials[1] == "It was positive."


def test_chunk_document():
    # Setup dummy document with multiple pages
    pages = [
        {
            "page_number": 1,
            "text": "This is page one sentence one. This is page one sentence two. Page one sentence three.",
        },
        {
            "page_number": 2,
            "text": "This is page two sentence one. This is page two sentence two.",
        },
    ]

    # Run semantic chunking with a target word count of 10 and overlap of 1 sentence
    chunks = chunking_service.chunk_document(
        pages=pages,
        document_id="doc-123",
        source_filename="test_file.pdf",
        target_words=10,
        overlap_sentences=1,
    )

    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk["document_id"] == "doc-123"
        assert chunk["source_filename"] == "test_file.pdf"
        assert "text" in chunk
        assert "page_number" in chunk
        assert "chunk_index" in chunk

    # Verify the chunking boundary outputs
    assert chunks[0]["page_number"] == 1
    assert "page one sentence one" in chunks[0]["text"].lower()

    assert chunks[1]["page_number"] == 1
    assert "page one sentence two" in chunks[1]["text"].lower()
    assert "page one sentence three" in chunks[1]["text"].lower()


def test_chunk_document_with_overlap():
    pages = [
        {
            "page_number": 1,
            "text": "One. Two. Three four five six seven eight nine ten.",
        }
    ]
    chunks = chunking_service.chunk_document(
        pages=pages,
        document_id="doc-123",
        source_filename="test_file.pdf",
        target_words=5,
        overlap_sentences=1,
    )
    assert len(chunks) == 2
    # First chunk should have "One. Two."
    assert chunks[0]["text"] == "One. Two."
    # Second chunk should carry over "Two." and have "Two. Three four five six seven eight nine ten."
    assert chunks[1]["text"] == "Two. Three four five six seven eight nine ten."


# ==========================================
# 2. RRF Fusion Unit Tests
# ==========================================


class MockQdrantPoint:
    def __init__(self, point_id, payload):
        self.id = point_id
        self.payload = payload


def test_rrf_fusion_logic():
    # Setup mock search outputs
    # Dense results: ID 1 is rank 1, ID 2 is rank 2
    dense_results = [
        MockQdrantPoint(
            point_id="doc_id_1",
            payload={
                "text": "text 1",
                "page_number": 1,
                "chunk_index": 0,
                "document_id": "doc1",
                "source_filename": "file1.pdf",
            },
        ),
        MockQdrantPoint(
            point_id="doc_id_2",
            payload={
                "text": "text 2",
                "page_number": 2,
                "chunk_index": 1,
                "document_id": "doc1",
                "source_filename": "file1.pdf",
            },
        ),
    ]

    # Sparse results: ID 2 is rank 1, ID 3 is rank 2
    sparse_results = [
        MockQdrantPoint(
            point_id="doc_id_2",
            payload={
                "text": "text 2",
                "page_number": 2,
                "chunk_index": 1,
                "document_id": "doc1",
                "source_filename": "file1.pdf",
            },
        ),
        MockQdrantPoint(
            point_id="doc_id_3",
            payload={
                "text": "text 3",
                "page_number": 3,
                "chunk_index": 2,
                "document_id": "doc1",
                "source_filename": "file1.pdf",
            },
        ),
    ]

    # RRF Math with k = 60:
    # doc_id_1 (dense rank 1): 1 / (60 + 1) = 0.016393
    # doc_id_2 (dense rank 2, sparse rank 1): 1 / (60 + 2) + 1 / (60 + 1) = 0.016129 + 0.016393 = 0.032522
    # doc_id_3 (sparse rank 2): 1 / (60 + 2) = 0.016129

    # Mock dense_search and sparse_search on retrieval_service
    with patch.object(
        retrieval_service, "dense_search", return_value=dense_results
    ), patch.object(retrieval_service, "sparse_search", return_value=sparse_results):

        # Run hybrid_search
        fused = retrieval_service.hybrid_search(query="test query", limit=3, rrf_k=60)

        assert len(fused) == 3
        # Rank 1 should be doc_id_2
        assert fused[0]["id"] == "doc_id_2"
        assert fused[0]["rrf_score"] == pytest.approx(0.032522, abs=1e-5)

        # Rank 2 should be doc_id_1
        assert fused[1]["id"] == "doc_id_1"
        assert fused[1]["rrf_score"] == pytest.approx(0.016393, abs=1e-5)

        # Rank 3 should be doc_id_3
        assert fused[2]["id"] == "doc_id_3"
        assert fused[2]["rrf_score"] == pytest.approx(0.016129, abs=1e-5)


def test_tokenizer():
    text = "R.U.F.F. & Black checks 10-K filings!"
    tokens = tokenize(text)
    assert "filings" in tokens
    assert "black" in tokens
    assert "checks" in tokens
