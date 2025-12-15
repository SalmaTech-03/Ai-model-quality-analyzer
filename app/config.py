import os

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data paths
DATA_DIR = os.path.join(BASE_DIR, "data")
REF_DATA_PATH = os.path.join(DATA_DIR, "housing_reference.csv")
CURR_DATA_PATH = os.path.join(DATA_DIR, "housing_current.csv")
ADULT_DATA_PATH = os.path.join(DATA_DIR, "adult_census.csv")

# Thresholds for Risk Badge
RISK_HIGH_THRESHOLD = 0.5  # If >50% features drift -> HIGH RISK
RISK_MID_THRESHOLD = 0.2   # If >20% features drift -> MEDIUM RISK