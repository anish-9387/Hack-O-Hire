# India Credit Risk Scoring System

A credit risk prediction system that scores 100K+ Indian borrowers using XGBoost, with a web UI for single predictions and automatic batch re-scoring on a schedule.

## How to Run (3 Steps)

### Prerequisites
- Python 3.10+
- 4GB+ RAM

### Step 1: Install dependencies

```bash
# Clone and enter the repo
git clone <repo-url>
cd Hack-O-Hire

# Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt

# Create output directories
mkdir -p data/processed src/model/artifacts
```

### Step 2: Train the model

```bash
python train.py
```

This reads `Datasets/india_credit_risk_dataset_100k.csv`, trains an XGBoost model, and saves it to `src/model/artifacts/`. Takes ~30 seconds.

You'll see output like:
```
  AUC:      0.9XXX
  F1:       0.8XXX
  Accuracy: 0.9XXX
  Top 10 Features:
    1. days_past_due_dpd
    2. cibil_bureau_score
    ...
```

To use LightGBM instead:
```bash
python train.py --model lightgbm
```

### Step 3: Start the app

```bash
uvicorn app:app --reload --port 8000
```

Open your browser:

| URL | What it does |
|-----|-------------|
| http://localhost:8000/ui | **Prediction form** — enter borrower details, get instant credit score |
| http://localhost:8000/results | **Batch results** — see all high-risk borrowers, trigger re-scoring |
| http://localhost:8000/docs | Auto-generated API documentation |

That's it. The app is running.

## What Each Page Does

### `/ui` — Single Borrower Prediction
A form where you fill in borrower details (age, CIBIL score, income, loan type, etc.) and click "Predict". Returns:
- **Credit Score** (0-900)
- **Risk Category** (LOW / MEDIUM / HIGH)
- **Default Probability** (0-100%)

No curl commands needed — just use the form.

### `/results` — Batch Results Dashboard
Shows the results of scoring **all 100K borrowers** at once:
- Summary cards: total borrowers, HIGH/MEDIUM/LOW counts
- Table of top 100 high-risk borrowers with their details
- "Re-run Batch Scoring" button to trigger it manually

### Automatic Re-scoring (every 2 days)
When the app is running, a background scheduler automatically re-scores all borrowers every 48 hours. No human intervention needed.

To change the interval, edit `BATCH_INTERVAL_HOURS` in `app.py` (line 37):
```python
BATCH_INTERVAL_HOURS = 48   # change to 24 for daily, 0.5 for 30-min testing
```

You can also trigger it manually anytime:
- Click "Re-run Batch Scoring" on the `/results` page, or
- `POST http://localhost:8000/run-batch`

## Project Structure

```
Hack-O-Hire/
│
├── Datasets/
│   └── india_credit_risk_dataset_100k.csv   # Your dataset (100K borrowers)
│
├── train.py              # Train the model (run once)
├── model.py              # XGBoost model wrapper (save/load/predict)
├── utils.py              # Data loading, preprocessing, encoding
├── app.py                # FastAPI server + web UI + scheduler
├── batch_score.py        # Batch scoring (scores all 100K borrowers)
│
├── src/model/artifacts/  # Saved model files (created by train.py)
├── data/processed/       # Batch results (created by batch_score.py)
│
├── src/dashboard/        # Plotly Dash dashboard (optional, port 8050)
├── src/utils/            # Alert engine, data generators (legacy)
├── notebooks/            # Jupyter notebooks for EDA
│
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

### What each file does

| File | Role |
|------|------|
| `train.py` | Loads dataset, encodes categoricals, trains XGBoost, saves model |
| `model.py` | `CreditScoringModel` class — wraps model + encoders for easy save/load/predict |
| `utils.py` | `load_dataset()`, `prepare_data()`, `features_from_dict()` + field metadata for the UI |
| `app.py` | FastAPI app with `/ui` (prediction form), `/results` (batch dashboard), `/predict` (API), scheduler |
| `batch_score.py` | Scores all borrowers, saves `batch_results.csv` + `high_risk.csv` |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/ui` | Prediction web form |
| GET | `/results` | Batch results dashboard |
| POST | `/predict` | Score a single borrower (JSON) |
| POST | `/run-batch` | Trigger batch re-scoring in background |
| GET | `/batch-summary` | Latest batch stats (JSON) |
| GET | `/health` | Service + scheduler status |
| GET | `/model-info` | Model metadata + performance |
| GET | `/docs` | Swagger API docs |

