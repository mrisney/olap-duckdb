import pytest
from fastapi.testclient import TestClient
from main import app  # Import your FastAPI app from main.py

client = TestClient(app)

def test_get_records():
    response = client.get("/records/")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "page" in data
    assert "size" in data
    assert "total_pages" in data
    assert "total_records" in data

if __name__ == "__main__":
    pytest.main()

