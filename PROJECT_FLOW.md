# 🔄 Detailed Project Flow - Financial Stress Prediction System

This document provides a comprehensive breakdown of the entire system architecture, data flow, and component interactions for creating wireframes and architecture diagrams.

---

## 📊 System Overview

**Purpose:** Real-time financial stress prediction system that analyzes banking transactions to identify customers at risk of financial distress.

**Core Components:**
1. Data Generation Pipeline
2. Feature Engineering Engine
3. ML Model Training & Serving
4. REST API Service
5. Real-time Stream Processing (Kafka)
6. Visualization Dashboard
7. Alert System

---

## 🎯 Complete Data Flow (End-to-End)

### Phase 1: Data Generation & Feature Engineering

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. TRANSACTION GENERATION (train_model_enhanced.py)             │
│                                                                  │
│ Input: Configuration Parameters                                 │
│   • n_customers = 1000                                          │
│   • start_date = '2022-01-01'                                   │
│   • months = 36                                                 │
│   • stress_pattern distribution                                │
│                                                                  │
│ Process:                                                         │
│   ┌──────────────────────────────────────────────┐             │
│   │ EnhancedTransactionGenerator()                │             │
│   │                                                │             │
│   │ For each customer:                             │             │
│   │  1. Assign stress pattern:                     │             │
│   │     - Normal (60%)                             │             │
│   │     - Early Stress (10%)                       │             │
│   │     - Late Stress (10%)                        │             │
│   │     - Gradual Stress (12%)                     │             │
│   │     - Recovered (8%)                           │             │
│   │                                                │             │
│   │  2. Generate monthly transactions:             │             │
│   │     - Salary (1x/month, ₹30K-₹150K)          │             │
│   │     - UPI (5-20x/month)                        │             │
│   │     - Bills (3-8x/month)                       │             │
│   │     - ATM (2-10x/month)                        │             │
│   │                                                │             │
│   │  3. Inject stress signals (if stressed):      │             │
│   │     - Salary delays (10-15 days)              │             │
│   │     - Balance drops (40-60%)                  │             │
│   │     - UPI to loan apps (20-35%)               │             │
│   │     - Failed autopay (3-8 failures)           │             │
│   │                                                │             │
│   │  4. Add 15% label noise (realism)            │             │
│   └──────────────────────────────────────────────┘             │
│                                                                  │
│ Output Files:                                                    │
│   • data/raw/enhanced_transactions.csv (2.5M rows)              │
│   • data/raw/enhanced_customer_profiles.csv (1000 rows)         │
│                                                                  │
│ Data Volume:                                                     │
│   • 2,567,791 transactions                                      │
│   • Size: ~85 MB (raw CSV)                                      │
│   • Timeline: 2022-01-02 to 2024-12-15                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. FEATURE ENGINEERING (FinancialFeatureEngine)                 │
│                                                                  │
│ Input: enhanced_transactions.csv                                │
│                                                                  │
│ Process:                                                         │
│   ┌──────────────────────────────────────────────┐             │
│   │ engineer_features()                            │             │
│   │                                                │             │
│   │ For each customer, calculate:                 │             │
│   │                                                │             │
│   │ A. Salary Features (6 features):              │             │
│   │    • days_since_last_salary                   │             │
│   │    • avg_salary_amount                        │             │
│   │    • salary_delay_trend                       │             │
│   │    • salary_variance_3m                       │             │
│   │    • months_with_salary                       │             │
│   │    • salary_regularity_score                  │             │
│   │                                                │             │
│   │ B. Balance Features (8 features):             │             │
│   │    • current_balance                          │             │
│   │    • min_balance_30d                          │             │
│   │    • balance_drop_4w                          │             │
│   │    • balance_trend                            │             │
│   │    • running_balance_30d_avg                  │             │
│   │    • balance_recovery_ability                 │             │
│   │    • balance_volatility                       │             │
│   │    • days_with_negative_balance               │             │
│   │                                                │             │
│   │ C. UPI Features (5 features):                 │             │
│   │    • upi_to_loan_apps_pct                     │             │
│   │    • upi_frequency                            │             │
│   │    • upi_amount_30d                           │             │
│   │    • upi_burst_count                          │             │
│   │    • upi_to_new_merchants_pct                 │             │
│   │                                                │             │
│   │ D. Payment Features (6 features):             │             │
│   │    • failed_autopay_count                     │             │
│   │    • bill_payment_delays                      │             │
│   │    • autopay_failure_trend                    │             │
│   │    • avg_bill_payment_day                     │             │
│   │    • payment_success_rate                     │             │
│   │    • late_payment_ratio                       │             │
│   │                                                │             │
│   │ E. ATM Features (4 features):                 │             │
│   │    • atm_withdrawal_frequency                 │             │
│   │    • atm_amount_variance                      │             │
│   │    • atm_large_withdrawal_pct                 │             │
│   │    • atm_weekend_withdrawals                  │             │
│   │                                                │             │
│   │ F. Velocity Features (4 features):            │             │
│   │    • transaction_count_7d                     │             │
│   │    • transaction_count_30d                    │             │
│   │    • transaction_amount_7d                    │             │
│   │    • transaction_amount_30d                   │             │
│   │                                                │             │
│   │ Time Window: Rolling 90-day aggregation       │             │
│   │ Observation Points: Every 7 days              │             │
│   └──────────────────────────────────────────────┘             │
│                                                                  │
│ Output:                                                          │
│   • data/processed/enhanced_features.csv                        │
│   • Shape: 5000 rows × 37 columns                               │
│   • Columns:                                                     │
│     - customer_id                                               │
│     - observation_date (timestamp)                              │
│     - 33 behavioral features                                    │
│     - is_stressed (label)                                       │
│     - stress_pattern (metadata)                                 │
│     - stress_start_month (metadata)                             │
│                                                                  │
│ Data Quality:                                                    │
│   • No missing values                                           │
│   • All features normalized/scaled                              │
│   • 15% label noise for realism                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Phase 2: Model Training & Validation

