import os
import io
import traceback

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Header
from pydantic import BaseModel
import pandas as pd

from app.core.drift_engine import DriftAnalyzer
from app.core.database import DatabaseEngine
from app.core.registry import ModelRegistry
from app.core.schemas import validate_dataframe

# ---------------------------------------------------------------------------
# Dependency providers
#
# db/registry are still process-wide singletons (that's correct - you want one
# shared DB connection and one registry per running app instance), but they're
# now provided via FastAPI's Depends() instead of being read as bare module
# globals. This gets you two things:
#   1. Tests can swap them out per-test with app.dependency_overrides instead
#      of monkeypatching module attributes.
#   2. If you ever need per-request state (e.g. a request-scoped DB session),
#      the seam is already there.
# ---------------------------------------------------------------------------
_db_singleton = DatabaseEngine()
_registry_singleton = ModelRegistry(_db_singleton)


def get_db() -> DatabaseEngine:
    return _db_singleton


def get_registry() -> ModelRegistry:
    return _registry_singleton


# ---------------------------------------------------------------------------
# Auth
#
# Simple API-key check via a header, not a full auth system - this stops the
# API from being wide open to anyone who finds the URL, which is the actual
# bar to clear here. Set API_KEY in your environment (.env / docker-compose
# env, etc). If API_KEY isn't set at all, the app refuses to authenticate
# requests rather than silently running with no protection - a deliberate
# fail-closed choice, not an oversight.
# ---------------------------------------------------------------------------
def verify_api_key(x_api_key: str = Header(default=None)):
    expected = os.environ.get("API_KEY")
    if not expected:
        raise HTTPException(
            status_code=500,
            detail="Server misconfigured: API_KEY environment variable is not set."
        )
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
    return True


router = APIRouter(dependencies=[Depends(verify_api_key)])


class SQLRequest(BaseModel):
    query: str


@router.post("/analyze")
async def analyze_drift(
    reference_file: UploadFile = File(...),
    current_file: UploadFile = File(...),
    db: DatabaseEngine = Depends(get_db),
    registry: ModelRegistry = Depends(get_registry),
):
    try:
        print(f"Processing: {reference_file.filename} vs {current_file.filename}")
        ref_content = await reference_file.read()
        curr_content = await current_file.read()

        ref_df = pd.read_csv(io.BytesIO(ref_content))
        curr_df = pd.read_csv(io.BytesIO(curr_content))

        is_valid, errors = validate_dataframe(curr_df)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail={"message": "Data Contract Violation", "errors": errors[:5]}
            )

        db.upload_dataset("reference_table", ref_df)
        db.upload_dataset("current_table", curr_df)

        engine = DriftAnalyzer(db_engine=db, registry=registry)
        results = engine.run_analysis(ref_df, curr_df)

        return {"status": "success", "data": results}

    except HTTPException as he:
        raise he
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sql")
async def run_sql(request: SQLRequest, db: DatabaseEngine = Depends(get_db)):
    result = db.execute_sql(request.query)
    return {"status": "success", "data": result}


@router.get("/sql/presets")
async def get_sql_presets():
    return {
        "status": "success",
        "data": [
            {
                "name": "Revenue Risk by Occupation",
                "query": "SELECT occupation, count(*) as vol FROM current_table WHERE class = '>50K' GROUP BY occupation ORDER BY vol DESC LIMIT 5",
                "desc": "Identify which job roles are most affected by model drift."
            },
            {
                "name": "Drift Over Time",
                "query": "SELECT date(timestamp), risk_score FROM run_history GROUP BY date(timestamp) ORDER BY date(timestamp)",
                "desc": "Time-series view of model health."
            }
        ]
    }


@router.get("/history")
async def get_history(db: DatabaseEngine = Depends(get_db)):
    return {"status": "success", "data": db.get_history()}


@router.get("/models")
async def get_model_history(registry: ModelRegistry = Depends(get_registry)):
    return {"status": "success", "data": registry.get_model_history()}


@router.post("/analyze/llm")
async def analyze_llm():
    return {"status": "success", "data": {"message": "Placeholder"}}