from app.core.analyzer import DriftAnalyzer
import pandas as pd
import os

# Load the data you downloaded
ref = pd.read_csv("data/housing_reference.csv")
curr = pd.read_csv("data/housing_current.csv")

print(" Initializing Brain...")
engine = DriftAnalyzer()

print(" Running Analysis (This uses the CPU)...")
results = engine.run_analysis(ref, curr)

print(f"Analysis Complete!")
print(f"Risk Level: {results['risk_level']}")
print(f"Top Drifting Feature: {results['leaderboard'][0]['feature']}")