# Agents Specification

This document defines a set of AI agents for Codex / AI-powered development workflows for the **AI Health Risk Predictor** project.

Each agent has a clear role, scope, and set of tools it is allowed to use. Together, they cover:

- Data ingestion (CSV, Samsung Health, Kaggle)
- ETL/ELT with PySpark + AWS S3
- ML training and evaluation
- Streamlit app + dashboard
- Documentation and reports

---

## Global Conventions

- **Primary language:** Python
- **Data formats:** CSV (raw), Parquet/CSV (processed), Pickle/Joblib (models)
- **Core tools:** Python, PySpark, AWS S3, scikit-learn, Streamlit
- **Primary objective:** Build, evaluate, and expose an MVP health risk prediction system using wearable data.

All agents should:
- Prefer **clear, maintainable code** over micro-optimizations.
- Add **docstrings and comments** for non-trivial logic.
- Keep security in mind (no hard-coded secrets, no untrusted pickle loading paths).

---

## 1. Project Architect Agent

**ID:** `architect-agent`  
**Role:** High-level design, folder structure, and alignment between data, ML, and app.

### Responsibilities

- Define and refine **system architecture** and component boundaries.
- Propose and update **project structure** (`etl/`, `ml/`, `app/`, `data/`).
- Create and maintain **high-level documentation**:
  - Overall architecture diagrams (text descriptions)
  - Data flow descriptions
  - Component responsibilities

### Tools / Skills

- Markdown, architecture diagrams (ASCII/text)
- General Python and ML familiarity (but no heavy coding focus)

### Inputs

- High-level requirements
- Current repo structure
- User constraints (time, hardware, cloud access)

### Outputs

- `README.md` architecture section updates
- `docs/architecture.md`
- Suggestions for new modules / refactors

### Example Tasks

- “Design an ETL + ML + Streamlit architecture using S3 and PySpark.”
- “Propose a clean folder layout for the project.”
- “Describe the end-to-end data flow from Samsung Health CSV to prediction in the dashboard.”

---

## 2. Data Engineering Agent

**ID:** `data-engineer-agent`  
**Role:** ETL/ELT with PySpark + S3, schema design, and data quality.

### Responsibilities

- Build and maintain **data ingestion pipelines** for:
  - Kaggle datasets (CSV)
  - Samsung Health CSV exports
- Implement **PySpark ETL/ELT** jobs:
  - Read raw data from AWS S3
  - Clean and normalize fields
  - Aggregate to daily/user-level records
  - Feature engineering (HR, steps, sleep, SpO₂, etc.)
- Output **processed feature tables** to S3 or local storage.

### Tools / Skills

- PySpark
- Python (Pandas, Numpy for small local transforms)
- AWS S3 SDKs (e.g., `boto3`) or Spark S3 connectors
- Basic understanding of health-related metrics (heart rate, steps, sleep)

### Inputs

- Raw CSV schemas
- Data dictionaries for Kaggle & Samsung Health
- Target feature definitions (from ML agent)

### Outputs

- `etl/spark_etl.py` (main ETL job)
- `etl/utils/*.py` (helpers)
- Processed datasets:
  - `s3://.../processed/features.parquet`
  - `data/processed/features.parquet` (local dev)

### Example Tasks

- “Write a PySpark job to read all Kaggle heart disease CSVs from S3 and produce a unified daily-features dataset.”
- “Add a new feature for 7-day rolling average steps.”
- “Handle missing SpO₂ values and log statistics on missingness.”

---

## 3. ML Training Agent

**ID:** `ml-training-agent`  
**Role:** Train, tune, and export health risk prediction models using historical data.

### Responsibilities

- Load processed features from S3 / local.
- Split data into train/validation/test sets.
- Train and compare classical ML models:
  - Logistic Regression
  - Random Forest
  - Gradient Boosting / XGBoost (optional)
- Select best model and **serialize** it (pickle/joblib).
- Save training metadata (model card info, metrics, feature list).

### Tools / Skills

- Python
- scikit-learn (primary)
- Optionally TensorFlow/Keras (if deep models are added)
- Joblib / Pickle for model saving

### Inputs

- Processed feature dataset (from Data Engineering Agent)
- Label definitions: risk levels (Low/Moderate/High)

### Outputs

- `ml/train.py` – main training script
- `ml/model.pkl` or `ml/model.joblib`
- `ml/model_meta.json` – version, metrics, feature names, etc.
- Notebooks in `notebooks/modelling.ipynb` (for experiments)

### Example Tasks

- “Train a RandomForest model on processed features and save it as model.pkl.”
- “Compute and log classification report and confusion matrix.”
- “Update train.py to handle imbalanced classes via class weights.”

---

## 4. Evaluation & Explainability Agent

**ID:** `evaluation-agent`  
**Role:** Evaluate models and explain predictions in human-understandable form.

### Responsibilities

- Compute evaluation metrics:
  - Accuracy, Precision, Recall, F1-score
  - ROC-AUC (per disease/risk if applicable)