```
┌─────────────────────────────────────────────────────────────────┐
│ 3. DATA PREPARATION                                              │
│                                                                  │
│ Input: enhanced_features.csv (5000 samples)                     │
│                                                                  │
│ A. Load & Validate:                                             │
│    • Read CSV file                                              │
│    • Check for missing values                                   │
│    • Verify feature dtypes                                      │
│    • Confirm date range (2022-2024)                             │
│                                                                  │
│ B. Feature Selection:                                           │
│    • Drop non-predictive columns:                               │
│      - customer_id (identifier)                                 │
│      - observation_date (timestamp)                             │
│      - stress_pattern (metadata)                                │
│      - stress_start_month (metadata)                            │
│    • Keep 33 behavioral features                                │
│    • Extract target: is_stressed                                │
│                                                                  │
│ C. Time-Based Split (Option 3: Hybrid):                         │
│    ┌────────────────────────────────────────┐                  │
│    │ 2022-01  to  2024-06  →  TRAIN (70%)   │                  │
│    │ ├─ 3538 samples                        │                  │
│    │ └─ Stress rate: 27.6%                  │                  │
│    │                                         │                  │
│    │ 2024-07  to  2024-09  →  VAL (15%)     │                  │
│    │ ├─ 759 samples                         │                  │
│    │ └─ Stress rate: 30.4%                  │                  │
│    │                                         │                  │
│    │ 2024-10  to  2024-12  →  TEST (15%)    │                  │
│    │ ├─ 703 samples                         │                  │
│    │ └─ Stress rate: 26.5%                  │                  │
│    └────────────────────────────────────────┘                  │
│                                                                  │
│ Why Time-Based?                                                  │
│   • Prevents data leakage (no future info in training)         │
│   • Simulates real production (train past, predict future)     │
│   • Validates generalization across time                        │
│                                                                  │
│ D. Handle Class Imbalance (SMOTE):                              │
│    Before SMOTE:                                                │
│      Normal:   2560 samples (72.4%)                             │
│      Stressed:  978 samples (27.6%)                             │
│                                                                  │
│    After SMOTE:                                                 │
│      Normal:   2560 samples (50%)                               │
│      Stressed: 2560 samples (50%)                               │
│                                                                  │
│    Note: SMOTE applied ONLY to training set                     │
│          (validation & test remain imbalanced)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. MODEL TRAINING                                                │
│                                                                  │
│ A. XGBoost Configuration (Realistic Accuracy):                  │
│    ┌────────────────────────────────────────────┐              │
│    │ xgb_params = {                              │              │
│    │   'max_depth': 5,          # Shallow trees │              │
│    │   'learning_rate': 0.03,   # Slow learning │              │
│    │   'n_estimators': 300,     # More trees    │              │
│    │   'min_child_weight': 5,   # Pruning       │              │
│    │   'gamma': 0.2,            # Regularization│              │
│    │   'subsample': 0.8,        # Row sampling  │              │
│    │   'colsample_bytree': 0.8, # Col sampling  │              │
│    │   'reg_alpha': 0.3,        # L1 penalty    │              │
│    │   'reg_lambda': 1.5        # L2 penalty    │              │
│    │ }                                           │              │
│    └────────────────────────────────────────────┘              │
│                                                                  │
│    Training Process:                                            │
│      1. Fit on balanced training data (5120 samples)           │
│      2. Evaluate on validation set                             │
│      3. Evaluate on test set                                   │
│      4. Track metrics: AUC, F1, Accuracy                       │
│                                                                  │
│ B. LightGBM Configuration (same parameters):                    │
│    • Similar regularization strategy                            │
│    • Leaf-wise tree growth                                     │
│    • Same evaluation metrics                                   │
│                                                                  │
│ C. Model Selection:                                             │
│    • Compare XGBoost vs LightGBM on validation AUC              │
│    • Select best model                                          │
│    • Retrain on train+validation (optional)                    │
│                                                                  │
│ D. Performance Metrics:                                         │
│    ┌────────────────────────────────────────┐                  │
│    │ Test Set Results (Expected):           │                  │
│    │ ├─ Accuracy:  87-92% ✅                │                  │
│    │ ├─ AUC:       0.85-0.90 ✅             │                  │
│    │ ├─ Precision: 85-90% ✅                │                  │
│    │ ├─ Recall:    80-88% ✅                │                  │
│    │ └─ F1 Score:  83-89% ✅                │                  │
│    └────────────────────────────────────────┘                  │
│                                                                  │
│ E. Explainability (SHAP):                                       │
│    • Calculate SHAP values for test set                         │
│    • Identify top 10 risk factors                               │
│    • Generate feature importance rankings                       │
│    • Save explainer for production                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. MODEL ARTIFACTS                                               │
│                                                                  │
│ Save to: src/model/artifacts/                                   │
│                                                                  │
│ Files:                                                           │
│   ┌──────────────────────────────────────────────────┐         │
│   │ 1. financial_stress_model.joblib                  │         │
│   │    • Trained XGBoost/LightGBM model               │         │
│   │    • Size: ~2-5 MB                                │         │
│   │    • Format: Joblib pickle                        │         │
│   │                                                    │         │
│   │ 2. feature_columns.joblib                         │         │
│   │    • List of 33 feature names                     │         │
│   │    • Ensures correct feature order                │         │
│   │                                                    │         │
│   │ 3. shap_explainer.joblib                          │         │
│   │    • SHAP TreeExplainer object                    │         │
│   │    • Used for prediction explanations             │         │
│   │                                                    │         │
│   │ 4. model_metadata.json                            │         │
│   │    {                                               │         │
│   │      "model_type": "XGBoost",                     │         │
│   │      "test_accuracy": 0.8921,                     │         │
│   │      "test_auc": 0.8843,                          │         │
│   │      "test_f1": 0.8567,                           │         │
│   │      "n_features": 33,                            │         │
│   │      "training_date": "2024-12-15T08:30:00"       │         │
│   │    }                                               │         │
│   └──────────────────────────────────────────────────┘         │
│                                                                  │
│ Usage: Loaded by API & Dashboard for predictions               │
└─────────────────────────────────────────────────────────────────┘
```

