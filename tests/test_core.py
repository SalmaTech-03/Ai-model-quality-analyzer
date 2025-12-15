from app.core.drift_engine import DriftAnalyzer
import pandas as pd
import pytest

@pytest.fixture
def sample_data():
    # Create tiny synthetic dataframes
    ref = pd.DataFrame({"age": [20, 21, 19, 18], "salary": [1000, 1100, 900, 950]})
    curr = pd.DataFrame({"age": [45, 46, 47, 44], "salary": [5000, 5100, 4900, 4800]})
    return ref, curr

def test_drift_detection(sample_data):
    ref, curr = sample_data
    engine = DriftAnalyzer()
    result = engine.run_analysis(ref, curr)
    
    # Since we changed data drastically, it should be HIGH risk
    assert result['risk_level'] == 'HIGH'
    assert result['drift_share'] > 0.5