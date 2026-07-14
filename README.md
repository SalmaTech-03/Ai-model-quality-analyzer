# AI Model Quality Analyzer

<div align="center">

**A Production-Oriented ML Observability Platform for Data Drift Detection, Fairness Evaluation, and Rule-Based Recommendations**

---

[![Python Version](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)
[![FastAPI Framework](https://img.shields.io/badge/FastAPI-Backend-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit UI](https://img.shields.io/badge/Streamlit-Dashboard-red.svg)](https://streamlit.io/)
[![Docker Compose](https://img.shields.io/badge/Docker-Containerized-blue.svg)](https://www.docker.com/)
[![SQLite Database](https://img.shields.io/badge/SQLite-Database-lightgrey.svg)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-black.svg)](https://github.com/astral-sh/ruff)

</div>

---

# Executive Summary

The **AI Model Quality Analyzer** is an operational machine learning observability tool designed to audit, evaluate, and track the data quality of deployed machine learning models. Built for single-node deployments, the application consumes reference data (e.g., training baselines) and current production data to identify statistical covariate shift, target distribution drift, and fairness violations across protected groups. 

Rather than serving purely as a static reporting dashboard, the system processes analysis requests via a key-authenticated FastAPI backend, validates data contracts against strict Pydantic schemas, runs localized statistical evaluations via Evidently AI, evaluates outcome discrepancies using regulatory impact metrics, logs metadata to a local SQLite store, and generates actionable, rules-based operational recommendations.

---

# Project Highlights

*   **FastAPI REST API**: Authenticated endpoints utilizing header-based validation (`x-api-key`).
*   **Evidently AI Monitoring**: Automated statistical profiling of continuous and categorical features.
*   **Fairness Evaluation**: Active screening for disparate impact violations using the regulatory Four-Fifths rule.
*   **Statistical Drift Detection**: Targeted comparison of input feature and target label distributions.
*   **Streamlit Dashboard**: A companion user interface for interactive analysis and visual reports.
*   **Pydantic Data Validation**: Strict column and type validation layers guarding the execution pipeline.
*   **SQLAlchemy + SQLite**: Local relational database persistence tracking historical run metadata.
*   **Pytest Suite**: Complete unit, integration, and endpoint routing test coverage.
*   **Docker Ready**: Simple, containerized orchestration configuration for local multi-service hosting.

---

###  FastAPI Swagger Interactive Docs (`/docs`)
*Exposes the fully documented API endpoints, request schemas, and validated JSON response payloads for seamless integration.*

*(FastAPI Swagger UI Screenshot Placeholder)*

---

# High-Level System Architecture

```text
                +------------------+
                |   Streamlit UI   |
                +--------+---------+
                         |
                         | HTTP Requests (with API Key)
                         v
                +------------------+
                | FastAPI Backend  |
                +--------+---------+
                         |
         +---------------+---------------+
         |                               |
         v                               v
   Drift Engine                   Fairness Engine
 (Evidently AI)                 (Disparate Impact)
         |                               |
         +---------------+---------------+
                         |
                         v
               Recommendation Engine
            (Rules-Based Alert Matrix)
                         |
                         v
               SQLite Metadata Store
```

---

# Quick Start

### 1. Install Dependencies
Clone the repository, create a virtual environment, and install dependencies:
```bash
git clone https://github.com/YourUsername/AI-model-quality-analyzer.git
cd AI-model-quality-analyzer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
Generate your environment variables file and configure your API key:
```bash
cp .env.example .env
# Verify the default key or set your own inside the .env file:
# API_KEY=my-local-dev-key-12345
```

### 3. Fetch Baseline Data & Baseline Models
Download the sample datasets and generate the baseline model run parameters:
```bash
python scripts/download_data.py
python scripts/train_model.py
```

### 4. Run the API Backend
Start the FastAPI server on localhost:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Launch the Dashboard
In a separate terminal window, launch your Streamlit front end:
```bash
streamlit run drift_streamlit_app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser to execute and visualize your data audits.

---

# The Problem: Silent Model Degradation

Once a machine learning model leaves the controlled environment of training and enters production, its predictive accuracy begins to decay. Unlike traditional software services, which typically alert teams via stack traces, out-of-memory errors, or API timeouts, machine learning models fail silently. A loan classifier, fraud detector, or pricing system will continue to return confident predictions (HTTP 200 OK) even if the underlying distribution of inputs has completely shifted.

```text
Traditional Software Failure:
Input Data ──► [ Bug / Schema Error ] ──► HTTP 500 / Exception (Loud Failure)

Machine Learning Silent Failure:
Drifted Input ──► [ Model Engine ] ──► Confident Wrong Prediction (Silent Failure)
```

Silent degradation is caused by several factors:
- **Covariate Shift**: The distribution of input features changes over time (e.g., shifts in average customer income or changing macro-economic conditions).
- **Concept Drift**: The relationship between model inputs and targets changes (e.g., historical default rates for specific debt ratios no longer reflect current realities).
- **Data Quality Issues**: Upstream ETL pipelines introduce unexpected nulls, zero values, or encoding formats that the model was not trained to handle.
- **Fairness Divergence**: A stable model can systematically develop biases against protected classes if the relationship between demographic features and target variables changes.

By the time downstream business metrics show a visible decline, inaccurate predictions may have been served for weeks. This platform is engineered to detect these silent failures early, flagging statistical anomalies before they impact the business bottom line.

---

# System Scope & Capabilities

This service is engineered to be a lightweight, self-contained analytical and metadata logging server. To prevent architectural overclaiming, its functional scope is defined below:

*   **Implemented**: Structured statistical monitoring of numerical and categorical variables, disparate impact fairness evaluation, API-based analytics orchestration, localized SQLite metadata logging, and a lightweight local registry state tracker storing evaluation metrics.
*   **Not Implemented (Out of Scope)**: Distributed message streaming (Kafka/RabbitMQ), persistent model hosting/serving, distributed background task queues (Celery/Redis), dynamic cluster scaling (Kubernetes/Helm), or cloud object storage.

---

# Folder-by-Folder Codebase Explanation

The system is organized with strict separation of concerns, decoupling presentation code, REST routing, validation logic, and numerical evaluation.

```text
AI-model-quality-analyzer/
│
├── .github/
│   └── workflows/
│       ├── deploy.yml          <-- Automation script running Docker builds
│       └── testing.yml         <-- CI test pipeline executing style checks & pytest
│
├── app/
│   ├── api/
│   │   └── routes.py           <-- FastAPI endpoints, payload parsing, and Dependency Injection
│   │
│   ├── core/
│   │   ├── analyzer.py         <-- Coordination module matching schema validation to analytical output
│   │   ├── config.py           <-- Configuration file loading thresholds from environmental files
│   │   ├── database.py         <-- SQLAlchemy engine config, SessionLocal generator, and metadata runs
│   │   ├── drift_engine.py     <-- Evidently report wrapper extracting statistical drift metrics & target drift
│   │   ├── fairness.py         <-- Statistical module for disparate impact ratio and 4/5ths rule calculation
│   │   ├── registry.py         <-- Local file storing model evaluation history and recommendation metadata
│   │   └── schemas.py          <-- Data validation contracts (Pydantic model of AdultCensus)
│   │
│   └── main.py                 <-- Service entry point configuring CORS, standard logs, and API routes
│
├── data/                       <-- SQLite database storage, plus local baseline reference CSVs
│
├── scripts/                    <-- Local utilities for data downloads and initial baseline training runs
│
├── tests/                      <-- Complete Pytest suite covering unit, integration, and endpoint contracts
│
├── drift_streamlit_app.py      <-- Interactive user interface written in Streamlit
│
├── Dockerfile                  <-- Container runtime specification preparing the execution environment
│
├── docker-compose.yml          <-- Multi-container definition packaging the API service and UI
│
├── requirements.txt            <-- Pinned package requirements ensuring environment reproducibility
│
└── .env.example                <-- Template defining required environmental variables
```

---

# Request Lifecycle & Core Logic

Every analysis request is received, validated, and processed sequentially:

```text
CSV Data ──► Input Validation ──► Preprocessing ──► Statistical Tests ──► Risk Score ──► Recommendation
```

Individual feature variables are profiled step-by-step to identify structural changes:

```text
Feature Column ──► Check Missing Values ──► Distribution Check ──► Run Drift Test ──► Result Output
```

---

# Architectural Decisions & Technology Rationale

1. **Why FastAPI over Flask or Django?**
   FastAPI provides asynchronous request handling capability, although the analytical pipeline executes synchronously because Evidently and pandas perform CPU-bound operations. This native async request boundary protects the I/O event loop during heavy concurrent file uploads. Additionally, native Pydantic integration guarantees automated type enforcement and schema documentation.

2. **Why Evidently AI for Drift Monitoring?**
   Rather than manually writing custom statistical routines for every feature type, Evidently AI acts as a mature, tested core. It profiles columns automatically, distinguishing between continuous numeric variables and discrete categorical labels, and applies appropriate algorithms (such as Kolmogorov-Smirnov, Population Stability Index, or Chi-Square tests) based on data characteristics.

3. **Why SQLite over PostgreSQL or MongoDB for Metadata Storage?**
   Since this service runs as a self-contained, single-node analysis helper, SQLite offers robust ACID compliance via a standard file, with zero external database processes to manage. This simplifies local and containerized development. The database engine utilizes SQLAlchemy, which decouples the queries from SQLite, allowing for a straightforward transition to PostgreSQL if horizontal scaling becomes a future requirement.

4. **Why Streamlit for Dashboarding?**
   Streamlit enables developers to build data-focused user interfaces completely in Python. This allows the frontend to easily share model schemas, helper methods, and metrics directly with the backend code, eliminating the need to maintain a separate JavaScript framework (such as React or Vue) for simple internal dashboarding.

---

# Design Patterns Used

- **Dependency Injection (DI)**: In `routes.py`, database sessions (`db`) and the local model recommendation tracking class (`registry`) are provided through FastAPI's `Depends()`. This pattern keeps route declarations loosely coupled to specific database instances, making it easy to swap them with SQLite memory databases or mock containers during unit testing.
- **Data Transfer Object (DTO)**: Data exchange across API routes and analysis methods is mediated by Pydantic schema models. This ensures that only validated data payloads pass between core business logic and presentation layers.
- **Repository Pattern (via SQLAlchemy)**: Database access is handled through object-relational mapping models, decoupling raw SQL commands from SQLite. This structure protects queries from database-specific syntax changes and simplifies future migrations to other relational systems.
- **Separation of Concerns (SoC)**: Data contracts (the validation logic), and mathematical analysis (the drift calculations) are isolated in separate modules. Changes in statistical thresholds do not affect database structures, and database updates do not alter route endpoints.

---

# Logical Metadata Schema

The SQLite database acts as a metadata repository, logging historical analysis requests. Below is the relational structure of the local metadata storage:

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                                 runs                                         │
├──────────────────────────────────────────────────────────────────────────────┤
│ id (INTEGER, PK) ────────────────────────────────────────────────────────┐   │
│ reference_shape (VARCHAR)                                                │   │
│ current_shape (VARCHAR)                                                  │   │
│ overall_drift (BOOLEAN)                                                  │   │
│ risk_level (VARCHAR)                                                     │   │
│ decision (VARCHAR)                                                       │   │
│ analyzed_at (TIMESTAMP)                                                  │   │
└──────────────────────────────────────────────────────────────────────────┼───┘
                                                                           │
                                                                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           feature_metrics                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│ id (INTEGER, PK)                                                             │
│ run_id (INTEGER, FK -> runs.id) ◄────────────────────────────────────────────┘
│ feature_name (VARCHAR)                                                       │
│ metric_name (VARCHAR)                                                        │
│ drift_score (FLOAT)                                                          │
│ drift_detected (BOOLEAN)                                                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

- **`runs` Table**: Logs overall operational metadata for each execution. It captures file profiles (shapes), overall stability verdicts, risk assessments, and the final state recommendations.
- **`feature_metrics` Table**: Stores the feature-by-feature statistical outcomes generated by Evidently AI for each run. This structured data is used to populate feature ranking tables and track quality trends over time.

---

# Core System Logic & Pipelines

## Data Validation Layer

Before running statistical comparisons, the system validates the incoming CSV files. If either dataset fails schema validation, the request is rejected immediately, preventing downstream statistical errors.

The validation schema is configured to a structure modeled around the **Adult Census** dataset. 

```python
# app/core/schemas.py
from pydantic import BaseModel, Field

class AdultCensusRow(BaseModel):
    age: int = Field(..., ge=17, le=90)
    workclass: str
    education: str
    marital_status: str = Field(..., alias="marital-status")
    occupation: str
    relationship: str
    race: str
    sex: str
    hours_per_week: int = Field(..., alias="hours-per-week", ge=1, le=99)
    native_country: str = Field(..., alias="native-country")
    income: str
```

*Note: In production deployments, this schema should be dynamically configurable to support monitoring of arbitrary datasets.*

---

## Statistical Drift Detection Engine

The system uses Evidently AI's data profiling suite to evaluate distribution changes between your baseline and current production datasets.

```text
                       COLUMN PROFILING PIPELINE
                      ┌──────────────────────────┐
                      │    Input Pandas Series   │
                      └────────────┬─────────────┘
                                   │
                      ┌────────────▼─────────────┐
                      │ Is Variable Continuous?  │
                      └────────────┬─────────────┘
                                   │
                ┌──────────────────┴──────────────────┐
                ▼ (Yes)                               ▼ (No)
   Numerical Distribution                 Categorical Distribution
                │                                     │
   ┌────────────▼─────────────┐          ┌────────────▼─────────────┐
   │ Kolmogorov-Smirnov Test  │          │      Chi-Square Test     │
   │   (Compares CDF curves)  │          │   (Compares frequencies) │
   └──────────────────────────┘          └──────────────────────────┘
```

The analyzer runs these algorithms to evaluate drift:
- **Numerical Features (Kolmogorov-Smirnov Test)**: Compares the empirical cumulative distribution functions (CDFs) of your continuous variables. If the maximum distance ($D$) between CDFs exceeds the critical threshold defined by the significance level ($\alpha=0.05$), the feature is flagged as drifted.
- **Categorical Features (Chi-Square Test)**: Evaluates the categorical frequencies between datasets. If the calculated $\chi^2$ statistic yields a $p$-value lower than $0.05$, the category distribution is flagged as drifted.

---

## Target & Label Drift Monitoring

Changes in your input features are only part of the story; monitor shifts in the predicted labels and true values as well. A change in the target variable's distribution is a strong indicator of concept drift, suggesting that your model's underlying assumptions may have broken down.

```text
               Target Variable: Z-Test for Proportions
                ┌───────────────────────────────────┐
                │ Baseline Outcome Rate (e.g., 20%) │
                └─────────────────┬─────────────────┘
                                  │ (Statistical Compare)
                                  ▼
                ┌───────────────────────────────────┐
                │ Production Outcome Rate (e.g.,90%)│
                └─────────────────┬─────────────────┘
                                  │
                                  ▼
                     p-value Calculation (< 0.05)
                                  │
                                  ▼
                        Target Drift Detected
```

The system evaluates categorical target shifts using a two-sample Z-test for proportions, flagging structural anomalies if the resulting $p$-value falls below $0.05$.

---

## Fairness Evaluation (Four-Fifths Rule)

The system includes a dedicated fairness monitor that evaluates prediction outcomes for potential demographic bias. The fairness engine uses the **Four-Fifths Rule** (or Disparate Impact Ratio), a standard metric in regulatory compliance and employment law.

The disparate impact ratio ($DIR$) is defined as:

$$DIR = \frac{P(\hat{Y} = 1 \mid \text{Protected Group} = 1)}{P(\hat{Y} = 1 \mid \text{Reference Group} = 0)}$$

```text
             Protected Attribute: Gender (Disparate Impact)
                ┌───────────────────────────────────┐
                │ Positive Rate: Female (e.g., 10%) │
                └─────────────────┬─────────────────┘
                                  │ (Ratio Division)
                                  ▼
                ┌───────────────────────────────────┐
                │  Positive Rate: Male (e.g., 40%)  │
                └─────────────────┬─────────────────┘
                                  │
                                  ▼
                     Disparate Impact = 0.25
                                  │
                                  ▼
                   Bias Flagged (0.25 < 0.80 Limit)
```

The fairness monitor raises a flag if the disparate impact ratio falls below $0.80$, signaling that predictions differ significantly across demographic groups. To prevent false positives, a minimum group size threshold is enforced ($N \ge 50$ rows). Smaller populations are excluded from the fairness audit to avoid flagging minor statistical fluctuations.

---

## Rules-Based Recommendation Engine

Instead of simply reporting raw statistics, the analyzer processes metrics through a rules-based recommendation engine. The engine evaluates the statistical results in order of severity to log operational recommendations:

```text
                                  ┌───────────────────────────┐
                                  │   Start Decision Engine   │
                                  └─────────────┬─────────────┘
                                                │
                                                ▼
                                  ┌───────────────────────────┐
                                  │ Evaluate Fairness Violate │
                                  └─────────────┬─────────────┘
                                                │
                               ┌────────────────┴────────────────┐
                               ▼ (Yes)                           ▼ (No)
                ┌─────────────────────────────┐   ┌─────────────────────────────┐
                │ RECOMMEND: BLOCK DEPLOYMENT │   │ Is Target Drift Detected?   │
                └─────────────────────────────┘   └─────────────┬─────────────┘
                                                                │
                                               ┌────────────────┴────────────────┐
                                               ▼ (Yes)                           ▼ (No)
                                ┌─────────────────────────────┐   ┌─────────────────────────────┐
                                │ RECOMMEND: STATE REVERT     │   │ Evaluate Feature Drift %    │
                                └─────────────────────────────┘   └─────────────┬─────────────┘
                                                                                │
                                                               ┌────────────────┴────────────────┐
                                                               ▼ (> 50% Columns)                 ▼ (<= 50% Columns)
                                                ┌─────────────────────────────┐   ┌─────────────────────────────┐
                                                │ RECOMMEND: RETRAIN MODEL    │   │ RECOMMEND: CONTINUE MONITOR │
                                                └─────────────────────────────┘   └─────────────────────────────┘
```

The local registry module (`registry.py`) acts as a historical log storage file, committing model version details and recommended model states inside local metadata database tables.

---

# API Reference & Usage Examples

The FastAPI service exposes endpoints for service checkouts and dataset audits.

### Service Health
```bash
curl -X GET "http://localhost:8000/"
```

**Expected Response (200 OK):**
```json
{
  "status": "running"
}
```

---

### Dataset Analysis
```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "x-api-key: my-local-dev-key-12345" \
  -F "reference=@data/adult_census_reference.csv" \
  -F "current=@data/adult_census_current.csv"
```

**Expected Response (200 OK):**
```json
{
  "status": "success",
  "overall_drift": true,
  "risk_level": "High",
  "decision": "Retrain Recommended",
  "dataset_summary": {
    "reference_shape": [15000, 11],
    "current_shape": [15000, 11],
    "drifted_features_count": 6,
    "total_features_count": 10,
    "drift_share": 0.6
  },
  "feature_summary": [
    {
      "feature_name": "age",
      "drift_score": 0.00001,
      "drift_detected": true
    },
    {
      "feature_name": "hours-per-week",
      "drift_score": 0.0012,
      "drift_detected": true
    }
  ],
  "fairness": {
    "protected_attribute": "sex",
    "disparate_impact_ratio": 0.82,
    "violation_detected": false
  },
  "target_drift": {
    "target_name": "income",
    "p_value": 0.124,
    "drift_detected": false
  }
}
```

---

# Docker Container Configuration

The system is containerized using standard Docker runtime files to ensure predictable setups on different host machines.

The included `docker-compose.yml` file configures local networking to connect our FastAPI backend with our Streamlit user interface:

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - API_KEY=my-local-dev-key-12345
      - APP_ENV=development
    volumes:
      - ./data:/app/data

  frontend:
    build: .
    ports:
      - "8501:8501"
    command: streamlit run drift_streamlit_app.py --server.port 8501 --server.address 0.0.0.0
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend
```

---

# CI Pipeline (GitHub Actions Specification)

The repository includes standard GitHub Action workflows designed to execute style guidelines and run pytest on every pull request.

- **`.github/workflows/deploy.yml`**: Validates the build path by testing whether the Docker configuration compiles correctly on a standardized Ubuntu runner.
- **`.github/workflows/testing.yml`**: Resolves python dependencies, installs system prerequisites (such as `libgomp1` to support scientific libraries), fetches data baselines, and executes the Pytest suite.

---

# Testing Strategy

The project features tests split across three strategic levels of concern:

- **Unit Testing**: Tests core mathematical utilities in isolation. It verifies the fairness monitor's division-by-zero protection when target columns contain only single-class labels, and checks that small populations are correctly excluded from audits.
- **Integration Testing**: Validates cooperation between our analysis layers and the Evidently AI library. These tests pass real dataframes through the system to ensure that calculations and thresholds are evaluated correctly.
- **Endpoint Routing & Dependency Injection Tests**: Uses FastAPI's `TestClient` and `dependency_overrides` to run endpoint tests. This allows us to test authentication and validation layers using mock SQLite instances, keeping the test database clean.

---

# Estimated Operational Characteristics

Memory usage increases with dataset size because pandas and Evidently maintain intermediate in-memory structures during analysis. Practical limits depend on available system memory and dataset characteristics. For processing very large datasets, it is recommended to apply an initial random sampling stage before uploading data to the `/analyze` endpoint to manage memory requirements on single-node setups.

---

# Security Best Practices

The system includes several security controls designed to safeguard local operations:

1. **Fail-Closed API Authentication**: If the server starts and the `API_KEY` environmental variable is empty or unset, the system defaults to a secure state. It rejects all incoming requests with an HTTP 500 configuration error, preventing unauthenticated access due to configuration mistakes.
2. **Standard Headers & CORS Controls**: Standard CORS policies are set up inside `main.py`, restricting allowed origins to the frontend's specific port to prevent cross-site scripting vulnerabilities.
3. **Local Database Isolation**: The SQLite metadata file is located in a protected data directory with access permissions restricted to the application's runtime system process.

---

# Monitoring & Logging Strategy

Operation logging is handled through Python’s standard logging utility, using a structured formatting template to capture execution events:

```text
LOG FORMAT:
[timestamp] | [log-level] | [module_name] | [transaction_id] | message
```

Key operational events are logged sequentially to provide clear tracing during troubleshooting:

```text
[2026-07-14 21:35:04] | INFO | app.main | [system] | FastAPI service initialized on Port 8000
[2026-07-14 21:36:12] | INFO | app.api  | [txn_485] | POST /api/analyze request received
[2026-07-14 21:36:13] | INFO | app.core | [txn_485] | Schema validation passed. Shape: (15000, 11)
[2026-07-14 21:36:15] | INFO | app.core | [txn_485] | Analysis complete. Metrics: 6/10 columns drifted
[2026-07-14 21:36:15] | WARN | app.core | [txn_485] | Decision generated: Retrain Recommended (Score: 60)
[2026-07-14 21:36:15] | INFO | app.api  | [txn_485] | Run ID 142 committed to metadata storage
```

---

# Project Limitations

Every engineering project has architectural trade-offs. The limitations of the current design are documented below:

- **Hardcoded Schema Validation**: The validation schema in `app/core/schemas.py` is configured to a single dataset structure. If a user uploads datasets from another domain, the data validation layer will reject them.
- **In-Memory Pandas Processing**: Because data is loaded entirely into memory, large datasets can cause out-of-memory failures depending on single-node hardware limitations.
- **Single API Key Authentication**: The authentication layer uses a single shared secret key, making it unsuitable for multi-tenant environments that require individual keys, access scopes, or audit histories.

---

# Planned Future Improvements

To transition this platform from a single-node utility into an automated ML observability platform, the following structural improvements are planned:

```text
       CURRENT SYSTEM                          PLANNED PRODUCTION SYSTEM
┌─────────────────────────────┐             ┌─────────────────────────────┐
│  In-Memory Pandas Loading   │  ────────►  │  Memory-Bounded Polars/Arrow│
├─────────────────────────────┤             ├─────────────────────────────┤
│  Hardcoded Pydantic Schema  │  ────────►  │  Dynamic JSON-Schema Engine │
├─────────────────────────────┤             ├─────────────────────────────┤
│  SQLite Metadata File       │  ────────►  │  PostgreSQL + DB Migrations │
├─────────────────────────────┤             ├─────────────────────────────┤
│  Synchronous File Uploads   │  ────────►  │  S3/Object Storage + Celery │
└─────────────────────────────┘             └─────────────────────────────┘
```

1. **Polars Integration**: Replace pandas with Polars or PyArrow to enable memory-bounded, out-of-core file operations and prevent RAM failures on large datasets.
2. **Dynamic JSON-Schema Validation**: Replace the hardcoded Pydantic schema with a dynamic validation layer that reads dataset structure requirements from JSON configuration files.
3. **PostgreSQL Integration**: Migrate database persistence from SQLite to PostgreSQL, managing updates through SQLAlchemy migrations.
4. **Asynchronous Task Architecture**: Add Celery and Redis to process analysis requests asynchronously, letting the API quickly return a job ID while worker processes perform the calculations.

---

# Key Engineering Skills Demonstrated

- **FastAPI**: Asynchronous REST framework configuration and API routing.
- **Docker**: Portable execution environments and container setups.
- **REST API Design**: Secure, key-authenticated REST endpoints.
- **Statistical Monitoring**: Data drift, label drift, and fairness metric calculation.
- **Pydantic Validation**: Strict data contract validation schemas.
- **SQLAlchemy**: Decoupled relational metadata models.
- **Pytest**: Modular testing patterns spanning unit, integration, and API tests.

---

# Local Setup & Running Instructions

### 1. Requirements Setup
Clone the repository and create a clean virtual environment:
```bash
git clone https://github.com/YourUsername/AI-model-quality-analyzer.git
cd AI-model-quality-analyzer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
Generate your environment variables file and configure your API key:
```bash
cp .env.example .env
# Edit the .env file to verify the default API key:
# API_KEY=my-local-dev-key-12345
```

### 3. Fetch Baseline Data & Baseline Models
Download the sample datasets and generate the baseline model run parameters:
```bash
python scripts/download_data.py
python scripts/train_model.py
```

### 4. Run the API Server
Start the FastAPI server:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Launch the Dashboard
In a separate terminal tab, start your Streamlit user interface:
```bash
streamlit run drift_streamlit_app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser to explore your statistical reports.

---

# License

This project is licensed under the MIT License. Refer to the LICENSE file for complete license information.
