import io
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app
from app.services.ingestion import ingestion_service
from app.services.llm import llm_service

client = TestClient(app)


def test_upload_and_chat_flow():
    # 1. Register a test user
    user_payload = {"email": "testuser@example.com", "password": "testpassword123"}
    register_response = client.post("/api/v1/auth/register", json=user_payload)
    assert register_response.status_code == 201
    auth_data = register_response.json()
    access_token = auth_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Login to verify authentication works
    login_response = client.post("/api/v1/auth/login", json=user_payload)
    assert login_response.status_code == 200

    # 3. Setup mock document ingestion content
    # We mock extract_text to return structured text for our dummy file
    mock_extracted_pages = [
        {
            "page_number": 1,
            "text": "This is page 1 of the Q4 financial report. Net income increased by 15% to $45 million.",
        }
    ]

    # Create a dummy PDF file in memory
    dummy_pdf_content = b"%PDF-1.4 dummy content"
    file_payload = {
        "file": ("sample.pdf", io.BytesIO(dummy_pdf_content), "application/pdf")
    }

    # Use patch to mock the text extraction from the PDF
    with patch.object(
        ingestion_service, "extract_text", return_value=mock_extracted_pages
    ):
        upload_response = client.post(
            "/api/v1/documents/upload", files=file_payload, headers=headers
        )

    assert upload_response.status_code == 202
    upload_data = upload_response.json()
    doc_id = upload_data["id"]
    assert upload_data["filename"] == "sample.pdf"
    assert upload_data["upload_status"] == "pending"

    # 4. Check the document status via status endpoint
    status_response = client.get(f"/api/v1/documents/{doc_id}/status", headers=headers)
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["upload_status"] == "completed"

    # 5. Mock Ollama LLM call to return a cited answer
    mock_answer = (
        "Net income increased by 15% to $45 million. [Source: sample.pdf, Page 1]"
    )

    # Send a query to the chat endpoint
    chat_payload = {"query": "By how much did net income increase?", "limit": 4}

    with patch.object(
        llm_service, "generate_answer", new_callable=AsyncMock
    ) as mock_generate:
        mock_generate.return_value = mock_answer

        chat_response = client.post("/api/v1/chat", json=chat_payload, headers=headers)

    assert chat_response.status_code == 200
    chat_data = chat_response.json()
    assert "45 million" in chat_data["answer"]
    assert len(chat_data["citations"]) > 0
    assert chat_data["citations"][0]["document"] == "sample.pdf"
    assert chat_data["citations"][0]["page"] == 1
    assert "Net income" in chat_data["citations"][0]["snippet"]
