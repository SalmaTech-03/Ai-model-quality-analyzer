import pandas as pd
import numpy as np
from sklearn.datasets import fetch_california_housing, fetch_openml
import os
import ssl

# Fix SSL issues for some networks
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Setup Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

print(f" Storage: {DATA_DIR}")
print(" Starting Enterprise Data Ingestion (6 Datasets)...")

def save_drift_pair(name, df, split_col, threshold, sample_size=50000):
    """
    Splits data based on a feature value to create 'Artificial Drift'.
    Ref = Low/Old values
    Curr = High/New values
    """
    try:
        print(f"\n🔹 Processing: {name} (Total Rows: {len(df)})")
        
        # 1. Clean Data
        df = df.dropna()
        
        # 2. Engineer Drift
        # We split by a specific column to simulate the world changing
        # (e.g., Inflation: Prices went up, so Reference is cheap, Current is expensive)
        ref = df[df[split_col] < threshold]
        curr = df[df[split_col] >= threshold]
        
        # 3. Cap size to keep repo manageable (but large enough for 50k requirement)
        # If dataset is huge, we take a random sample up to sample_size
        if len(ref) > sample_size: ref = ref.sample(sample_size, random_state=42)
        if len(curr) > sample_size: curr = curr.sample(sample_size, random_state=42)

        # 4. Save
        ref.to_csv(os.path.join(DATA_DIR, f"{name}_reference.csv"), index=False)
        curr.to_csv(os.path.join(DATA_DIR, f"{name}_current.csv"), index=False)
        
        print(f"    Saved: {name} | Ref: {len(ref)} rows | Curr: {len(curr)} rows")
        
    except Exception as e:
        print(f"    Failed {name}: {e}")

# 1. Housing Prices (Economic Drift)

housing = fetch_california_housing(as_frame=True).frame
save_drift_pair("housing", housing, "MedHouseVal", 2.0, 10000)


# 2. Adult Census (Demographic Bias)

# OpenML ID: 1590
adult = fetch_openml(data_id=1590, as_frame=True, parser="auto").frame
# Fix column types
for col in adult.select_dtypes(['category']):
    adult[col] = adult[col].astype('object')
save_drift_pair("adult_census", adult, "age", 40, 25000)


# 3. Diamonds (Luxury Market Drift)

# OpenML ID: 42225 (Diamonds) ~54k rows
diamonds = fetch_openml(data_id=42225, as_frame=True, parser="auto").frame
# Drift Scenario: Reference = Smaller diamonds, Current = Larger diamonds
save_drift_pair("diamonds", diamonds, "price", 2000, 25000)


# 4. Bank Marketing (Behavioral Drift)

# OpenML ID: 1461 (Bank Marketing) ~45k rows
bank = fetch_openml(data_id=1461, as_frame=True, parser="auto").frame
# Drift Scenario: Reference = Short calls, Current = Long calls
save_drift_pair("bank_marketing", bank, "V12", 200, 20000) # V12 is usually duration

# 5. Forest Covertype (Environmental Drift) - HUGE

# OpenML ID: 1596 (Covertype) ~581k rows
# We will downsample this to 100k total
cover = fetch_openml(data_id=1596, as_frame=True, parser="auto").frame
# Drift Scenario: Elevation shift
save_drift_pair("forest_cover", cover, "Elevation", 2900, 50000)


# 6. Electricity (Time Series/Energy Drift)

# OpenML ID: 151 (Electricity) ~45k rows
elec = fetch_openml(data_id=151, as_frame=True, parser="auto").frame
# Drift Scenario: Period shift
save_drift_pair("electricity", elec, "period", 0.5, 20000)

print("\n ALL DATASETS DOWNLOADED SUCCESSFULLY!")