---

### Phase 3: API Service (FastAPI)

```
┌─────────────────────────────────────────────────────────────────┐
│ 6. API SERVER (app/main.py)                                     │
│                                                                  │
│ Startup Process:                                                │
│   1. Load model artifacts                                       │
│   2. Initialize RealTimeScoringService                          │
│   3. Initialize FinancialFeatureEngine                           │
│   4. Start Uvicorn server (port 8000)                           │
│                                                                  │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │ API ENDPOINTS                                              │  │
│ │                                                            │  │
│ │ 1. POST /api/v1/score                                      │  │
│ │    Input: CustomerFeatures (33 features + customer_id)    │  │
│ │    Process:                                                │  │
│ │      ├─ Validate feature values                           │  │
│ │      ├─ Ensure correct feature order                      │  │
│ │      ├─ Predict risk score (0-1)                          │  │
│ │      ├─ Calculate SHAP values                             │  │
│ │      ├─ Determine risk level (Critical/High/Medium/Low)   │  │
│ │      └─ Return prediction + explanation                   │  │
│ │    Output:                                                 │  │
│ │      {                                                     │  │
│ │        "customer_id": 12345,                              │  │
│ │        "risk_score": 0.7823,                              │  │
│ │        "risk_level": "High",                              │  │
│ │        "prediction": "Stressed",                          │  │
│ │        "confidence": 0.7823,                              │  │
│ │        "top_risk_factors": [                              │  │
│ │          {"feature": "upi_to_loan_apps_pct",              │  │
│ │           "shap_value": 0.1523,                           │  │
│ │           "feature_value": 0.28},                         │  │
│ │          ...                                               │  │
│ │        ],                                                  │  │
│ │        "timestamp": "2024-12-15T10:30:00"                 │  │
│ │      }                                                     │  │
│ │                                                            │  │
│ │ 2. POST /api/v1/score/batch                               │  │
│ │    Input: List[CustomerFeatures]                          │  │
│ │    Process: Score multiple customers in parallel          │  │
│ │    Output: List of predictions                            │  │
│ │                                                            │  │
│ │ 3. POST /api/v1/score/from-transactions                   │  │
│ │    Input: customer_id + raw transactions                  │  │
│ │    Process:                                                │  │
│ │      ├─ Call FinancialFeatureEngine                       │  │
│ │      ├─ Calculate 33 features from transactions           │  │
│ │      ├─ Score using model                                 │  │
│ │      └─ Return prediction                                 │  │
│ │                                                            │  │
│ │ 4. GET /api/v1/score/example                              │  │
│ │    Returns: Pre-scored example customer                   │  │
│ │                                                            │  │
│ │ 5. GET /api/v1/model/metadata                             │  │
│ │    Returns: Model version, metrics, training date         │  │
│ │                                                            │  │
│ │ 6. GET /health                                             │  │
│ │    Returns: API health status                             │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│ Deployment:                                                      │
│   • Host: 0.0.0.0                                               │
│   • Port: 8000                                                  │
│   • Docs: http://localhost:8000/docs (Swagger UI)              │
│   • Workers: 4 (Uvicorn)                                        │
│   • Async: True (FastAPI async endpoints)                      │
└─────────────────────────────────────────────────────────────────┘
```

---

### Phase 4: Visualization Dashboard (Plotly Dash)