### Example API call

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "borrower_segment": "salaried_urban",
    "employment_type": "Salaried",
    "loan_type": "Personal",
    "state": "Maharashtra",
    "borrower_age": 35,
    "cibil_bureau_score": 650,
    "monthly_net_income_inr": 45000,
    "days_past_due_dpd": 30,
    "debt_to_income_ratio": 0.45,
    "loan_amount_requested_inr": 500000
  }'
```

Response:
```json
{
  "credit_score": 612.3,
  "default_probability": 0.3197,
  "risk_category": "LOW"
}
```

## Dataset

**File**: `Datasets/india_credit_risk_dataset_100k.csv` (100,000 Indian borrowers)

| Column | Type | Description |
|--------|------|-------------|
| borrower_id | ID | Unique identifier |
| borrower_segment | Categorical | salaried_urban, gig_worker, self_employed_msme, etc. |
| employment_type | Categorical | Salaried, Self-Employed, Gig/Freelance, Agricultural |
| loan_type | Categorical | Personal, Home, Vehicle, Business, Education, Gold, BNPL, MUDRA |
| state | Categorical | Indian state |
| is_urban | Binary | 0 or 1 |
| borrower_age | Numeric | Age in years |
| debt_to_income_ratio | Numeric | 0-1 |
| days_past_due_dpd | Numeric | Days payment is overdue |
| previous_loan_default_flag | Binary | Has defaulted before? |
| num_late_payments_12m | Numeric | Late payments in last 12 months |
| credit_utilisation_ratio | Numeric | 0-1 |
| cibil_bureau_score | Numeric | 300-900 |
| monthly_net_income_inr | Numeric | Monthly income in INR |
| payment_to_income_ratio_pti | Numeric | 0-1 |
| num_hard_enquiries_12m | Numeric | Hard credit pulls in 12 months |
| txn_frequency_monthly_avg | Numeric | Avg transactions per month |
| income_consistency_score | Numeric | 0-1 |
| revolving_credit_balance_inr | Numeric | Outstanding revolving balance |
| age_oldest_credit_account_months | Numeric | Credit history length |
| num_open_credit_lines | Numeric | Active credit accounts |
| loan_to_value_ratio_ltv | Numeric | 0-1 |
| digital_engagement_score | Numeric | 0-100 |
| utility_payment_score | Numeric | 0-100 |
| loan_amount_requested_inr | Numeric | Loan amount in INR |
| **credit_risk_label** | **Target** | **0 = No default, 1 = Default** |

`default_probability` and `credit_risk_score` are pre-computed columns excluded from training to prevent data leakage.

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| ML Model | XGBoost / LightGBM | Best for tabular data, fast training |
| API | FastAPI + Uvicorn | Async, auto docs, fast |
| Web UI | HTML/CSS/JS (served by FastAPI) | No frontend framework needed |
| Scheduler | APScheduler | Lightweight, runs inside the app |
| Dashboard (optional) | Plotly Dash | Interactive charts |

## Optional: Plotly Dashboard

The original Dash dashboard is still available for visual exploration:

```bash
python src/dashboard/dashboard_app.py
```

Access at http://localhost:8050 — shows risk distributions, scatter plots, and customer drill-down.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Model not loaded` when hitting `/predict` | Run `python train.py` first |
| `No batch results yet` on `/results` | Click "Run Batch Scoring Now" or run `python batch_score.py` |
| `APScheduler not installed` warning | Run `pip install apscheduler` |
| Port 8000 already in use | Use `uvicorn app:app --port 8001` |

---

**Hack-O-Hire Team - 2026**
