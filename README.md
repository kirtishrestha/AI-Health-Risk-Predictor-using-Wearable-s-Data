# 🩺 AI Health Risk Predictor  
### Wearable Data → PySpark ETL → Machine Learning → Risk Insights Dashboard

The **AI Health Risk Predictor** is a data-driven health analytics system that uses smartwatch data (Samsung Health), Kaggle datasets, and historical records to predict a user’s **health risk level** (Low / Moderate / High).  
It combines **PySpark ETL**, **AWS S3**, **machine learning**, and a **Streamlit dashboard** to support preventive healthcare.

This project was developed as part of the **Final Year BSIT Capstone**.

---

## 📌 Key Features

### ✔️ Wearable Data Integration  
- Supports Samsung Health CSV exports  
- Supports Kaggle datasets (heart disease, stress, sleep, diabetes)

### ✔️ Cloud-Based Data Lake  
- Amazon S3 for storage  
- Organized into **raw** and **processed** zones

### ✔️ PySpark ETL / ELT  
- Cleans, transforms, aggregates, and joins datasets  
- Generates daily/user-level feature tables  
- Outputs Parquet/CSV files for ML

### ✔️ Machine Learning  
- Predicts health risk using classical ML models  
- Uses heart rate, sleep, steps, SpO₂, BMI, etc.  
- Model saved as **pickle/joblib**

### ✔️ Streamlit Dashboard  
- Upload smartwatch CSV  
- Real-time risk prediction  
- HR/steps/sleep trend charts  
- Personalized recommendations  
- Simple UI for end users

---

## 🧰 Tech Stack

| Layer | Tools |
|------|-------|
| Programming | Python |
| Storage | AWS S3 |
| ETL/ELT | PySpark |
| Data Handling | CSV, Parquet, Pandas |
| ML | scikit-learn, Joblib/Pickle |
| Dashboard | Streamlit |
| Datasets | Samsung Health, Kaggle |

---

## 🏗️ System Architecture

             ┌─────────────────────────────┐
             │       Wearable Data         │
             │  Samsung Health CSV, Kaggle │
             └───────────────┬─────────────┘
                             │
                       (Ingestion)
                             │
                             ▼
             ┌─────────────────────────────┐
             │      AWS S3 - Raw Zone      │
             └───────────────┬─────────────┘
                             │
                        PySpark ETL
                             │
                             ▼
             ┌─────────────────────────────┐
             │   AWS S3 - Processed Zone   │
             │     features.parquet        │
             └───────────────┬─────────────┘
                             │
                       ML Training
                             │
                             ▼
             ┌─────────────────────────────┐
             │   model.pkl / model.joblib  │
             └───────────────┬─────────────┘
                             │
                     Streamlit App
                             ▼
               Risk Prediction Dashboard


---

## 📂 Project Structure

AI-Health-Risk-Predictor/
│
├── data/
│ ├── raw/
│ └── processed/
│
├── etl/
│ ├── spark_etl.py
│ └── utils/
│
├── ml/
│ ├── train.py
│ ├── evaluation.py
│ ├── model.pkl
│ └── model_meta.json
│
├── app/
│ ├── app.py
│ ├── components/
│ └── requirements.txt
│
├── notebooks/
│ ├── exploration.ipynb
│ └── modelling.ipynb
│
├── docs/
│ ├── architecture.md
│ ├── system_design.md
│ └── agents.md
│
└── README.md


---

##  Installation & Setup

### 1. Clone the Project
```bash
git clone https://github.com/<your-username>/AI-Health-Risk-Predictor.git
cd AI-Health-Risk-Predictor

##  Installation & Setup

python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows

## Install Dependencies

pip install -r app/requirements.txt

## Configure AWS (if using S3)

aws configure

## Run PySpark ETL

python etl/spark_etl.py

## Train ML Model

python ml/train.py

## Run Streamlit Dashboard

streamlit run app/app.py


## ML Pipeline

- Load processed feature dataset

- Label-encode risk categories

- Train ML models (Logistic Regression, Random Forest, etc.)

- Evaluate using test split

- Save best model as model.pkl

- Save metadata (model_meta.json)

## Dashboard Features

- Upload Samsung Health CSV

- Automatic preprocessing

- Predict risk level (Low / Moderate / High)

- Plot daily trends (HR, steps, sleep)

- Display model probabilities

- Give recommendations based on metrics

## Datasets Used
### Kaggle Sources (examples)

- Heart Disease Dataset

- Stress Level Dataset

- Sleep & Activity Dataset

### Samsung Health CSV Exports

- Activity

- Heart Rate

- Sleep


## Contributions

Pull requests, suggestions, and improvements are welcome.