```
┌─────────────────────────────────────────────────────────────────┐
│ 7. DASHBOARD (src/dashboard/dashboard_app.py)                   │
│                                                                  │
│ Startup Process:                                                │
│   1. Load enhanced_features.csv (5000 samples)                  │
│   2. Load model artifacts                                       │
│   3. Calculate risk scores for all customers                    │
│   4. Generate SHAP values                                       │
│   5. Start Dash server (port 8050)                              │
│                                                                  │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │ DASHBOARD LAYOUT                                           │  │
│ │                                                            │  │
│ │ ┌─────────────────────────────────────────────────────┐   │  │
│ │ │ HEADER: Financial Stress Prediction Dashboard       │   │  │
│ │ └─────────────────────────────────────────────────────┘   │  │
│ │                                                            │  │
│ │ ┌─────────────────────────────────────────────────────┐   │  │
│ │ │ FILTERS & CONTROLS                                   │   │  │
│ │ │ ├─ Risk Level: [All|Critical|High|Medium|Low]        │   │  │
│ │ │ └─ Refresh Button                                    │   │  │
│ │ └─────────────────────────────────────────────────────┘   │  │
│ │                                                            │  │
│ │ ┌──────────────┬──────────────┬──────────────┐           │  │
│ │ │ Summary Card │ Summary Card │ Summary Card │           │  │
│ │ │ Total        │ Critical     │ High Risk    │           │  │
│ │ │ Customers    │ Risk (>0.8)  │ (0.6-0.8)    │           │  │
│ │ │ 5000         │ 450          │ 780          │           │  │
│ │ └──────────────┴──────────────┴──────────────┘           │  │
│ │                                                            │  │
│ │ ┌─────────────────────────────────────────────────────┐   │  │
│ │ │ RISK DISTRIBUTION HISTOGRAM                          │   │  │
│ │ │ X-axis: Risk Score (0-1)                             │   │  │
│ │ │ Y-axis: Number of Customers                          │   │  │
│ │ │ Color: Risk Level (Red/Orange/Yellow/Green)          │   │  │
│ │ └─────────────────────────────────────────────────────┘   │  │
│ │                                                            │  │
│ │ ┌─────────────────────────────────────────────────────┐   │  │
│ │ │ TOP 20 AT-RISK CUSTOMERS TABLE                       │   │  │
│ │ │ ┌──────────┬────────────┬──────────────┬─────────┐  │   │  │
│ │ │ │ Customer │ Risk Score │ Risk Level   │ Actions │  │   │  │
│ │ │ ├──────────┼────────────┼──────────────┼─────────┤  │   │  │
│ │ │ │ CUST_123 │ 0.89       │ Critical 🔴  │ [View]  │  │   │  │
│ │ │ │ CUST_456 │ 0.85       │ Critical 🔴  │ [View]  │  │   │  │
│ │ │ │ CUST_789 │ 0.78       │ High 🟠      │ [View]  │  │   │  │
│ │ │ └──────────┴────────────┴──────────────┴─────────┘  │   │  │
│ │ │ Features: Sortable columns, pagination, export CSV   │   │  │
│ │ └─────────────────────────────────────────────────────┘   │  │
│ │                                                            │  │
│ │ ┌─────────────────────────────────────────────────────┐   │  │
│ │ │ INDIVIDUAL CUSTOMER ANALYSIS                         │   │  │
│ │ │ Select Customer: [Dropdown]                          │   │  │
│ │ │                                                       │   │  │
│ │ │ SHAP Waterfall Plot:                                 │   │  │
│ │ │ ┌───────────────────────────────────────────────┐   │   │  │
│ │ │ │ Base Risk: 0.30                               │   │   │  │
│ │ │ │ ├─ upi_to_loan_apps_pct (+0.15) ▶ 0.45       │   │   │  │
│ │ │ │ ├─ balance_drop_4w (+0.13) ▶ 0.58            │   │   │  │
│ │ │ │ ├─ salary_delay_trend (+0.09) ▶ 0.67         │   │   │  │
│ │ │ │ ├─ running_balance_30d_avg (-0.05) ▶ 0.62    │   │   │  │
│ │ │ │ └─ ... other features ... ▶ Final: 0.78      │   │   │  │
│ │ │ └───────────────────────────────────────────────┘   │   │  │
│ │ │                                                       │   │  │
│ │ │ Recommended Actions:                                 │   │  │
│ │ │ • Immediate intervention required                    │   │  │
│ │ │ • Contact relationship manager                       │   │  │
│ │ │ • Offer debt consolidation counseling               │   │  │
│ │ └─────────────────────────────────────────────────────┘   │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│ Interactivity:                                                  │
│   • Click customer → Show SHAP analysis                         │
│   • Filter by risk level → Update all charts                    │
│   • Refresh → Reload data from CSV                              │
│   • Export → Download at-risk customers CSV                     │
│                                                                  │
│ Deployment:                                                      │
│   • Host: 0.0.0.0                                               │
│   • Port: 8050                                                  │
│   • Access: http://localhost:8050                               │
└─────────────────────────────────────────────────────────────────┘
```

---

### Phase 5: Real-time Stream Processing (Optional - Kafka)

