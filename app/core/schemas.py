from pydantic import BaseModel, Field, validator, ValidationError
from typing import Optional
import pandas as pd

class AdultCensusRow(BaseModel):
    """
    Data Contract for the Adult Census Dataset.
    Enforces strict types and value ranges to prevent system crashes.
    """
    age: int = Field(..., ge=17, le=100, description="Employee Age")
    workclass: str
    fnlwgt: int
    education: str
    # Handling hyphens in CSV headers via aliases
    education_num: int = Field(..., alias="education-num", ge=1, le=16)
    marital_status: str = Field(..., alias="marital-status")
    occupation: str
    relationship: str
    race: str
    sex: str
    capital_gain: int = Field(..., alias="capital-gain", ge=0)
    capital_loss: int = Field(..., alias="capital-loss", ge=0)
    hours_per_week: int = Field(..., alias="hours-per-week", gt=0, le=168)
    native_country: str = Field(..., alias="native-country")
    target: str = Field(..., alias="class")

    @validator('target')
    def validate_target(cls, v):
        # Ensure target labels match what the model expects
        if v.strip() not in ['<=50K', '>50K']:
            raise ValueError(f"Unknown target label: {v}")
        return v

def validate_dataframe(df: pd.DataFrame, limit: int = 100):
    """
    Runs schema validation on the first 'limit' rows of a DataFrame.
    Returns (True, None) or (False, error_message).
    """
    errors = []
    # Convert DataFrame to dict records for Pydantic validation
    records = df.head(limit).to_dict(orient='records')
    
    for i, record in enumerate(records):
        try:
            AdultCensusRow(**record)
        except ValidationError as e:
            # Format error for readability in the UI
            try:
                err_msg = e.errors()[0]['msg']
                loc = e.errors()[0]['loc'][0]
                errors.append(f"Row {i} - Field '{loc}': {err_msg}")
            except:
                errors.append(f"Row {i}: {str(e)}")
            
    if errors:
        return False, errors
    return True, None