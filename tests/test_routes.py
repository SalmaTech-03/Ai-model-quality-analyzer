"""
Tests for app/api/routes.py

Now that routes.py uses Depends() for db/registry and a router-level API-key
check, these tests use FastAPI's app.dependency_overrides mechanism instead
of monkeypatching module attributes - the correct pattern for DI-based code.

Run with: pytest tests/test_routes.py -v
"""
import io
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.routes as routes_module


class FakeDB:
    def __init__(self):
        self.uploaded = {}
        self.sql_calls = []

    def check_cooldown(self):
        return (False, None)

    def get_current_version(self):
        return "v1.0.0-test"

    def upload_dataset(self, name, df):
        self.uploaded[name] = df

    def execute_sql(self, query):
        self.sql_calls.append(query)
        return [{"col": "value"}]

    def get_history(self):
        return [{"run": 1, "drift_share": 0.1}]

    def log_run(self, *a, **k):
        pass


class FakeRegistry:
    def get_model_history(self):
        return [{"version": "v1.0.0", "active": True}]

    def execute_rollback(self, reason=None):
        return {"rolled_back_to": "v0.9.0", "reason": reason}


@pytest.fixture
def client(monkeypatch):
    fake_db = FakeDB()
    fake_registry = FakeRegistry()

    app = FastAPI()
    app.include_router(routes_module.router, prefix="/api")

    # Correct DI pattern: override the provider functions, not module globals.
    app.dependency_overrides[routes_module.get_db] = lambda: fake_db
    app.dependency_overrides[routes_module.get_registry] = lambda: fake_registry
    # Auth is real business logic (item 3), so most tests bypass it here to stay
    # focused on route behavior - the dedicated TestAuth class below tests the
    # real, non-overridden verify_api_key dependency instead.
    app.dependency_overrides[routes_module.verify_api_key] = lambda: True

    monkeypatch.setattr(routes_module, "validate_dataframe", lambda df: (True, []))

    test_client = TestClient(app)
    test_client.fake_db = fake_db
    test_client.fake_registry = fake_registry
    return test_client


def _csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


class TestAuth:
    """
    These tests do NOT use the `client` fixture above (which overrides auth) -
    they exercise the real verify_api_key dependency against a real environment
    variable, since auth correctness matters enough to test for real.
    """

    def _real_client(self, monkeypatch, api_key_env=None):
        if api_key_env is None:
            monkeypatch.delenv("API_KEY", raising=False)
        else:
            monkeypatch.setenv("API_KEY", api_key_env)

        app = FastAPI()
        app.include_router(routes_module.router, prefix="/api")
        app.dependency_overrides[routes_module.get_db] = lambda: FakeDB()
        app.dependency_overrides[routes_module.get_registry] = lambda: FakeRegistry()
        return TestClient(app)

    def test_missing_api_key_header_is_rejected(self, monkeypatch):
        client = self._real_client(monkeypatch, api_key_env="secret123")
        resp = client.get("/api/history")
        assert resp.status_code == 401

    def test_wrong_api_key_is_rejected(self, monkeypatch):
        client = self._real_client(monkeypatch, api_key_env="secret123")
        resp = client.get("/api/history", headers={"x-api-key": "wrong"})
        assert resp.status_code == 401

    def test_correct_api_key_is_accepted(self, monkeypatch):
        client = self._real_client(monkeypatch, api_key_env="secret123")
        resp = client.get("/api/history", headers={"x-api-key": "secret123"})
        assert resp.status_code == 200

    def test_unset_api_key_env_fails_closed_not_open(self, monkeypatch):
        # If the server itself isn't configured with an API_KEY, it must refuse
        # rather than silently letting every request through unauthenticated.
        client = self._real_client(monkeypatch, api_key_env=None)
        resp = client.get("/api/history", headers={"x-api-key": "anything"})
        assert resp.status_code == 500