```
┌─────────────────────────────────────────────────────────────────┐
│ 8. KAFKA INFRASTRUCTURE                                          │
│                                                                  │
│ Docker Compose Setup:                                           │
│   • Zookeeper (port 2181) - Coordination                        │
│   • Kafka Broker (port 9092) - Message broker                   │
│   • Topic: "transactions" (partitions: 3, replication: 1)       │
│                                                                  │
│ ┌──────────────────────────────────────────────────┐           │
│ │ PRODUCER (src/ingestion/kafka_producer.py)        │           │
│ │                                                    │           │
│ │ Process:                                           │           │
│ │   1. Connect to Kafka (localhost:9092)            │           │
│ │   2. Generate synthetic transactions:             │           │
│ │      • Rate: 5-10 transactions/second             │           │
│ │      • Types: UPI, Salary, Bills, ATM             │           │
│ │      • Random customer selection                  │           │
│ │   3. Serialize to JSON                            │           │
│ │   4. Publish to "transactions" topic              │           │
│ │                                                    │           │
│ │ Message Format:                                   │           │
│ │   {                                                │           │
│ │     "customer_id": 12345,                         │           │
│ │     "timestamp": "2024-12-15T10:30:00",           │           │
│ │     "transaction_type": "upi_debit",              │           │
│ │     "amount": -5000,                              │           │
│ │     "category": "loan_apps",                      │           │
│ │     "merchant": "MoneyTap",                       │           │
│ │     "description": "UPI payment"                  │           │
│ │   }                                                │           │
│ └──────────────────────────────────────────────────┘           │
│                         │                                        │
│                         │ Kafka Topic: "transactions"            │
│                         │ (in-memory queue)                      │
│                         ▼                                        │
│ ┌──────────────────────────────────────────────────┐           │
│ │ CONSUMER (src/ingestion/kafka_consumer.py)        │           │
│ │                                                    │           │
│ │ Process:                                           │           │
│ │   1. Subscribe to "transactions" topic            │           │
│ │   2. Poll for new messages (batch: 100)           │           │
│ │   3. Group by customer_id                         │           │
│ │   4. Maintain in-memory transaction buffer:       │           │
│ │      • Per customer: Last 90 days of transactions │           │
│ │      • Size: ~1000 transactions per customer      │           │
│ │   5. On each new transaction:                     │           │
│ │      ├─ Add to customer buffer                    │           │
│ │      ├─ Check if 90-day window complete           │           │
│ │      ├─ If yes:                                    │           │
│ │      │  ├─ Call FeatureEngine                     │           │
│ │      │  ├─ Calculate 33 features                  │           │
│ │      │  ├─ Call ScoringService                    │           │
│ │      │  ├─ Get risk score                         │           │
│ │      │  ├─ Check threshold (>0.75)                │           │
│ │      │  └─ Trigger alert if high risk             │           │
│ │      └─ Continue                                   │           │
│ │                                                    │           │
│ │ Latency: <100ms per transaction                   │           │
│ │ Throughput: 100+ transactions/sec                 │           │
│ └──────────────────────────────────────────────────┘           │
│                         │                                        │
│                         ▼                                        │
│ ┌──────────────────────────────────────────────────┐           │
│ │ ALERT ENGINE (src/utils/alert_engine.py)          │           │
│ │                                                    │           │
│ │ Triggered when: risk_score > threshold            │           │
│ │                                                    │           │
│ │ Risk Levels:                                       │           │
│ │   • Critical (>0.8): Immediate intervention       │           │
│ │   • High (0.6-0.8): Proactive outreach            │           │
│ │   • Medium (0.4-0.6): Monitoring                  │           │
│ │   • Low (<0.4): Normal                            │           │
│ │                                                    │           │
│ │ Alert Channels:                                   │           │
│ │   ✅ Log File: logs/alerts/alert_YYYY-MM-DD.log   │           │
│ │   ✅ JSON File: One per alert                     │           │
│ │   📧 Email: (configurable, default: OFF)          │           │
│ │   📱 SMS: (configurable, default: OFF)            │           │
│ │                                                    │           │
│ │ Alert Content:                                    │           │
│ │   {                                                │           │
│ │     "alert_id": "ALT_20241215_103000_12345",      │           │
│ │     "customer_id": 12345,                         │           │
│ │     "risk_score": 0.8234,                         │           │
│ │     "risk_level": "Critical",                     │           │
│ │     "timestamp": "2024-12-15T10:30:00",           │           │
│ │     "top_risk_factors": [                         │           │
│ │       {"feature": "upi_to_loan_apps_pct",         │           │
│ │        "value": 0.35, "impact": 0.15},            │           │
│ │       ...                                          │           │
│ │     ],                                             │           │
│ │     "recommended_actions": [                      │           │
│ │       "Immediate relationship manager contact",   │           │
│ │       "Debt consolidation counseling",            │           │
│ │       "Financial stress assessment"               │           │
│ │     ]                                              │           │
│ │   }                                                │           │
│ └──────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ System Architecture Diagram (Text Representation)

```
┌───────────────────────────────────────────────────────────────────────┐
│                           USER INTERACTIONS                            │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐             │
│  │   Web App    │   │  Mobile App  │   │  Dashboard   │             │
│  │   (React)    │   │   (React     │   │  (Plotly     │             │
│  │              │   │    Native)   │   │   Dash)      │             │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘             │
│         │                  │                  │                       │
│         └──────────────────┼──────────────────┘                       │
│                            │                                           │
└────────────────────────────┼───────────────────────────────────────────┘
                             │ HTTP/REST
                             ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY LAYER                              │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │              FastAPI Application (port 8000)                     │ │
