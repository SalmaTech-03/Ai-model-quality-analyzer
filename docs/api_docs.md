# ModelGuard API Documentation

## Overview
Enterprise-grade REST API for ML Observability.

## Endpoints

### `POST /api/analyze`
Uploads tabular data to detect distribution drift.
- **Input:** `multipart/form-data` (reference_file, current_file)
- **Output:** JSON containing Risk Score, Drift Leaderboard, and HTML Report.

### `POST /api/analyze/llm`
Scans text generation for safety.
- **Input:** JSON `{ "prompt": "...", "response": "..." }`
- **Output:** Sentiment analysis and Text Length metrics.