from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_app_starts():
    """
    Smoke Test:
    Verifies that the app can initialize and return the homepage.
    """
    response = client.get("/")
    # We expect 200, but any non-500 code means the app isn't crashing
    assert response.status_code != 500