│  │  ┌──────────────────────────────────────────────────────────┐  │ │
│  │  │ Endpoints:                                                │  │ │
│  │  │  • POST /api/v1/score                                     │  │ │
│  │  │  • POST /api/v1/score/batch                              │  │ │
│  │  │  • POST /api/v1/score/from-transactions                  │  │ │
│  │  │  • GET  /api/v1/model/metadata                           │  │ │
│  │  │  • GET  /health                                           │  │ │
│  │  └──────────────────────────────────────────────────────────┘  │ │
│  │                                                                   │ │
│  │  Features:                                                        │ │
│  │  • Async request handling                                        │ │
│  │  • CORS enabled                                                  │ │
│  │  • Auto-generated OpenAPI docs                                   │ │
│  │  • Request validation (Pydantic)                                 │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                        │
└────────────────────────────┬───────────────────────────────────────────┘
                             │
                             ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         BUSINESS LOGIC LAYER                           │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ RealTimeScoringService (src/scoring/scoring_service.py)         │ │
│  │  • Load model artifacts                                          │ │
│  │  • Validate features                                             │ │
│  │  • Generate predictions                                          │ │
│  │  • Calculate SHAP explanations                                   │ │
│  │  • Determine risk levels                                         │ │
│  └──────────────────────────┬───────────────────────────────────────┘ │
│                             │                                          │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ FinancialFeatureEngine (src/features/feature_engineering.py)    │ │
│  │  • Aggregate transactions                                        │ │
│  │  • Calculate 33 behavioral features                              │ │
│  │  • Handle time windows                                           │ │
│  │  • Feature validation                                            │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                        │
└────────────────────────────┬───────────────────────────────────────────┘
                             │
                             ▼
┌───────────────────────────────────────────────────────────────────────┐
│                           MODEL LAYER                                  │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ ML Model (XGBoost/LightGBM)                                      │ │
│  │  • Trained on 5000 samples                                       │ │
│  │  • 33 input features                                             │ │
│  │  • Binary classification (Stressed/Normal)                       │ │
│  │  • Performance: 87-92% accuracy, 0.85-0.90 AUC                   │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ SHAP Explainer                                                    │ │
│  │  • TreeExplainer for gradient boosting                           │ │
│  │  • Calculates feature contributions                              │ │
│  │  • Generates waterfall plots                                     │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  Model Artifacts (src/model/artifacts/):                              │
│  • financial_stress_model.joblib (2-5 MB)                            │
│  • feature_columns.joblib                                            │
│  • shap_explainer.joblib                                             │
│  • model_metadata.json                                               │
│                                                                        │
└────────────────────────────┬───────────────────────────────────────────┘
                             │
                             ▼
┌───────────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                                    │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Processed Features (data/processed/)                             │ │
│  │  • enhanced_features.csv (5000 rows × 37 cols)                   │ │
│  │    - 1000 customers                                              │ │
│  │    - 5 observation points per customer                           │ │
│  │    - 33 behavioral features                                      │ │
│  │    - Timeline: 2022-01-02 to 2024-12-15                          │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Raw Transactions (data/raw/)                                     │ │
│  │  • enhanced_transactions.csv (2.5M rows)                         │ │
│  │    - Transaction types: UPI, Salary, Bills, ATM                  │ │
│  │    - Timeline: 36 months                                         │ │
│  │  • enhanced_customer_profiles.csv (1000 rows)                    │ │
│  │    - Customer metadata                                           │ │
│  │    - Stress patterns                                             │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                        │
└────────────────────────────┬───────────────────────────────────────────┘
                             │
                             ▼
┌───────────────────────────────────────────────────────────────────────┐
│                    STREAMING LAYER (Optional)                          │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────┐        ┌──────────────┐        ┌──────────────┐   │
│  │   Producer   │ ─────> │    Kafka     │ ─────> │   Consumer   │   │
│  │  (Simulate   │        │   Broker     │        │  (Feature    │   │
│  │ Transactions)│        │ Topic: txns  │        │  Engineer +  │   │
│  │              │        │              │        │   Scorer)    │   │
│  └──────────────┘        └──────────────┘        └──────┬───────┘   │
│                                                           │            │
│  Rate: 5-10 txns/sec      Partitions: 3              Latency: <100ms │
│                                                           │            │
│                                                           ▼            │
│                                                  ┌──────────────┐     │
│                                                  │    Alert     │     │
│                                                  │    Engine    │     │
│                                                  └──────────────┘     │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Lineage & Dependencies

### Current Data Files (Post-Cleanup)

```
data/
├── raw/
│   ├── enhanced_transactions.csv         [USED] ✅
│   │   • Generated by: train_model_enhanced.py
│   │   • Size: ~85 MB
│   │   • Rows: 2,567,791
│   │   • Used by: Notebook (fallback), FeatureEngine
│   │
│   └── enhanced_customer_profiles.csv    [USED] ✅
│       • Generated by: train_model_enhanced.py
│       • Size: ~96 KB
│       • Rows: 1000
│       • Contains: customer_id, stress_pattern, stress_start_month
│
└── processed/
    └── enhanced_features.csv              [USED] ✅
        • Generated by: train_model_enhanced.py
        • Size: ~1.9 MB
        • Rows: 5000
        • Columns: 37 (customer_id, observation_date, 33 features,
                       is_stressed, stress_pattern, stress_start_month)
        • Used by: Notebook (priority 1), Dashboard, Training
```

### Removed Files (No Longer Used)

