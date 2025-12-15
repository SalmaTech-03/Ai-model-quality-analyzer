from fastapi.testclient import TestClient
# This import will now work thanks to pytest.ini
from app.main import app 

client = TestClient(app)

def test_app_starts():
    """
    Smoke Test:
    Verifies the app initializes without crashing.
    """
    response = client.get("/")
    # If the app starts, it returns 200. If it crashes, it's 500.
    assert response.status_code == 200
