# RiskSense - Credit Risk Prediction & Financial Stress Detection

A full-stack credit risk management platform for the Indian lending market. It scores 100K+ borrowers using XGBoost/LightGBM, detects financial stress through transaction analysis, and provides dual portals for lenders (admin) and borrowers (user) with SHAP-powered explainability and cross-bank defaulter detection.

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS, Radix UI, Recharts, Framer Motion, Zustand |
| **Backend** | FastAPI, SQLAlchemy, PostgreSQL 16, APScheduler |
| **ML** | XGBoost, LightGBM, SHAP, Scikit-learn, SMOTEENN |
| **Auth** | JWT (HS256) + bcrypt |

## Features

**Admin Portal** — Portfolio dashboard, risk distribution analytics, customer management, model performance metrics, intervention management, audit logs, cross-bank defaulter registry

**User Portal** — Personal risk score & trends, transaction history, income/spending analytics, SHAP-based risk explanation, AI financial coach, what-if scenario simulator

**ML Pipeline** — 100K borrower dataset, 45+ engineered features (edge case handling), probability calibration, automatic batch re-scoring every 48 hours

**Cross-Bank Detection** — Privacy-preserving shared defaulter registry (PAN + phone hash), automatic risk score boosting on cross-bank defaults

## Quick Start

### Prerequisites
- Python 3.10+, Node 20+, PostgreSQL 16

### Backend

```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

python train.py                # Train model (~30s)
python load_db.py              # Load data into PostgreSQL
uvicorn app:app --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                    # http://localhost:3000 (proxies /api to :8000)
```

### Demo Credentials
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@demo.com | admin123 |
| User | user@demo.com | user123 |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | JWT login |
| POST | `/api/predict` | Score a single borrower |
| POST | `/api/run-batch` | Trigger batch re-scoring |
| GET | `/api/dashboard` | Portfolio overview |
| GET | `/api/users` | List users (filterable) |
| GET | `/api/risk-distribution` | Risk analytics |
| GET | `/api/cross-bank/defaults` | Cross-bank defaulter list |
| GET | `/api/model-info` | Model metadata & metrics |
| GET | `/docs` | Swagger API docs |

## Project Structure

```
Hack-O-Hire/
├── app.py                  # FastAPI server
├── api_bridge.py           # React frontend API bridge
├── train.py                # ML training pipeline
├── model.py                # XGBoost/LightGBM wrapper
├── edge_case_features.py   # 25+ edge case feature engineering
├── batch_score.py          # Batch scoring (100K borrowers)
├── cross_bank.py           # Cross-bank defaulter detection
├── db.py                   # PostgreSQL layer
├── load_db.py              # CSV to DB loader
├── Datasets/               # 100K borrower dataset
├── src/model/artifacts/    # Saved model files
├── data/processed/         # Batch results
└── frontend/               # React + TypeScript + Vite app
    └── src/pages/
        ├── admin/          # Admin portal (8 pages)
        └── user/           # User portal (6 pages)
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```
DATABASE_URL=postgresql://postgres:password@localhost:5432/risk_sense
JWT_SECRET=your-secret-key
BATCH_INTERVAL_HOURS=48
```

---

**Hack-O-Hire Team - 2026**