```
❌ data/processed/engineered_features.csv     [DELETED]
   • Old features, replaced by enhanced_features.csv

❌ data/processed/X_train.csv, X_test.csv, etc. [DELETED]
   • Intermediate split files, not needed (model uses in-memory splits)

❌ data/processed/feature_importance.csv       [DELETED]
   • Not referenced anywhere

❌ data/raw/synthetic_transactions.csv         [DELETED]
   • Old generator output, replaced by enhanced_transactions.csv

❌ data/raw/customer_profiles.csv              [DELETED]
   • Not used
```

---

## 🔄 Request-Response Flow Examples

### Example 1: Single Customer Scoring (API)

```
Client Request:
POST http://localhost:8000/api/v1/score
{
  "customer_id": 12345,
  "days_since_last_salary": 45,
  "balance_drop_4w": 0.42,
  "upi_to_loan_apps_pct": 0.28,
  ... (30 more features)
}
     │
     ▼
┌────────────────────────────────┐
│ FastAPI validates request      │
│ (Pydantic model)               │
└────────┬───────────────────────┘
         │
         ▼
┌────────────────────────────────┐
│ RealTimeScoringService         │
│ • Loads model                  │
│ • Validates features           │
│ • Orders features correctly    │
└────────┬───────────────────────┘
         │
         ▼
┌────────────────────────────────┐
│ XGBoost Model predicts         │
│ risk_score = 0.7823            │
└────────┬───────────────────────┘
         │
         ▼
┌────────────────────────────────┐
│ SHAP Explainer calculates      │
│ feature contributions          │
│ • upi_to_loan_apps: +0.15      │
│ • balance_drop: +0.13          │
│ • salary_delay: +0.09          │
└────────┬───────────────────────┘
         │
         ▼
┌────────────────────────────────┐
│ Determine risk level           │
│ 0.7823 → "High Risk"           │
└────────┬───────────────────────┘
         │
         ▼
API Response:
{
  "customer_id": 12345,
  "risk_score": 0.7823,
  "risk_level": "High",
  "prediction": "Stressed",
  "top_risk_factors": [...],
  "timestamp": "2024-12-15T10:30:00"
}
```

### Example 2: Real-time Stream Processing (Kafka)

```
New Transaction Event:
{
  "customer_id": 12345,
  "timestamp": "2024-12-15T10:30:00",
  "transaction_type": "upi_debit",
  "amount": -5000,
  "category": "loan_apps",
  "merchant": "MoneyTap"
}
     │
     ▼ Published to Kafka
┌────────────────────────────────┐
│ Kafka Topic: "transactions"    │
│ (in-memory queue)              │
└────────┬───────────────────────┘
         │
         ▼ Consumed
┌────────────────────────────────┐
│ KafkaConsumer                  │
│ • Groups by customer_id        │
│ • Maintains 90-day buffer      │
│ • Buffer for 12345: 850 txns   │
└────────┬───────────────────────┘
         │
         ▼
┌────────────────────────────────┐
│ Check if 90-day window complete│
│ ✅ Yes, 850 transactions       │
└────────┬───────────────────────┘
         │
         ▼
┌────────────────────────────────┐
│ FinancialFeatureEngine         │
│ • Aggregates 850 transactions  │
│ • Calculates 33 features       │
│ • Execution time: 20ms         │
└────────┬───────────────────────┘
         │
         ▼
┌────────────────────────────────┐
│ RealTimeScoringService         │
│ • Scores customer              │
│ • risk_score = 0.8234          │
│ • Execution time: 10ms         │
└────────┬───────────────────────┘
         │
         ▼
┌────────────────────────────────┐
│ Check threshold                │
│ 0.8234 > 0.75? YES → Alert!    │
└────────┬───────────────────────┘
         │
         ▼
┌────────────────────────────────┐
│ AlertEngine                    │
│ • Writes to log file           │
│ • Saves alert JSON             │
│ • (Optional) Send email/SMS    │
└────────────────────────────────┘

Total Latency: ~50ms (end-to-end)
```

---

## 🎨 Wireframe Guidelines

### 1. Dashboard Main Screen

**Layout Structure:**
```
┌───────────────────────────────────────────────────────────┐
│ [Logo] Financial Stress Prediction Dashboard    [Logout]  │
├───────────────────────────────────────────────────────────┤
│ [Filter: All Customers ▼] [Date Range: Last 30 Days ▼]   │
│ [🔄 Refresh]                                              │
├─────────────┬─────────────┬─────────────┬───────────────┤
│   Total     │  Critical   │   High      │   Medium      │
│  Customers  │   Risk      │   Risk      │   Risk        │
│   5,000     │    450      │    780      │   1,200       │
│             │   (9%)      │   (15.6%)   │   (24%)       │
└─────────────┴─────────────┴─────────────┴───────────────┘
│                                                           │
│ ┌───────────────────────────────────────────────────┐   │
│ │      Risk Distribution Histogram                   │   │
│ │  [Bar chart with color-coded risk levels]         │   │
│ └───────────────────────────────────────────────────┘   │
│                                                           │
│ ┌───────────────────────────────────────────────────┐   │
│ │  Top 20 At-Risk Customers                         │   │
│ │  ┌──────┬──────┬───────┬────────┬──────────────┐ │   │
│ │  │ Rank │  ID  │ Score │ Level  │ Actions      │ │   │
│ │  ├──────┼──────┼───────┼────────┼──────────────┤ │   │
│ │  │  1   │ 1234 │ 0.89  │ 🔴 Crit│ [View][Alert]│ │   │
│ │  │  2   │ 5678 │ 0.85  │ 🔴 Crit│ [View][Alert]│ │   │
│ │  │ ...  │ ...  │ ...   │ ...    │ ...          │ │   │
│ │  └──────┴──────┴───────┴────────┴──────────────┘ │   │
│ │  [Export CSV] [← Prev] [Next →]                  │   │
│ └───────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────┘
```

