from pydantic import BaseModel, Field, validator, ValidationError
import pandas as pd

class AdultCensusRow(BaseModel):
    age: int = Field(..., ge=17, le=100)
    workclass: str
    fnlwgt: int
    education: str
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
        if v.strip() not in ['<=50K', '>50K']:
            raise ValueError(f"Unknown target label: {v}")
        return v

def validate_dataframe(df: pd.DataFrame, limit: int = 100):
    errors = []
    records = df.head(limit).to_dict(orient='records')
    for i, record in enumerate(records):
        try:
            AdultCensusRow(**record)
        except ValidationError as e:
            errors.append(f"Row {i}: {str(e)}")
    if errors:
        return False, errors
    return True, None
