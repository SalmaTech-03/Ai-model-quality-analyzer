import os

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Thresholds for Risk Badge (Used in core/analyzer.py)
RISK_HIGH_THRESHOLD = 0.5  # If >50% features drift -> HIGH RISK
RISK_MID_THRESHOLD = 0.2   # If >20% features drift -> MEDIUM RISK