### 2. Individual Customer Analysis

**Components:**
```
┌───────────────────────────────────────────────────────────┐
│ Customer Analysis: CUST_12345                 [← Back]    │
├───────────────────────────────────────────────────────────┤
│ ┌─────────────────┬───────────────────────────────────┐  │
│ │ Customer Info   │ Risk Assessment                   │  │
│ │ ID: CUST_12345  │ Score: 0.78 (High Risk)          │  │
│ │ Since: 2022-01  │ Confidence: 78%                  │  │
│ │ Pattern: Gradual│ Last Updated: 2024-12-15         │  │
│ └─────────────────┴───────────────────────────────────┘  │
│                                                           │
│ ┌───────────────────────────────────────────────────┐   │
│ │ SHAP Waterfall Plot                               │   │
│ │ Base Risk (0.30)                                  │   │
│ │ ├─ UPI to Loan Apps (+0.15) ──────▶              │   │
│ │ ├─ Balance Drop (+0.13) ────────▶                │   │
│ │ ├─ Salary Delay (+0.09) ──────▶                  │   │
│ │ ├─ Running Balance (-0.05) ◀──                   │   │
│ │ └─ Other Features (+0.16) ────▶                  │   │
│ │ Final Risk: 0.78                                  │   │
│ └───────────────────────────────────────────────────┘   │
│                                                           │
│ ┌───────────────────────────────────────────────────┐   │
│ │ Top Risk Factors                                  │   │
│ │ 1. UPI to Loan Apps: 28% (🔴 Critical)           │   │
│ │ 2. Balance Drop: 42% (🔴 Critical)               │   │
│ │ 3. Salary Delays: 12.5 days (🟠 High)            │   │
│ │ 4. Failed Autopay: 5 times (🟠 High)             │   │
│ │ 5. ATM Frequency: 8/month (🟡 Medium)            │   │
│ └───────────────────────────────────────────────────┘   │
│                                                           │
│ ┌───────────────────────────────────────────────────┐   │
│ │ Recommended Actions                               │   │
│ │ ☑ Immediate relationship manager contact          │   │
│ │ ☑ Offer debt consolidation counseling             │   │
│ │ ☑ Financial stress assessment appointment         │   │
│ │ ☑ Payment restructuring options                   │   │
│ │ [Send Alert] [Schedule Call] [View History]      │   │
│ └───────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────┘
```

---

## ⚙️ Configuration & Environment

### Environment Variables

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Model Configuration
MODEL_PATH=src/model/artifacts/financial_stress_model.joblib
FEATURE_COLUMNS_PATH=src/model/artifacts/feature_columns.joblib
SHAP_EXPLAINER_PATH=src/model/artifacts/shap_explainer.joblib

# Data Configuration
FEATURES_CSV=data/processed/enhanced_features.csv
TRANSACTIONS_CSV=data/raw/enhanced_transactions.csv

# Kafka Configuration (Optional)
KAFKA_ENABLED=false
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=transactions
KAFKA_GROUP_ID=financial-stress-consumers
KAFKA_AUTO_OFFSET_RESET=earliest

# Alert Configuration
ALERT_ENABLED=true
ALERT_LOG_ENABLED=true
ALERT_EMAIL_ENABLED=false
ALERT_SMS_ENABLED=false
ALERT_EMAIL_RECIPIENT=alerts@bank.com
ALERT_SMS_NUMBER=+1234567890

# Risk Thresholds
CRITICAL_THRESHOLD=0.8
HIGH_THRESHOLD=0.6
MEDIUM_THRESHOLD=0.4

# Dashboard Configuration
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8050
DASHBOARD_DEBUG=false
```

---

## 📝 Summary for Architecture Diagrams

### Component Breakdown

| Layer | Components | Responsibilities |
|-------|-----------|------------------|
| **Presentation** | Web UI, Mobile App, Dashboard | User interaction, visualization |
| **API Gateway** | FastAPI | Request routing, validation, authentication |
| **Business Logic** | ScoringService, FeatureEngine | Feature calculation, predictions |
| **Model** | XGBoost, SHAP | Risk scoring, explainability |
| **Data** | CSV files, Kafka | Persistent storage, streaming |
| **Alert** | AlertEngine | Notification delivery |

### Integration Points

1. **API ↔ Model**: Joblib serialization
2. **Dashboard ↔ Data**: Direct CSV read
3. **Kafka ↔ FeatureEngine**: JSON message passing
4. **Model ↔ SHAP**: TreeExplainer integration
5. **Alerts ↔ Logs**: File system writes

---

**This document provides all the details needed to create:**
- Architecture diagrams (C4 model, UML, system context)
- Wireframes (web/mobile/dashboard UI)
- Data flow diagrams
- Sequence diagrams
- Deployment diagrams
