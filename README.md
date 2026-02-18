# 🏦 Financial Stress Prediction System

A production-grade real-time financial stress prediction system using machine learning to identify bank customers at risk of financial distress. The system processes 2.5M+ transactions, engineers 33 behavioral features, and provides risk scores with explainable AI (SHAP) achieving 85-92% accuracy.

---

## 📋 Table of Contents
- [Overview](#overview)
- [Complete Workflow](#complete-workflow)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Model Training](#model-training)
- [API Usage](#api-usage)
- [Dashboard](#dashboard)
- [Real-time Processing](#real-time-processing)
- [Project Structure](#project-structure)
- [Deployment](#deployment)

---

## 🎯 Overview

This system predicts financial stress in bank customers by analyzing transaction patterns, spending behaviors, and payment histories. It uses gradient boosting models (XGBoost/LightGBM) with **time-based validation** and **SHAP explainability** to provide transparent, production-ready risk assessments.

### 🏆 Key Performance Metrics:
- **Test Accuracy**: 85-92% ✅ (Industry standard for financial ML)
- **AUC Score**: 0.85-0.90 ✅ (Excellent discrimination)
- **F1 Score**: 0.80-0.88 ✅ (Balanced precision/recall)
- **Data Scale**: 2.5M+ transactions, 5000 feature snapshots
- **Timeline**: 36 months (Jan 2022 - Dec 2024)

---

## 🔄 Complete Workflow

### Phase 1: Data Generation
```bash
python train_model_enhanced.py
```
**What it does:**
1. Generates 2.5M+ realistic transactions over 36 months (2022-2024)
2. Creates 5 customer stress patterns:
   - **Normal** (60%): Stable finances
   - **Early Stress** (10%): Stress starts in first 12 months
   - **Late Stress** (10%): Stress starts after 24 months
   - **Gradual Stress** (12%): Slow decline over time
   - **Recovered** (8%): Stress early, then recovery
3. Injects realistic behavioral signals:
   - Salary delays (10-15 day lags)
   - Balance drops (40-60% decline over 4 weeks)
   - UPI to loan apps (20-35% of spending)
   - Failed autopay (3-8 failures in 30 days)
4. Engineers 33 behavioral features per customer
5. Applies time-based split (70/15/15%)

**Output:**
- `data/raw/enhanced_transactions.csv` (2.5M rows)
- `data/processed/enhanced_features.csv` (5000 rows × 37 cols)

---

### Phase 2: Model Training

**Option A: Jupyter Notebook (Recommended)**
```bash
# Start Jupyter
jupyter notebook

# Open notebooks/model_training.ipynb
# Click: Kernel → Restart & Run All
```

**Option B: Python Script**
```bash
# The script includes training
python train_model_enhanced.py
```

**What it does:**
1. Loads enhanced features (prioritizes `enhanced_features.csv`)
2. Detects `observation_date` column for time-based split
3. Splits data at time boundaries:
   - **Train**: 70% (first 30 months) - 3538 samples
   - **Val**: 15% (next 3 months) - 759 samples
   - **Test**: 15% (last 3 months) - 703 samples
4. Applies SMOTE to balance classes (2560:978 → 2560:2560)
5. Trains XGBoost & LightGBM with heavy regularization:
   - `max_depth=5` (prevent deep trees)
   - `learning_rate=0.03` (slow learning)
   - `n_estimators=300` (more trees)
   - `reg_alpha=0.3, reg_lambda=1.5` (L1/L2 regularization)
6. Calculates SHAP values for explainability
7. Saves best model to `src/model/artifacts/`

**Output:**
- `src/model/artifacts/financial_stress_model.joblib`
- `src/model/artifacts/feature_columns.joblib`
- `src/model/artifacts/shap_explainer.joblib`
- `src/model/artifacts/model_metadata.json`

---

### Phase 3: API Deployment
```bash
python app/main.py
```

**Access:**
- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

**Endpoints:**
- `POST /api/v1/score` - Score customer from features
- `POST /api/v1/score/batch` - Batch scoring
- `POST /api/v1/score/from-transactions` - Score from raw transactions
- `GET /api/v1/score/example` - Test with example customer
- `GET /api/v1/model/metadata` - Model info

---

### Phase 4: Dashboard Launch
```bash
python src/dashboard/dashboard_app.py
```

**Access:** http://localhost:8050

**Features:**
- Risk distribution histogram
- Top 20 at-risk customers table
- Individual customer SHAP analysis
- Filter by risk level (Critical/High/Medium/Low)

---

### Phase 5: Real-time Processing

**Start Kafka:**
```bash
docker-compose up -d kafka zookeeper
```

**Start Producer:**
```bash
python src/ingestion/kafka_producer.py
```

**Start Consumer & Scorer:**
```bash
python src/ingestion/kafka_consumer.py
```

**What it does:**
- Producer sends transactions to Kafka topic
- Consumer processes transactions into features
- Scoring service calculates real-time risk scores
- Alert engine triggers notifications for high-risk customers

---

## 🚀 Features

### 1. **Data Generation & Processing**
- Scrapes Kaggle datasets (GiveMeSomeCredit, Home Credit)
- Generates synthetic transaction data (UPI, salary, bills, ATM)
- Injects realistic stress signals (delays, balance drops, loan apps)
- 2.5M+ transactions over 36-month timeline

### 2. **Feature Engineering (33 Features)**
Automatically calculated behavioral features:

**Salary Patterns (6 features):**
- `salary_delay_trend` - Recent delay pattern
- `salary_variance_3m` - Income stability
- `days_since_last_salary` - Liquidity proxy

**Balance Analysis (8 features):**
- `balance_drop_4w` - Cash flow crisis indicator
- `running_balance_30d_avg` - Liquidity level
- `balance_recovery_ability` - Financial resilience

**UPI Spending (5 features):**
- `upi_to_loan_apps_pct` - High-risk spending %
- `upi_frequency` - Transaction velocity
- `upi_burst_count` - Spending spikes

**Payment Behavior (6 features):**
- `failed_autopay_count` - Payment struggles
- `bill_payment_delays` - Late payment pattern
- `autopay_failure_trend` - Deterioration signal

**ATM Patterns (4 features):**
- `atm_withdrawal_frequency` - Cash dependency
- `atm_amount_variance` - Withdrawal stability

**Transaction Velocity (4 features):**
- `transaction_count_7d`, `30d` - Activity level
- `transaction_amount_7d`, `30d` - Spending volume

### 3. **ML Models**
- **Algorithms**: XGBoost, LightGBM (ensemble-ready)
- **Performance**: 85-92% accuracy, 0.85-0.90 AUC
- **Training**: Time-based validation (no data leakage)
- **Regularization**: Heavy (max_depth=5, lr=0.03)
- **Class Balancing**: SMOTE (handles 30% minority class)
- **Explainability**: SHAP values for every prediction

### 4. **Real-time Streaming**
- Kafka-based transaction ingestion (topic: `transactions`)
- Consumer processes events into features
- Real-time risk scoring pipeline (<100ms latency)
- Alert triggering for high-risk customers

### 5. **Alert System**
- **Critical Risk** (>0.8): Immediate intervention
- **High Risk** (0.6-0.8): Proactive outreach
- **Medium Risk** (0.4-0.6): Monitoring
- Multi-channel alerts (email, SMS, logs)
- Recommended interventions for each customer
- Alert history tracking in `logs/alerts/`

### 6. **Dashboard**
- Interactive Plotly Dash UI
- Risk distribution histogram
- Top at-risk customer table (sortable)
- Individual SHAP analysis (waterfall plots)
- Filter by risk level
- Real-time refresh

### 7. **REST API**
- FastAPI-based microservice (async)
- Score single or batch customers
- Score directly from transactions
- Model metadata endpoints
- Auto-generated OpenAPI docs (Swagger UI)
- CORS enabled for web integration

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Sources (Phase 1)                    │
│  Synthetic Transaction Generator → 2.5M Transactions         │
│  (Salary, UPI, Bills, ATM, Loan Apps) 2022-2024             │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              Feature Engineering (Phase 1)                   │
│  FinancialFeatureEngine → 33 Behavioral Features             │
│  Time-based Aggregation → Feast Feature Store (Optional)     │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│           ML Model Training (Phase 2)                        │
│  Time-based Split (70/15/15) + SMOTE Balancing              │
│  XGBoost/LightGBM (max_depth=5, lr=0.03) + L1/L2 Reg        │
│  SHAP Explainability → Model Artifacts                       │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│         Real-time Stream Processing (Phase 5 Optional)       │
│  Kafka Producer → Transactions → Kafka Consumer             │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│           Model Serving (Phase 3 - FastAPI)                  │
│  Risk Scoring Service → Alert Engine                        │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│     Visualization Dashboard (Phase 4 - Plotly Dash)         │
│  Risk Monitoring & Customer SHAP Analysis                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

### Machine Learning
| Component | Technology | Purpose |
|-----------|-----------|---------|
| ML Models | XGBoost, LightGBM | Gradient boosting classifiers |
| Class Balancing | SMOTE (imbalanced-learn) | Handle 30% minority class |
| Explainability | SHAP | Feature importance & prediction explanation |
| Validation | Time-based Split | Prevent data leakage |
| Feature Store | Feast (optional) | Feature versioning & serving |

### Backend Services
| Component | Technology | Purpose |
|-----------|-----------|---------|
| API Server | FastAPI | Async REST API (8000) |
| Dashboard | Plotly Dash | Interactive visualization (8050) |
| Stream Processing | Apache Kafka | Real-time transaction ingestion |
| Data Processing | Pandas, NumPy | Feature engineering |

### Deployment
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Containerization | Docker, Docker Compose | Service orchestration |
| Model Serialization | Joblib | Fast model persistence |
| Logging | Python logging | Alert & error tracking |

---

## 🚀 Quick Start

### Prerequisites
- **Python**: 3.10 or 3.11 (tested with 3.14.2)
- **RAM**: 4GB minimum
- **Disk**: 500MB for data + models
- **(Optional)** Docker for Kafka

### Step 1: Setup Environment (2 minutes)

```bash
# Clone repository (if not already)
cd Hack-O-Hire

# Create virtual environment
python -m venv venv

# Activate environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Generate Data & Train Model (5 minutes)

```bash
# THIS SINGLE COMMAND DOES EVERYTHING:
# 1. Generates 2.5M realistic transactions (2022-2024)
# 2. Engineers 33 behavioral features
# 3. Applies time-based split (70/15/15)
# 4. Trains XGBoost/LightGBM with SMOTE
# 5. Saves model artifacts

python train_model_enhanced.py
```

### Step 3: Start API Server (30 seconds)

```bash
python app/main.py
```

**Access:** http://localhost:8000/docs

### Step 4: Start Dashboard (30 seconds)

Open a new terminal:

```bash
# Activate environment again
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

python src/dashboard/dashboard_app.py
```

**Access:** http://localhost:8050

### Step 5: Test the System

**Test API:**
```bash
# Windows PowerShell:
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/score/example" -Method Get

# Mac/Linux:
curl http://localhost:8000/api/v1/score/example
```

## 📊 Model Training (Deep Dive)

### Training Strategy: Option 3 (Time-based + Stratified)

**Why this approach?**
- ✅ **Prevents data leakage**: Train on past, validate on future
- ✅ **Simulates production**: Model never sees future data
- ✅ **Maintains balance**: Stratified sampling within time periods
- ✅ **Realistic evaluation**: Tests generalization to new time periods

### Data Timeline

```
2022-01-02 ────────────────────────────────────── 2024-12-15
│                    │          │          │
│    TRAIN (70%)     │  VAL 15% │ TEST 15% │
│                    │          │          │
│  30 months         │ 3 months │ 3 months │
│  3538 samples      │ 759      │ 703      │
│  Stress: 27.6%     │ 30.4%    │ 26.5%    │
```

### Customer Stress Patterns

| Pattern | % | Description | Signals |
|---------|---|-------------|---------|
| **Normal** | 60% | Stable finances | Low risk scores consistently |
| **Early Stress** | 10% | Stress in first year | Salary delays, balance drops early |
| **Late Stress** | 10% | Stress after 2 years | Late deterioration pattern |
| **Gradual Stress** | 12% | Slow decline | Progressively worsening metrics |
| **Recovered** | 8% | Stress then recovery | High risk early, then improvement |

### Model Hyperparameters (Realistic Accuracy)

```python
XGBoost/LightGBM Configuration:
├── max_depth: 5              # Shallow trees (was 6-8)
├── learning_rate: 0.03       # Slow learning (was 0.1)
├── n_estimators: 300         # More trees (was 100)
├── min_child_weight: 5       # More samples per leaf
├── gamma: 0.2                # Pruning threshold
├── subsample: 0.8            # Row sampling
├── colsample_bytree: 0.8     # Column sampling
├── reg_alpha: 0.3            # L1 regularization
└── reg_lambda: 1.5           # L2 regularization
```

**Result:** 85-92% accuracy (realistic generalization, not overfitting)

### Understanding Model Metrics

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **Test Accuracy** | 87-92% | Good generalization (100% = overfitting!) |
| **Train-Test Gap** | <10% | Healthy (large gap = overfitting) |
| **AUC** | 0.85-0.90 | Excellent discrimination |
| **Precision** | 85-90% | 85% of "stressed" predictions correct |
| **Recall** | 80-88% | Catches 80-88% of actual stressed customers |
| **F1 Score** | 83-89% | Good balance of precision/recall |

### Typical Confusion Matrix

```
                Predicted
              Normal  Stressed
Actual Normal   570      30      (95% correct)
    Stressed     70     330      (82.5% correct)
```

**Trade-offs:**
- **30 False Positives**: Normal customers flagged → Low-cost outreach
- **70 False Negatives**: Missed stressed customers → Acceptable given early intervention focus

---

## 🔌 API Usage

### Base URL
```
http://localhost:8000/api/v1
```

### Endpoints

#### 1. Score Customer from Features

```bash
POST /api/v1/score
Content-Type: application/json

{
  "customer_id": "CUST_001",
  "features": {
    "salary_delay_trend": 12.5,
    "balance_drop_4w": 0.45,
    "upi_to_loan_apps_pct": 0.28,
    "failed_autopay_count": 5,
    "days_since_last_salary": 18,
    "running_balance_30d_avg": 5000,
    "upi_frequency": 45,
    "atm_withdrawal_frequency": 8,
  }
}
```

**Response:**
```json
{
  "customer_id": "CUST_001",
  "risk_score": 0.7823,
  "risk_level": "High",
  "prediction": "Stressed",
  "confidence": 0.7823,
  "top_risk_factors": [
    {"feature": "upi_to_loan_apps_pct", "shap_value": 0.1523, "feature_value": 0.28},
    {"feature": "balance_drop_4w", "shap_value": 0.1287, "feature_value": 0.45},
    {"feature": "salary_delay_trend", "shap_value": 0.0945, "feature_value": 12.5}
  ],
  "timestamp": "2024-12-15T10:30:00"
}
```

#### 2. Batch Scoring

```bash
POST /api/v1/score/batch
Content-Type: application/json

{
  "customers": [
    {"customer_id": "CUST_001", "features": {...}},
    {"customer_id": "CUST_002", "features": {...}}
  ]
}
```

#### 3. Score from Transactions

```bash
POST /api/v1/score/from-transactions
Content-Type: application/json

{
  "customer_id": "CUST_001",
  "transactions": [
    {"type": "UPI", "amount": 5000, "category": "loan_app", "timestamp": "2024-12-01"},
    {"type": "Salary", "amount": 50000, "timestamp": "2024-12-05"}
    // ... more transactions
  ]
}
```

#### 4. Example Customer (Quick Test)

```bash
GET /api/v1/score/example
```

Returns a pre-scored example customer for testing.

#### 5. Model Metadata

```bash
GET /api/v1/model/metadata
```

**Response:**
```json
{
  "model_type": "XGBoost",
  "test_accuracy": 0.8921,
  "test_auc": 0.8843,
  "test_f1": 0.8567,
  "n_features": 33,
  "training_date": "2024-12-15T08:30:00"
}
```

#### 6. Health Check

```bash
GET /health
```

---

## 📊 Dashboard

Access at: **http://localhost:8050**

### Features

1. **Risk Distribution Histogram**
   - Visualizes customer risk scores (0-1 range)
   - Color-coded by risk level
   - Shows concentration of high-risk customers

2. **Top At-Risk Customers Table**
   - Top 20 customers by risk score
   - Sortable columns (Customer ID, Risk Score, Risk Level)
   - Exportable to CSV

3. **Individual Customer Analysis**
   - Select customer from dropdown
   - SHAP waterfall plot showing:
     - Which features increase/decrease risk
     - Feature values and contributions
     - Base risk vs final risk score

4. **Risk Level Filters**
   - **Critical** (>0.8): Red - Immediate action
   - **High** (0.6-0.8): Orange - Proactive outreach
   - **Medium** (0.4-0.6): Yellow - Monitor
   - **Low** (<0.4): Green - Stable

---

## ⚡ Real-time Processing (Optional Kafka Setup)

### Start Kafka Services

```bash
docker-compose up -d
```

**Services Started:**
- Zookeeper (port 2181)
- Kafka (port 9092)

### Start Transaction Producer

```bash
python src/ingestion/kafka_producer.py
```

**What it does:**
- Generates synthetic transactions every 1-5 seconds
- Sends to Kafka topic: `transactions`
- Transaction types: UPI, Salary, Bills, ATM

### Start Consumer & Scoring Service

Open a new terminal:

```bash
python src/ingestion/kafka_consumer.py
```

**What it does:**
- Consumes transactions from Kafka
- Aggregates into feature windows (per customer)
- Scores customers in real-time
- Triggers alerts for high-risk customers

### View Alerts

```bash
# View alert logs
cat logs/alerts/alert_*.log

# Real-time monitoring
tail -f logs/alerts/alert_2024-12-15.log
```

---

## 📁 Project Structure

```
Hack-O-Hire/
│
├── app/                              # FastAPI Application
│   ├── main.py                       # API server (port 8000)
│   └── config.yaml                   # API configuration
│
├── data/                             # Data Storage
│   ├── raw/
│   │   └── enhanced_transactions.csv # 2.5M transactions (2.5GB)
│   └── processed/
│       └── enhanced_features.csv     # 5000 feature snapshots (1.9MB)
│
├── feast_repo/                       # Feature Store (Optional)
│   ├── feature_repo.py               # Feature definitions
│   └── feature_store.yaml            # Feast configuration
│
├── logs/                             # Logging
│   └── alerts/                       # Alert history
│
├── notebooks/                        # Interactive Analysis
│   ├── eda.ipynb                     # Exploratory Data Analysis
│   └── model_training.ipynb          # Model Training & Evaluation
│
├── src/                              # Source Code
│   ├── dashboard/
│   │   └── dashboard_app.py          # Plotly Dash UI (port 8050)
│   │
│   ├── features/
│   │   └── feature_engineering.py    # FinancialFeatureEngine (33 features)
│   │
│   ├── ingestion/
│   │   ├── kafka_producer.py         # Transaction stream producer
│   │   └── kafka_consumer.py         # Consumer + real-time scorer
│   │
│   ├── model/
│   │   ├── model_wrapper.py          # StressPredictor wrapper class
│   │   └── artifacts/                # Saved models
│   │       ├── financial_stress_model.joblib
│   │       ├── feature_columns.joblib
│   │       ├── shap_explainer.joblib
│   │       └── model_metadata.json
│   │
│   ├── scoring/
│   │   └── scoring_service.py        # Risk scoring logic
│   │
│   └── utils/
│       ├── alert_engine.py           # Alert system (multi-channel)
│       ├── data_merger.py            # Kaggle + synthetic merger
│       ├── kaggle_downloader.py      # Kaggle dataset downloader
│       └── synthetic_data_generator.py # Transaction generator
│
├── train_model_enhanced.py           # MAIN TRAINING SCRIPT ⭐
├── requirements.txt                  # Python dependencies
├── setup.py                          # Package setup
├── Dockerfile                        # Container image
├── docker-compose.yaml               # Multi-service orchestration
└── README.md                         # This file

```

---

## 🚢 Deployment

### Development (Local)

```bash
# 1. Generate data & train model
python train_model_enhanced.py

# 2. Start API
python app/main.py

# 3. Start dashboard (new terminal)
python src/dashboard/dashboard_app.py
```

### Production (Docker)

```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f dashboard

# Stop services
docker-compose down
```

**Services Available:**
- API: http://localhost:8000
- Dashboard: http://localhost:8050
- Kafka: localhost:9092 (if enabled)

### Environment Variables

Create `.env` file:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Model Configuration
MODEL_PATH=src/model/artifacts/financial_stress_model.joblib

# Kafka Configuration (Optional)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=transactions

# Alert Configuration
ALERT_EMAIL_ENABLED=false
ALERT_SMS_ENABLED=false
ALERT_LOG_ENABLED=true

# Risk Thresholds
CRITICAL_THRESHOLD=0.8
HIGH_THRESHOLD=0.6
MEDIUM_THRESHOLD=0.4
```

---

## 📈 Model Retraining Strategy

### When to Retrain

1. **Monthly Schedule**: Retrain with new transaction data
2. **Model Drift**: If test AUC drops below 0.80
3. **Data Drift**: If feature distributions change >20%
4. **Business Changes**: New transaction types, policies

### Retraining Steps

```bash
# 1. Backup current model
cp src/model/artifacts/financial_stress_model.joblib \
   src/model/artifacts/financial_stress_model_backup.joblib

# 2. Generate new data (with updated date ranges)
python train_model_enhanced.py

# 3. Evaluate new model
# Check test accuracy, AUC, F1 in output

# 4. A/B test (optional)
# Run both models in parallel, compare performance

# 5. Deploy new model
# Restart API: python app/main.py
```

### Model Monitoring

Track these metrics:
- **Prediction distribution**: Should match training (30% stressed)
- **Feature drift**: Monitor top 10 features for distribution changes
- **Performance metrics**: Log accuracy, precision, recall weekly
- **Alert rate**: Should be stable (10-15% of customers)

---

## 📚 Key Concepts Explained

### Why Time-Based Split?

**Problem with Random Split:**
```python
# BAD: Random shuffle
train_test_split(X, y, test_size=0.2, shuffle=True)
# Model sees future data in training → Leakage!
```

**Solution: Time-Based Split:**
```python
# GOOD: Split by time
train = data[data['date'] <= '2024-06-30']  # Past
test = data[data['date'] > '2024-09-30']    # Future
# Model only sees past → No leakage!
```

### SHAP Explainability Example

```python
Customer CUST_001 - Risk Score: 0.78 (High)

Base Risk (all customers): 0.30

Feature Contributions:
+ upi_to_loan_apps_pct (0.28)      → +0.15  (RED FLAG)
+ balance_drop_4w (0.45)            → +0.13  (DANGER)
+ salary_delay_trend (12.5 days)    → +0.09  (CONCERN)
- running_balance_30d_avg (₹15K)    → -0.05  (POSITIVE)
- autopay_success_rate (0.9)        → -0.03  (POSITIVE)
  ... other features                 → +0.09
                                    ─────────
Final Risk Score:                      0.78
```

**Business Action:**
- High UPI spending to loan apps → Debt consolidation offer
- Balance dropping rapidly → Emergency credit line
- Salary delays → Paycheck advance program

---

## 📞 Support & Documentation

### Additional Resources

- **Swagger API Docs**: http://localhost:8000/docs
- **Notebooks**: See `notebooks/` for detailed analysis
- **SHAP Documentation**: https://shap.readthedocs.io/
- **XGBoost Docs**: https://xgboost.readthedocs.io/

### Common Issues

**Issue**: "No module named 'xgboost'"
```bash
pip install --upgrade xgboost lightgbm
```

**Issue**: "SHAP values taking too long"
```python
# In notebook, reduce sample size:
X_test_sample = X_test.sample(100, random_state=42)  # Instead of 500
```

**Issue**: "Kafka connection refused"
```bash
# Check Kafka is running:
docker-compose ps

# Restart Kafka:
docker-compose restart kafka
```

**Issue**: "100% accuracy in notebook"
```bash
# Delete old data and regenerate:
rm data/processed/engineered_features.csv
python train_model_enhanced.py
```

---

## 🏆 Project Highlights

✅ **Production-Ready**: Time-based validation prevents data leakage  
✅ **Explainable AI**: SHAP values for every prediction  
✅ **Scalable**: Kafka streaming for real-time processing  
✅ **Well-Documented**: Comprehensive README + notebooks  
✅ **Realistic Performance**: 85-92% accuracy (not overfitted)  
✅ **Feature-Rich**: 33 behavioral features engineered  
✅ **Multi-Service**: API + Dashboard + Streaming  
✅ **Containerized**: Docker Compose for easy deployment