class TestAnalyzeEndpoint:
    def test_analyze_returns_success_with_valid_csvs(self, client, monkeypatch):
        class StubAnalyzer:
            def __init__(self, db_engine=None, registry=None):
                pass

            def run_analysis(self, ref_df, curr_df):
                return {"automation": {"action": "NO ACTION"}}

        monkeypatch.setattr(routes_module, "DriftAnalyzer", StubAnalyzer)

        ref = pd.DataFrame({"age": [25, 30], "class": [">50K", "<=50K"]})
        curr = pd.DataFrame({"age": [26, 31], "class": [">50K", "<=50K"]})

        resp = client.post(
            "/api/analyze",
            files={
                "reference_file": ("ref.csv", _csv_bytes(ref), "text/csv"),
                "current_file": ("curr.csv", _csv_bytes(curr), "text/csv"),
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["data"]["automation"]["action"] == "NO ACTION"

    def test_analyze_uploads_both_datasets_to_db(self, client, monkeypatch):
        class StubAnalyzer:
            def __init__(self, db_engine=None, registry=None):
                pass

            def run_analysis(self, ref_df, curr_df):
                return {}

        monkeypatch.setattr(routes_module, "DriftAnalyzer", StubAnalyzer)

        ref = pd.DataFrame({"age": [25]})
        curr = pd.DataFrame({"age": [26]})
        client.post(
            "/api/analyze",
            files={
                "reference_file": ("ref.csv", _csv_bytes(ref), "text/csv"),
                "current_file": ("curr.csv", _csv_bytes(curr), "text/csv"),
            },
        )

        assert "reference_table" in client.fake_db.uploaded
        assert "current_table" in client.fake_db.uploaded

    def test_analyze_returns_400_on_data_contract_violation(self, client, monkeypatch):
        monkeypatch.setattr(
            routes_module, "validate_dataframe",
            lambda df: (False, ["missing column: age", "missing column: sex"])
        )

        ref = pd.DataFrame({"x": [1]})
        curr = pd.DataFrame({"x": [1]})
        resp = client.post(
            "/api/analyze",
            files={
                "reference_file": ("ref.csv", _csv_bytes(ref), "text/csv"),
                "current_file": ("curr.csv", _csv_bytes(curr), "text/csv"),
            },
        )

        assert resp.status_code == 400
        assert resp.json()["detail"]["message"] == "Data Contract Violation"

    def test_analyze_returns_500_with_message_on_unexpected_error(self, client, monkeypatch):
        class BoomAnalyzer:
            def __init__(self, db_engine=None, registry=None):
                pass

            def run_analysis(self, ref_df, curr_df):
                raise RuntimeError("simulated failure")

        monkeypatch.setattr(routes_module, "DriftAnalyzer", BoomAnalyzer)

        ref = pd.DataFrame({"age": [25]})
        curr = pd.DataFrame({"age": [26]})
        resp = client.post(
            "/api/analyze",
            files={
                "reference_file": ("ref.csv", _csv_bytes(ref), "text/csv"),
                "current_file": ("curr.csv", _csv_bytes(curr), "text/csv"),
            },
        )

        assert resp.status_code == 500
        assert "simulated failure" in resp.json()["detail"]

    def test_analyze_rejects_missing_files(self, client):
        resp = client.post("/api/analyze", files={})
        assert resp.status_code == 422


class TestSqlEndpoint:
    def test_run_sql_returns_query_result(self, client):
        resp = client.post("/api/sql", json={"query": "SELECT 1"})
        assert resp.status_code == 200
        assert resp.json() == {"status": "success", "data": [{"col": "value"}]}
        assert client.fake_db.sql_calls == ["SELECT 1"]

    def test_run_sql_rejects_missing_query_field(self, client):
        resp = client.post("/api/sql", json={})
        assert resp.status_code == 422

    def test_sql_presets_returns_two_presets(self, client):
        resp = client.get("/api/sql/presets")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2
        assert data[0]["name"] == "Revenue Risk by Occupation"


class TestHistoryEndpoint:
    def test_get_history_returns_db_history(self, client):
        resp = client.get("/api/history")
        assert resp.status_code == 200
        assert resp.json() == {"status": "success", "data": [{"run": 1, "drift_share": 0.1}]}


class TestModelsEndpoint:
    def test_get_models_returns_registry_history(self, client):
        resp = client.get("/api/models")
        assert resp.status_code == 200
        assert resp.json() == {
            "status": "success",
            "data": [{"version": "v1.0.0", "active": True}],
        }


class TestAnalyzeLLMEndpoint:
    def test_placeholder_endpoint_responds(self, client):
        resp = client.post("/api/analyze/llm")
        assert resp.status_code == 200
        assert resp.json()["data"]["message"] == "Placeholder"