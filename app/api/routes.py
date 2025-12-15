from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import pandas as pd
import io
import traceback

from app.core.drift_engine import DriftAnalyzer
from app.core.database import DatabaseEngine
from app.core.schemas import validate_dataframe # Checks Data Contracts

db = DatabaseEngine()
router = APIRouter()

class SQLRequest(BaseModel):
    query: str

@router.post("/analyze")
async def analyze_drift(
    reference_file: UploadFile = File(...),
    current_file: UploadFile = File(...)
):
    try:
        print(f"📥 Processing: {reference_file.filename} vs {current_file.filename}")
        ref_content = await reference_file.read()
        curr_content = await current_file.read()
        
        ref_df = pd.read_csv(io.BytesIO(ref_content))
        curr_df = pd.read_csv(io.BytesIO(curr_content))
        
        # 1. DATA CONTRACT VALIDATION (The Gatekeeper)
        # We validate 'current' data to stop garbage from entering the pipeline
        is_valid, errors = validate_dataframe(curr_df)
        if not is_valid:
            print("❌ Data Contract Violation")
            # 400 Bad Request triggers the frontend alert
            raise HTTPException(
                status_code=400, 
                detail={"message": "Data Contract Violation", "errors": errors[:5]}
            )
        
        # 2. SQL UPLOAD (Analyst Mode)
        db.upload_dataset("reference_table", ref_df)
        db.upload_dataset("current_table", curr_df)
        
        # 3. ANALYSIS
        engine = DriftAnalyzer(db_engine=db)
        results = engine.run_analysis(ref_df, curr_df)
        
        return {"status": "success", "data": results}

    except HTTPException as he:
        raise he
    except Exception as e:
        print("\n❌ API CRASH REPORT:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sql")
async def run_sql(request: SQLRequest):
    """Executes arbitrary SQL queries on the uploaded data."""
    print(f"🔍 SQL: {request.query}")
    result = db.execute_sql(request.query)
    return {"status": "success", "data": result}

@router.get("/sql/presets")
async def get_sql_presets():
    """Returns pre-canned queries for business users."""
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
async def get_history():
    return {"status": "success", "data": db.get_history()}

# Stub for future LLM integration
@router.post("/analyze/llm")
async def analyze_llm():
    return {"status": "success", "data": {"message": "Placeholder"}}