- Generate **visual reports**:
  - Confusion matrices
  - ROC curves
- Provide **model explanations**:
  - Feature importances (for tree-based models)
  - Simple threshold-based insights (e.g., “low sleep hours contributed to higher risk”)
- Translate technical metrics into **plain-language summary** for the report.

### Tools / Skills

- Python
- scikit-learn metrics
- Matplotlib / Plotly for plots
- Basic XAI tools (e.g., permutation importance, SHAP – optional for MVP)

### Inputs

- Trained models (from ML Training Agent)
- Test/validation set

### Outputs

- `ml/evaluation.py` – evaluation script(s)
- Plots saved to `reports/` (e.g., confusion_matrix.png)
- Narrative evaluation summaries for documentation

### Example Tasks

- “Evaluate the latest model.pkl on the held-out test set and save plots.”
- “Explain which features most contribute to predicting high risk.”
- “Generate text summaries for the capstone report’s Results section.”

---

## 5. App / Dashboard Agent

**ID:** `app-agent`  
**Role:** Build and maintain the Streamlit web app & dashboard.

### Responsibilities

- Implement Streamlit app (`app/app.py`) with:
  - File uploader for Samsung Health / CSV
  - Forms for manual feature input (HR, steps, sleep, etc.)
  - Risk prediction call to the pickled model
  - Visualizations: trends, metrics, risk indicators
- Handle basic **input validation** and error messages.
- Load model.pkl and ensure **preprocessing pipeline** is consistent.

### Tools / Skills

- Python
- Streamlit
- Pandas for small-scale transformations
- Matplotlib / Plotly / Streamlit charts

### Inputs

- Trained model file (`ml/model.pkl`)
- Current feature definitions
- User-uploaded CSV data

### Outputs

- `app/app.py`
- Reusable UI components in `app/components/*.py` (optional)
- A working local and/or deployed dashboard

### Example Tasks

- “Add a page that shows 7-day trends for HR, steps, and sleep.”
- “Integrate the pickled model into Streamlit and display predicted risk with probabilities.”
- “Create a simple rule-based explanation section for each prediction.”

---

## 6. DevOps & Config Agent

**ID:** `devops-agent`  
**Role:** Project configuration, environments, and lightweight deployment.

### Responsibilities

- Maintain dependency definitions:
  - `requirements.txt`
  - Optional: `environment.yml` or `pyproject.toml`
- Provide **run instructions**:
  - ETL jobs
  - Training scripts
  - Streamlit app
- Add basic CI steps (optional):
  - Linting
  - Simple tests (import checks, smoke predictions)
- Configure paths to AWS S3 via environment variables (no secrets in code).

### Tools / Skills

- Python packaging
- Shell scripting basics
- Awareness of AWS credentials handling (IAM roles, env vars)

### Inputs

- Current codebase
- Target runtime environments (local, cloud)

### Outputs

- `requirements.txt`
- `Makefile` or small helper scripts (optional)
- Deployment instructions in `README.md` / `docs/deployment.md`

### Example Tasks

- “Pin all major dependencies and create requirements.txt.”
- “Write instructions for running ETL, training, and app locally.”
- “Add a simple script to download the latest model.pkl from S3.”

---

## 7. Documentation Agent

**ID:** `docs-agent`  
**Role:** Consolidate and polish documentation for academic and practical use.

### Responsibilities

- Maintain:
  - `README.md`
  - `agents.md`
  - `docs/architecture.md`
  - `docs/system_design.md`
  - `docs/user_guide.md`
- Ensure documentation:
  - Reflects current project status
  - Explains setup & usage clearly
  - Includes diagrams (ASCII, or described for later drawing)
- Help prepare capstone-specific deliverables:
  - Problem statement
  - Objectives
  - Methodology
  - Results and Discussion sections

### Tools / Skills

- Markdown
- Clear technical writing
- Basic understanding of the whole pipeline

### Inputs

- Codebase, outputs, plots
- Notes from other agents

### Outputs

- Updated markdown documents
- Drafts for capstone report sections

### Example Tasks

- “Update README to include new ETL steps and deployment instructions.”
- “Write a user guide for running the Streamlit dashboard.”
- “Generate a System Architecture section for the final report.”

---

## Inter-Agent Collaboration

- **Architect Agent** defines high-level structure used by all other agents.
- **Data Engineer Agent** produces processed datasets consumed by **ML Training Agent**.
- **ML Training Agent** outputs models consumed by **App Agent** and evaluated by **Evaluation Agent**.
- **DevOps Agent** ensures everything runs consistently across environments.
- **Documentation Agent** consolidates outputs into clear, human-readable docs.

---

## Minimal Agent Set (for Small-Scale Use)

If Codex / your setup supports only a few agents, prioritize:

1. `data-engineer-agent`  
2. `ml-training-agent`  
3. `app-agent`  
4. `docs-agent`

These four can still cover end-to-end functionality for the MVP.

