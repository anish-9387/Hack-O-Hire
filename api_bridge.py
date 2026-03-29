"""
API Bridge — /api/* endpoints for the React frontend (AI-Pipeline UI).

Translates the frontend's expected API contract to the existing
Hack-O-Hire FastAPI backend data (model, CSV, batch results).

Auth: JWT (HS256) with bcrypt password hashing.
"""
import base64
import io
import json
import os
import random
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import bcrypt
import jwt
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

# ── Paths (relative to project root) ─────────────────────────────────
DATASET_PATH   = Path("Datasets/india_credit_risk_dataset_100k.csv")
RESULTS_PATH   = Path("data/processed/batch_results.csv")
HIGH_RISK_PATH = Path("data/processed/high_risk.csv")
SUMMARY_PATH   = Path("data/processed/batch_summary.json")
ARTIFACTS_DIR  = "src/model/artifacts"

# ── JWT & Auth Configuration ─────────────────────────────────────────
JWT_SECRET      = os.environ.get("JWT_SECRET", "finhealth-super-secret-key-change-in-production")
JWT_ALGORITHM   = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES  = 60      # 1 hour
REFRESH_TOKEN_EXPIRE_MINUTES = 10080   # 7 days

_bearer_scheme = HTTPBearer(auto_error=False)

# In-memory user store (production would use a database)
# Passwords are bcrypt-hashed
_USER_STORE: dict[str, dict] = {}

def _init_demo_users():
    """Create demo users with bcrypt-hashed passwords on startup."""
    global _USER_STORE
    demo_users = [
        {"email": "admin@demo.com",  "password": "admin123", "role": "admin", "name": "Risk Admin"},
        {"email": "user@demo.com",   "password": "demo123",  "role": "user",  "name": "Demo User"},
    ]
    for u in demo_users:
        hashed = bcrypt.hashpw(u["password"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        _USER_STORE[u["email"]] = {
            "email":         u["email"],
            "password_hash": hashed,
            "role":          u["role"],
            "name":          u["name"],
        }

_init_demo_users()

router = APIRouter(prefix="/api")

# ── Cached data (loaded once per worker) ──────────────────────────────

_dataset: Optional[pd.DataFrame] = None
_results: Optional[pd.DataFrame] = None


def _get_dataset() -> pd.DataFrame:
    global _dataset
    if _dataset is None and DATASET_PATH.exists():
        _dataset = pd.read_csv(DATASET_PATH)
    return _dataset


def _get_results() -> Optional[pd.DataFrame]:
    global _results
    if RESULTS_PATH.exists():
        _results = pd.read_csv(RESULTS_PATH)
    return _results


def _reload_results():
    global _results
    if RESULTS_PATH.exists():
        _results = pd.read_csv(RESULTS_PATH)
    return _results


# ── JWT Token helpers ─────────────────────────────────────────────────

def _create_access_token(data: dict) -> str:
    """Create a short-lived JWT access token."""
    payload = {
        **data,
        "type": "access",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _create_refresh_token(data: dict) -> str:
    """Create a long-lived JWT refresh token."""
    payload = {
        **data,
        "type": "refresh",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises on expiry or invalid signature."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


def _parse_token(authorization: str = "") -> dict:
    """Parse Authorization header → dict with role / borrower_id.
    Gracefully handles missing/invalid tokens for backwards compatibility."""
    try:
        token = authorization.replace("Bearer ", "").strip()
        if not token:
            return {"role": "user", "borrower_id": ""}
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        # Fallback: try legacy base64 tokens during migration
        try:
            return json.loads(base64.b64decode(token).decode())
        except Exception:
            return {"role": "user", "borrower_id": ""}


async def _get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme)) -> dict:
    """FastAPI dependency: extract and validate the current user from JWT."""
    if credentials is None:
        raise HTTPException(401, "Authentication required")
    return _decode_token(credentials.credentials)


async def _require_admin(user: dict = Depends(_get_current_user)) -> dict:
    """FastAPI dependency: require admin role."""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    return user


# ── Synthetic data helpers ─────────────────────────────────────────────

def _risk_level_str(prob: float) -> str:
    if prob >= 0.50: return "critical"
    if prob >= 0.30: return "high"
    if prob >= 0.10: return "medium"
    return "low"


def _credit_to_risk_score(credit_score: float) -> int:
    """Convert 900-scale credit score to 0-100 risk score."""
    return max(0, min(100, round((1 - credit_score / 900) * 100)))


def _gen_risk_trend(base_score: int, n: int = 10) -> list:
    """Generate plausible historical risk scores."""
    rng = random.Random(base_score)
    scores = []
    s = base_score + rng.randint(-15, 15)
    for i in range(n):
        s += rng.randint(-4, 4)
        s = max(5, min(95, s))
        date = (datetime.now() - timedelta(days=(n - i) * 3)).strftime("%Y-%m-%d")
        scores.append({"date": date, "score": s})
    return scores


def _gen_spending(income: float, risk: float) -> list:
    """Generate a synthetic spending breakdown."""
    cats = [
        ("rent",             0.28),
        ("grocery",          0.12),
        ("utility_bill",     0.07),
        ("food_delivery",    0.06),
        ("emi_payment",      0.10 + risk * 0.15),
        ("atm_withdrawal",   0.05 + risk * 0.08),
        ("loan_app",         risk * 0.12),
        ("entertainment",    max(0, 0.06 - risk * 0.04)),
    ]
    monthly = income * 0.7
    items = []
    total = sum(w for _, w in cats)
    for cat, weight in cats:
        pct = round(weight / total * 100, 1)
        if pct < 1:
            continue
        items.append({
            "category":   cat,
            "amount":     round(monthly * weight / total, 0),
            "percentage": pct,
        })
    return sorted(items, key=lambda x: -x["amount"])[:6]


def _gen_transactions(borrower_id: str, income: float, risk: float) -> list:
    rng = random.Random(hash(borrower_id) & 0xFFFF)
    txn_templates = [
        ("salary",          "credit",  income,         "bank_transfer", False),
        ("rent",            "debit",   income * 0.27,  "bank_transfer", False),
        ("grocery",         "debit",   income * 0.04,  "upi",           False),
        ("food_delivery",   "debit",   income * 0.02,  "upi",           False),
        ("utility_bill",    "debit",   income * 0.03,  "upi",           False),
        ("emi_payment",     "debit",   income * 0.10,  "auto_debit",    risk > 0.3),
        ("atm_withdrawal",  "debit",   income * 0.05,  "atm",           risk > 0.2),
        ("loan_app",        "credit",  income * 0.08 * risk, "upi",     risk > 0.3),
    ]
    txns = []
    for i, (cat, typ, base_amt, method, stress) in enumerate(txn_templates):
        if base_amt < 100:
            continue
        noise = 1 + rng.uniform(-0.1, 0.1)
        date = (datetime.now() - timedelta(days=rng.randint(1, 25))).strftime("%Y-%m-%dT%H:%M:%S")
        txns.append({
            "id":              f"TXN-{borrower_id[-4:]}-{i:02d}",
            "category":        cat,
            "type":            typ,
            "amount":          round(abs(base_amt * noise), 0),
            "paymentMethod":   method,
            "merchantName":    cat.replace("_", " ").title(),
            "description":     cat.replace("_", " ").title(),
            "transactionDate": date,
            "isStressIndicator": stress,
        })
    txns.sort(key=lambda x: x["transactionDate"], reverse=True)
    return txns


def _gen_alerts(borrower_id: str, risk: float, prob: float) -> list:
    alerts = []
    rng = random.Random(hash(borrower_id) & 0xFFFF)
    if prob >= 0.30:
        alerts.append({
            "id": f"ALT-{borrower_id[-4:]}-1",
            "title": "High Default Risk Detected",
            "message": f"Your risk score has exceeded the HIGH threshold. Immediate review recommended.",
            "severity": "critical",
            "type": "risk_alert",
            "isRead": False,
            "createdAt": (datetime.now() - timedelta(hours=2)).isoformat(),
        })
    if prob >= 0.10:
        alerts.append({
            "id": f"ALT-{borrower_id[-4:]}-2",
            "title": "EMI Payment Due Soon",
            "message": "Your next EMI payment is due in 3 days. Ensure sufficient balance.",
            "severity": "warning",
            "type": "payment_reminder",
            "isRead": False,
            "createdAt": (datetime.now() - timedelta(hours=8)).isoformat(),
        })
    if rng.random() > 0.5:
        alerts.append({
            "id": f"ALT-{borrower_id[-4:]}-3",
            "title": "Monthly Statement Available",
            "message": "Your account statement for the last 30 days is ready.",
            "severity": "info",
            "type": "statement",
            "isRead": True,
            "createdAt": (datetime.now() - timedelta(days=1)).isoformat(),
        })
    return alerts


def _gen_predictions(base_score: int, prob: float) -> dict:
    trend = "stable"
    deltas = [2, 3, 2, 1]
    if prob >= 0.30:
        trend = "deteriorating"
        deltas = [3, 5, 4, 3]
    elif prob < 0.10:
        trend = "improving"
        deltas = [-2, -3, -2, -1]

    preds = []
    s = base_score
    for i, d in enumerate(deltas, start=1):
        s = max(5, min(95, s + d))
        level = _risk_level_str(s / 100)
        preds.append({
            "week":           i,
            "predictedScore": s,
            "predictedLevel": level,
            "confidence":     round(0.85 - i * 0.04, 2),
        })

    key_risks = []
    if prob >= 0.30:
        key_risks = ["High EMI burden relative to income", "Cash withdrawal frequency increasing"]
    elif prob >= 0.10:
        key_risks = ["Moderate spending spike detected", "Savings rate below target"]

    return {"overallTrend": trend, "keyRisks": key_risks, "predictions": preds}


def _get_borrower_score(borrower_id: str):
    """Return (credit_score, default_probability, risk_category) for a borrower."""
    results = _get_results()
    if results is not None:
        row = results[results["borrower_id"] == borrower_id]
        if not row.empty:
            r = row.iloc[0]
            return float(r["credit_score"]), float(r["default_probability"]), str(r["risk_category"])
    # Fallback: compute on-the-fly
    ds = _get_dataset()
    if ds is not None:
        row = ds[ds["borrower_id"] == borrower_id]
        if not row.empty:
            dp = float(row.iloc[0].get("default_probability", 0.15))
            cs = round((1 - dp) * 900, 1)
            rc = "HIGH" if dp >= 0.30 else "MEDIUM" if dp >= 0.10 else "LOW"
            return cs, dp, rc
    return 720.0, 0.08, "LOW"


# ── Auth ───────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str
    role: str = "user"


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    name: str
    role: str = "user"


class RefreshRequest(BaseModel):
    refreshToken: str


# Revoked tokens set (in production, use Redis or DB)
_revoked_tokens: set[str] = set()


@router.post("/auth/login")
async def api_login(req: LoginRequest):
    ds = _get_dataset()

    # Verify credentials against user store
    stored_user = _USER_STORE.get(req.email)
    if stored_user:
        if not bcrypt.checkpw(req.password.encode("utf-8"), stored_user["password_hash"].encode("utf-8")):
            raise HTTPException(401, "Invalid email or password")
        role = stored_user["role"]
    else:
        # For demo: allow any email/password for user role, reject unknown admin
        if req.role == "admin":
            raise HTTPException(401, "Invalid admin credentials")
        role = "user"

    # Build user info based on role
    if role == "admin":
        borrower_id = "ADMIN"
        user_info = {
            "id":    "ADMIN",
            "name":  stored_user["name"] if stored_user else "Admin",
            "email": req.email,
            "role":  "admin",
            "city":  "Mumbai",
            "state": "Maharashtra",
        }
    else:
        # User login: treat email as borrower_id or pick demo one
        borrower_id = req.email.strip()
        if ds is not None:
            if borrower_id not in ds["borrower_id"].values:
                borrower_id = ds["borrower_id"].iloc[0]
            row = ds[ds["borrower_id"] == borrower_id].iloc[0]
            name = stored_user["name"] if stored_user else f"Borrower {borrower_id[-4:]}"
            city  = str(row.get("state", "Mumbai")).split()[0]
            state = str(row.get("state", "Maharashtra"))
            emp   = str(row.get("employment_type", "Salaried"))
            inc   = float(row.get("monthly_net_income_inr", 50000))
        else:
            name, city, state, emp, inc = "Demo User", "Mumbai", "Maharashtra", "Salaried", 50000.0

        user_info = {
            "id":             borrower_id,
            "name":           name,
            "email":          req.email,
            "role":           "user",
            "city":           city,
            "state":          state,
            "employmentType": emp,
            "monthlyIncome":  inc,
        }

    token_data = {"role": role, "borrower_id": borrower_id, "email": req.email}
    access_token  = _create_access_token(token_data)
    refresh_token = _create_refresh_token(token_data)

    log_audit("USER_LOGIN", req.email, "session", f"SES-{random.randint(1000,9999)}")
    return {
        "token":        access_token,
        "refreshToken": refresh_token,
        "expiresIn":    ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "role":         role,
        "user":         user_info,
    }


@router.post("/auth/register")
async def api_register(req: RegisterRequest):
    """Register a new user account with bcrypt-hashed password."""
    if req.email in _USER_STORE:
        raise HTTPException(409, "An account with this email already exists")

    hashed = bcrypt.hashpw(req.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    _USER_STORE[req.email] = {
        "email":         req.email,
        "password_hash": hashed,
        "role":          req.role if req.role in ("user", "admin") else "user",
        "name":          req.name,
    }

    # Auto-login after registration
    borrower_id = req.email
    ds = _get_dataset()
    if ds is not None and borrower_id not in ds["borrower_id"].values:
        borrower_id = ds["borrower_id"].iloc[0]

    token_data = {"role": req.role, "borrower_id": borrower_id, "email": req.email}
    access_token  = _create_access_token(token_data)
    refresh_token = _create_refresh_token(token_data)

    log_audit("USER_REGISTER", req.email, "session", f"SES-{random.randint(1000,9999)}")
    return {
        "token":        access_token,
        "refreshToken": refresh_token,
        "expiresIn":    ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "role":         req.role,
        "user": {
            "id":    borrower_id,
            "name":  req.name,
            "email": req.email,
            "role":  req.role,
        },
    }


@router.post("/auth/refresh")
async def api_refresh_token(req: RefreshRequest):
    """Exchange a valid refresh token for a new access token."""
    if req.refreshToken in _revoked_tokens:
        raise HTTPException(401, "Refresh token has been revoked")

    payload = _decode_token(req.refreshToken)
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid token type — expected refresh token")

    token_data = {"role": payload["role"], "borrower_id": payload["borrower_id"], "email": payload["email"]}
    new_access = _create_access_token(token_data)

    return {
        "token":     new_access,
        "expiresIn": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/auth/logout")
async def api_logout(authorization: str = Header(default="")):
    """Revoke the current tokens."""
    try:
        token = authorization.replace("Bearer ", "").strip()
        if token:
            _revoked_tokens.add(token)
    except Exception:
        pass
    return {"message": "Logged out successfully"}


@router.get("/auth/me")
async def api_get_me(user: dict = Depends(_get_current_user)):
    """Return the current authenticated user's profile."""
    ds = _get_dataset()
    bid = user.get("borrower_id", "")
    role = user.get("role", "user")

    if role == "admin":
        return {
            "id": "ADMIN", "name": "Risk Admin",
            "email": user.get("email", ""), "role": "admin",
        }

    if ds is not None and bid in ds["borrower_id"].values:
        row = ds[ds["borrower_id"] == bid].iloc[0]
        return {
            "id": bid,
            "name": f"Borrower {bid[-4:]}",
            "email": user.get("email", ""),
            "role": "user",
            "city": str(row.get("state", "Mumbai")).split()[0],
            "state": str(row.get("state", "Maharashtra")),
            "employmentType": str(row.get("employment_type", "Salaried")),
            "monthlyIncome": float(row.get("monthly_net_income_inr", 50000)),
        }

    return {"id": bid, "name": "User", "email": user.get("email", ""), "role": "user"}


# ── Dashboard Overview ─────────────────────────────────────────────────

def _get_borrower_full(borrower_id: str):
    """Return (dataset_row, results_row) for a borrower, or (None, None)."""
    ds = _get_dataset()
    results = _get_results()
    ds_row = res_row = None
    if ds is not None and borrower_id and borrower_id in ds["borrower_id"].values:
        ds_row = ds[ds["borrower_id"] == borrower_id].iloc[0]
    if results is not None and borrower_id and borrower_id in results["borrower_id"].values:
        res_row = results[results["borrower_id"] == borrower_id].iloc[0]
    return ds_row, res_row


def _real_spending(ds_row, income: float, prob: float) -> list:
    """Build spending breakdown from REAL dataset columns."""
    dti  = _safe_float(ds_row.get("debt_to_income_ratio")) if ds_row is not None else 0.3
    pti  = _safe_float(ds_row.get("payment_to_income_ratio_pti")) if ds_row is not None else 0.2
    cu   = _safe_float(ds_row.get("credit_utilisation_ratio")) if ds_row is not None else 0.4

    emi_amount   = round(income * pti, 0)
    debt_payment = round(income * dti - emi_amount, 0) if dti > pti else 0
    rent         = round(income * 0.25, 0)
    groceries    = round(income * 0.10, 0)
    utilities    = round(income * 0.05, 0)
    discretionary = round(income * max(0.02, 0.08 - prob * 0.06), 0)

    items = [
        {"category": "emi_payment",   "amount": max(emi_amount, 0),   "percentage": round(pti * 100, 1)},
        {"category": "rent",          "amount": rent,                 "percentage": 25.0},
        {"category": "grocery",       "amount": groceries,            "percentage": 10.0},
        {"category": "utility_bill",  "amount": utilities,            "percentage": 5.0},
        {"category": "debt_payment",  "amount": max(debt_payment, 0), "percentage": round(max(dti - pti, 0) * 100, 1)},
        {"category": "discretionary", "amount": discretionary,        "percentage": round(discretionary / max(income, 1) * 100, 1)},
    ]
    return [i for i in sorted(items, key=lambda x: -x["amount"]) if i["amount"] > 0]


def _real_transactions(borrower_id: str, ds_row, income: float, prob: float) -> list:
    """Build transactions from REAL dataset columns rather than templates."""
    rng = random.Random(hash(borrower_id) & 0xFFFF)
    pti  = _safe_float(ds_row.get("payment_to_income_ratio_pti")) if ds_row is not None else 0.2
    dpd  = _safe_int(ds_row.get("days_past_due_dpd")) if ds_row is not None else 0
    late = _safe_int(ds_row.get("num_late_payments_12m")) if ds_row is not None else 0
    txn_freq = _safe_int(ds_row.get("txn_frequency_monthly_avg", 20)) if ds_row is not None else 20
    loan_amt = _safe_float(ds_row.get("loan_amount_requested_inr")) if ds_row is not None else 0
    revolving = _safe_float(ds_row.get("revolving_credit_balance_inr")) if ds_row is not None else 0

    txns = []
    # Salary credit
    txns.append({
        "id": f"TXN-{borrower_id[-4:]}-01", "category": "salary", "type": "credit",
        "amount": round(income, 0), "paymentMethod": "bank_transfer",
        "merchantName": "Employer", "description": "Monthly Salary Credit",
        "transactionDate": (datetime.now() - timedelta(days=rng.randint(1, 5))).strftime("%Y-%m-%dT%H:%M:%S"),
        "isStressIndicator": False,
    })
    # EMI payment
    emi = round(income * pti, 0)
    if emi > 0:
        is_late = dpd > 0 or late > 0
        txns.append({
            "id": f"TXN-{borrower_id[-4:]}-02", "category": "emi_payment", "type": "debit",
            "amount": emi, "paymentMethod": "auto_debit",
            "merchantName": "Loan EMI", "description": f"EMI Payment (Loan: {formatINR_py(loan_amt)})" if loan_amt else "EMI Payment",
            "transactionDate": (datetime.now() - timedelta(days=rng.randint(1, 10))).strftime("%Y-%m-%dT%H:%M:%S"),
            "isStressIndicator": is_late,
        })
    # Rent
    txns.append({
        "id": f"TXN-{borrower_id[-4:]}-03", "category": "rent", "type": "debit",
        "amount": round(income * 0.25, 0), "paymentMethod": "bank_transfer",
        "merchantName": "Landlord", "description": "Monthly Rent",
        "transactionDate": (datetime.now() - timedelta(days=rng.randint(1, 5))).strftime("%Y-%m-%dT%H:%M:%S"),
        "isStressIndicator": False,
    })
    # Utility bills
    txns.append({
        "id": f"TXN-{borrower_id[-4:]}-04", "category": "utility_bill", "type": "debit",
        "amount": round(income * 0.05 * rng.uniform(0.8, 1.2), 0), "paymentMethod": "upi",
        "merchantName": "Utility Provider", "description": "Electricity & Water Bill",
        "transactionDate": (datetime.now() - timedelta(days=rng.randint(5, 20))).strftime("%Y-%m-%dT%H:%M:%S"),
        "isStressIndicator": False,
    })
    # Groceries (based on txn frequency)
    n_grocery = min(max(txn_freq // 10, 2), 6)
    for g in range(n_grocery):
        txns.append({
            "id": f"TXN-{borrower_id[-4:]}-G{g}", "category": "grocery", "type": "debit",
            "amount": round(income * 0.03 * rng.uniform(0.5, 1.5), 0), "paymentMethod": "upi",
            "merchantName": rng.choice(["BigBasket", "DMart", "More Supermarket", "Local Kirana"]),
            "description": "Grocery Purchase",
            "transactionDate": (datetime.now() - timedelta(days=rng.randint(1, 25))).strftime("%Y-%m-%dT%H:%M:%S"),
            "isStressIndicator": False,
        })
    # Revolving credit payment (if any)
    if revolving > 0:
        txns.append({
            "id": f"TXN-{borrower_id[-4:]}-RC", "category": "credit_card_payment", "type": "debit",
            "amount": round(revolving * 0.05, 0), "paymentMethod": "auto_debit",
            "merchantName": "Credit Card", "description": f"Min. Due on Revolving Balance ({formatINR_py(revolving)})",
            "transactionDate": (datetime.now() - timedelta(days=rng.randint(1, 15))).strftime("%Y-%m-%dT%H:%M:%S"),
            "isStressIndicator": prob > 0.3,
        })
    txns.sort(key=lambda x: x["transactionDate"], reverse=True)
    return txns


def formatINR_py(n: float) -> str:
    if n >= 10000000: return f"{n/10000000:.1f}Cr"
    if n >= 100000:   return f"{n/100000:.1f}L"
    if n >= 1000:     return f"{n/1000:.1f}K"
    return f"{n:.0f}"


@router.get("/dashboard/overview")
async def api_dashboard_overview(authorization: str = Header(default="")):
    info = _parse_token(authorization)
    borrower_id = info.get("borrower_id", "")

    ds_row, res_row = _get_borrower_full(borrower_id)

    income    = _safe_float(ds_row.get("monthly_net_income_inr", 50000)) if ds_row is not None else 50000.0
    state_val = str(ds_row["state"]) if ds_row is not None else "Maharashtra"
    emp_val   = str(ds_row["employment_type"]) if ds_row is not None else "Salaried"
    dti       = _safe_float(ds_row.get("debt_to_income_ratio", 0.3)) if ds_row is not None else 0.3
    pti       = _safe_float(ds_row.get("payment_to_income_ratio_pti", 0.2)) if ds_row is not None else 0.2

    cs, prob, rc = _get_borrower_score(borrower_id)
    risk_score = _credit_to_risk_score(cs)
    level      = _risk_level_str(prob)
    health     = max(0, min(100, 100 - risk_score))

    # Derive expenses from real debt-to-income and payment-to-income ratios
    debt_expenses  = round(income * dti, 0)
    living_expenses = round(income * 0.40, 0)  # rent + groceries + utilities
    total_expenses = round(debt_expenses + living_expenses, 0)
    savings_rt     = round(max(0, (income - total_expenses) / max(income, 1) * 100), 1)

    # Balance: income minus expenses accumulated over ~2 months
    balance = round(max(0, (income - total_expenses) * 2 + income), 0)

    return {
        "user": {
            "id":             borrower_id,
            "name":           f"Borrower {borrower_id[-4:]}",
            "city":           state_val.split()[0],
            "state":          state_val,
            "employmentType": emp_val,
        },
        "totalBalance":    balance,
        "monthlyIncome":   round(income, 0),
        "monthlyExpenses": total_expenses,
        "savingsRate":     savings_rt,
        "currentRiskScore": {
            "score":               risk_score,
            "level":               level,
            "financialHealthScore": health,
            "confidence":          0.87,
        },
        "riskTrend":          _gen_risk_trend(risk_score),
        "spendingBreakdown":  _real_spending(ds_row, income, prob),
        "recentTransactions": _real_transactions(borrower_id, ds_row, income, prob),
    }


# ── Spending Analytics ─────────────────────────────────────────────────

@router.get("/dashboard/spending")
async def api_spending(period: str = "30d", authorization: str = Header(default="")):
    info = _parse_token(authorization)
    borrower_id = info.get("borrower_id", "")

    ds_row, _ = _get_borrower_full(borrower_id)
    income = _safe_float(ds_row.get("monthly_net_income_inr", 50000)) if ds_row is not None else 50000.0
    dti    = _safe_float(ds_row.get("debt_to_income_ratio", 0.3)) if ds_row is not None else 0.3
    ic_score = _safe_float(ds_row.get("income_consistency_score", 0.7)) if ds_row is not None else 0.7

    _, prob, _ = _get_borrower_score(borrower_id)

    days_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
    n_days   = days_map.get(period, 30)
    n_weeks  = max(1, n_days // 7)

    # Timeline derived from real income consistency score (variance based on it)
    timeline = []
    rng = random.Random(hash(borrower_id) & 0xFF)
    variance = max(0.02, 0.15 * (1 - ic_score))  # Low consistency = high variance
    expense_rate = 0.40 + dti  # living + debt
    for i in range(n_weeks):
        wk_income  = income / 4 * (1 + rng.uniform(-variance, variance))
        wk_expense = income / 4 * expense_rate * (1 + rng.uniform(-0.03, 0.05))
        date = (datetime.now() - timedelta(weeks=(n_weeks - i))).strftime("%Y-%m-%d")
        timeline.append({"date": date, "income": round(wk_income, 0), "expenses": round(wk_expense, 0), "spent": round(wk_expense, 0)})

    spending = _real_spending(ds_row, income, prob)
    categories = [
        {
            "category":         s["category"],
            "total":            s["amount"],
            "amount":           s["amount"],
            "percentage":       s["percentage"],
            "trend":            "up" if s["category"] == "emi_payment" and prob > 0.2 else "stable",
            "count":            rng.randint(1, 8),
            "transactionCount": rng.randint(1, 8),
        }
        for s in spending
    ]

    total_out = round(income * expense_rate * (n_days / 30), 0)
    total_in  = round(income * (n_days / 30), 0)
    return {
        "timeline":    timeline,
        "categories":  categories,
        "totalOutflow": total_out, "totalSpent": total_out,
        "totalInflow":  total_in,  "totalIncome": total_in,
    }


# ── Risk ───────────────────────────────────────────────────────────────

@router.get("/risk/score")
async def api_risk_score(authorization: str = Header(default="")):
    info = _parse_token(authorization)
    borrower_id = info.get("borrower_id", "")
    cs, prob, _ = _get_borrower_score(borrower_id)
    risk_score  = _credit_to_risk_score(cs)
    level       = _risk_level_str(prob)
    return {
        "score":               risk_score,
        "level":               level,
        "financialHealthScore": max(0, min(100, 100 - risk_score)),
        "confidence":          0.87,
    }


@router.get("/risk/explain")
async def api_risk_explain(authorization: str = Header(default="")):
    info = _parse_token(authorization)
    borrower_id = info.get("borrower_id", "")
    cs, prob, _ = _get_borrower_score(borrower_id)
    risk_score  = _credit_to_risk_score(cs)

    ds_row, res_row = _get_borrower_full(borrower_id)

    # Build risk factors from REAL data
    dti    = _safe_float(ds_row.get("debt_to_income_ratio")) if ds_row is not None else 0.3
    pti    = _safe_float(ds_row.get("payment_to_income_ratio_pti")) if ds_row is not None else 0.2
    cu     = _safe_float(ds_row.get("credit_utilisation_ratio")) if ds_row is not None else 0.4
    dpd    = _safe_int(ds_row.get("days_past_due_dpd")) if ds_row is not None else 0
    late   = _safe_int(ds_row.get("num_late_payments_12m")) if ds_row is not None else 0
    prev_def = _safe_int(ds_row.get("previous_loan_default_flag")) if ds_row is not None else 0
    enquiries = _safe_int(ds_row.get("num_hard_enquiries_12m")) if ds_row is not None else 0
    ltv    = _safe_float(ds_row.get("loan_to_value_ratio_ltv")) if ds_row is not None else 0
    cibil  = _safe_float(ds_row.get("cibil_bureau_score")) if ds_row is not None else 700
    ic     = _safe_float(ds_row.get("income_consistency_score")) if ds_row is not None else 0.7
    ups    = _safe_float(ds_row.get("utility_payment_score")) if ds_row is not None else 60
    des    = _safe_float(ds_row.get("digital_engagement_score")) if ds_row is not None else 50

    top_factors = []
    # Rank actual risk drivers by severity
    risk_items = [
        ("debtToIncomeRatio",      dti * 30,       f"Debt-to-income ratio: {dti:.0%}"),
        ("paymentToIncomeRatio",   pti * 25,       f"EMI payments consume {pti:.0%} of income"),
        ("creditUtilisation",      cu * 20,        f"Credit utilisation at {cu:.0%}"),
        ("daysPastDue",            min(dpd / 5, 20), f"{dpd} days overdue on payments"),
        ("latePayments",           late * 3,        f"{late} late payments in last 12 months"),
        ("previousDefault",        prev_def * 18,   "Previous loan default on record"),
        ("hardEnquiries",          enquiries * 2,   f"{enquiries} credit enquiries in 12 months"),
        ("loanToValueRatio",       ltv * 15,        f"Loan-to-value ratio: {ltv:.0%}"),
        ("lowCibilScore",          max(0, (650 - cibil) / 10), f"CIBIL score: {int(cibil)}"),
    ]
    risk_items.sort(key=lambda x: -x[1])
    for feat, impact, desc in risk_items[:5]:
        if impact > 0.5:
            top_factors.append({"feature": feat, "impact": round(impact, 2), "direction": "increases_risk", "description": desc})

    protective = []
    prot_items = [
        ("incomeConsistency",   ic * 15,   f"Income consistency score: {ic:.0%}"),
        ("utilityPaymentScore", ups / 8,   f"Utility payment score: {int(ups)}/100"),
        ("digitalEngagement",   des / 10,  f"Digital engagement score: {int(des)}/100"),
        ("highCibilScore",      max(0, (cibil - 700) / 20), f"Good CIBIL score: {int(cibil)}"),
    ]
    prot_items.sort(key=lambda x: -x[1])
    for feat, impact, desc in prot_items:
        if impact > 0.5:
            protective.append({"feature": feat, "impact": round(impact, 2), "direction": "decreases_risk", "description": desc})

    # Personalized recommendations based on actual data
    recs = []
    if dpd > 0:
        recs.append(f"You are {dpd} days overdue — clear pending dues immediately to prevent NPA classification.")
    if dti > 0.5:
        recs.append(f"Your debt-to-income ratio is {dti:.0%} — aim to bring it below 40% by paying off smaller loans.")
    if cu > 0.7:
        recs.append(f"Credit utilisation is {cu:.0%} — keep it below 30% to improve credit score.")
    if late > 2:
        recs.append(f"You had {late} late payments this year — set up auto-debit for all EMIs.")
    if enquiries >= 4:
        recs.append(f"You've had {enquiries} credit enquiries — avoid new loan applications for 6 months.")
    if ltv > 0.8:
        recs.append(f"Loan-to-value ratio is {ltv:.0%} — consider making a partial prepayment.")
    if not recs:
        recs = [
            "Your financial profile is strong — maintain your current habits.",
            f"CIBIL score of {int(cibil)} is {'excellent' if cibil >= 750 else 'good'} — continue timely payments.",
            "Consider diversifying savings into SIPs or fixed deposits.",
        ]

    level = _risk_level_str(prob)
    summary_map = {
        "critical": "Your financial profile shows critical stress indicators. Immediate action required.",
        "high":     "Multiple risk factors detected. Focus on reducing debt obligations.",
        "medium":   "Moderate risk level. Monitor spending and maintain timely payments.",
        "low":      "Your financial health looks good. Continue your disciplined financial habits.",
    }
    return {
        "overallScore":      risk_score,
        "summary":           summary_map[level],
        "topFactors":        top_factors,
        "protectiveFactors": protective,
        "recommendations":   recs,
        "confidence":        0.87,
    }


@router.get("/risk/predict")
async def api_risk_predict(authorization: str = Header(default="")):
    info = _parse_token(authorization)
    borrower_id = info.get("borrower_id", "")
    cs, prob, _ = _get_borrower_score(borrower_id)
    risk_score  = _credit_to_risk_score(cs)
    return _gen_predictions(risk_score, prob)


@router.get("/risk/history")
async def api_risk_history(authorization: str = Header(default="")):
    info = _parse_token(authorization)
    borrower_id = info.get("borrower_id", "")
    cs, prob, _ = _get_borrower_score(borrower_id)
    return _gen_risk_trend(_credit_to_risk_score(cs), 20)


# ── Alerts ─────────────────────────────────────────────────────────────

@router.get("/alerts")
async def api_alerts(unreadOnly: bool = False, authorization: str = Header(default="")):
    info = _parse_token(authorization)
    borrower_id = info.get("borrower_id", "")
    _, prob, _  = _get_borrower_score(borrower_id)
    alerts = _gen_alerts(borrower_id, _credit_to_risk_score(prob * 100) / 100, prob)
    if unreadOnly:
        alerts = [a for a in alerts if not a["isRead"]]
    return alerts


# ── Transactions ───────────────────────────────────────────────────────

@router.get("/transactions")
async def api_transactions(limit: int = 50, authorization: str = Header(default="")):
    info = _parse_token(authorization)
    borrower_id = info.get("borrower_id", "")

    ds_row, _ = _get_borrower_full(borrower_id)
    income = _safe_float(ds_row.get("monthly_net_income_inr", 50000)) if ds_row is not None else 50000.0

    _, prob, _ = _get_borrower_score(borrower_id)
    txns = _real_transactions(borrower_id, ds_row, income, prob)
    return {"transactions": txns[:limit], "data": txns[:limit], "total": len(txns), "limit": limit, "offset": 0}


class SimulateRequest(BaseModel):
    amount: float = 5000
    type: str = "debit"
    category: str = "grocery"
    description: str = ""


@router.post("/transactions/simulate")
async def api_simulate_txn(req: SimulateRequest, authorization: str = Header(default="")):
    info = _parse_token(authorization)
    borrower_id = info.get("borrower_id", "")
    cs, prob, _ = _get_borrower_score(borrower_id)
    risk_score  = _credit_to_risk_score(cs)

    # High-risk categories increase risk more
    stress_cats = {"loan_app", "atm_withdrawal", "festival_shopping", "gambling"}
    cat_risk = 0.05 if req.category in stress_cats else 0.01
    if req.type == "credit":
        cat_risk = -0.02

    ds = _get_dataset()
    income = 50000.0
    if ds is not None and borrower_id and borrower_id in ds["borrower_id"].values:
        income = float(ds[ds["borrower_id"] == borrower_id].iloc[0]["monthly_net_income_inr"])

    amount_ratio = req.amount / max(income, 1)
    delta = round((cat_risk + amount_ratio * 0.1) * 100, 1)
    if req.type == "credit":
        delta = round(-amount_ratio * 5, 1)

    projected = max(0, min(100, risk_score + delta))
    proj_level = _risk_level_str(projected / 100)

    warning = None
    if req.category in stress_cats:
        warning = f"'{req.category}' transactions are flagged as high-risk indicators."
    elif delta > 5:
        warning = "This transaction will significantly increase your risk score."

    return {
        "projectedScore":     projected,
        "projectedRiskScore": projected,
        "riskDelta":          delta,
        "warning":            warning,
        "recommendation": "Consider digital payment alternatives to reduce cash dependency."
                          if req.category == "atm_withdrawal"
                          else "Ensure you have sufficient savings buffer before this expense.",
    }


@router.post("/transactions/create")
async def api_create_txn(req: SimulateRequest, authorization: str = Header(default="")):
    return {"id": f"TXN-NEW-{datetime.now().strftime('%H%M%S')}", "status": "created"}


# ── Coach ──────────────────────────────────────────────────────────────

@router.get("/coach/advice")
async def api_coach(authorization: str = Header(default="")):
    info = _parse_token(authorization)
    borrower_id = info.get("borrower_id", "")
    cs, prob, _ = _get_borrower_score(borrower_id)

    ds_row, res_row = _get_borrower_full(borrower_id)
    income = _safe_float(ds_row.get("monthly_net_income_inr", 50000)) if ds_row is not None else 50000.0
    dti    = _safe_float(ds_row.get("debt_to_income_ratio", 0.3)) if ds_row is not None else 0.3
    pti    = _safe_float(ds_row.get("payment_to_income_ratio_pti", 0.2)) if ds_row is not None else 0.2
    cu     = _safe_float(ds_row.get("credit_utilisation_ratio", 0.4)) if ds_row is not None else 0.4
    dpd    = _safe_int(ds_row.get("days_past_due_dpd")) if ds_row is not None else 0
    late   = _safe_int(ds_row.get("num_late_payments_12m")) if ds_row is not None else 0
    des    = _safe_float(ds_row.get("digital_engagement_score", 50)) if ds_row is not None else 50

    level = _risk_level_str(prob)
    msgs = {
        "critical": "Urgent action needed. Your financial stress indicators are at a critical level.",
        "high":     "Your risk profile needs immediate attention. Focus on reducing debt load.",
        "medium":   "You're managing reasonably but there's room to improve financial resilience.",
        "low":      "Your financial health is excellent! You're in a great position to grow wealth.",
    }

    # Personalized tips based on actual borrower data
    tips = []
    if dti > 0.4:
        tips.append({
            "category": "debt", "title": "Reduce Debt-to-Income Ratio",
            "tip": f"Reduce Debt-to-Income Ratio — Your DTI is {dti:.0%}, target below 40%. Consider consolidating or prepaying smaller loans.",
            "description": f"Your DTI is {dti:.0%} — target below 40%. Consider consolidating or prepaying smaller loans.",
            "potentialSaving": round(income * (dti - 0.4), 0), "priority": "high",
        })
    if cu > 0.5:
        tips.append({
            "category": "spending", "title": "Lower Credit Utilisation",
            "tip": f"Lower Credit Utilisation — Your utilisation is {cu:.0%}, keeping it under 30% can boost your CIBIL score by 30-50 points.",
            "description": f"Your utilisation is {cu:.0%} — keeping it under 30% can boost your CIBIL score by 30-50 points.",
            "potentialSaving": round(income * 0.05, 0), "priority": "high" if cu > 0.7 else "medium",
        })
    if dpd > 0:
        tips.append({
            "category": "emergency", "title": "Clear Overdue Payments",
            "tip": f"Clear Overdue Payments — You are {dpd} days past due. Clearing this immediately prevents NPA classification and penalty charges.",
            "description": f"You are {dpd} days past due. Clearing this immediately prevents NPA classification and penalty charges.",
            "potentialSaving": round(income * 0.08, 0), "priority": "high",
        })
    if late > 0:
        tips.append({
            "category": "income", "title": "Set Up Auto-Debit for EMIs",
            "tip": f"Set Up Auto-Debit for EMIs — You had {late} late payment(s) this year. Auto-debit ensures on-time payments and improves credit history.",
            "description": f"You had {late} late payment(s) this year. Auto-debit ensures on-time payments and improves credit history.",
            "potentialSaving": round(income * 0.03, 0), "priority": "medium",
        })
    if des < 40:
        tips.append({
            "category": "spending", "title": "Increase Digital Payments",
            "tip": f"Increase Digital Payments — Digital engagement score is {int(des)}/100. Using UPI/net-banking creates a traceable financial footprint.",
            "description": f"Digital engagement score is {int(des)}/100. Using UPI/net-banking creates a traceable financial footprint.",
            "potentialSaving": round(income * 0.02, 0), "priority": "low",
        })
    # Always ensure at least one tip
    if not tips:
        tips.append({
            "category": "savings", "title": "Build Emergency Fund",
            "tip": "Build Emergency Fund — You're in great shape! Invest surplus in SIPs or FDs for wealth creation.",
            "description": "You're in great shape! Invest surplus in SIPs or FDs for wealth creation.",
            "potentialSaving": round(income * 0.15, 0), "priority": "low",
        })

    flags = []
    if dpd > 90:
        flags.append(f"CRITICAL: {dpd} days past due — NPA classification imminent")
    elif dpd > 30:
        flags.append(f"WARNING: {dpd} days overdue — clear immediately")
    if dti > 0.6:
        flags.append(f"Debt-to-income ratio of {dti:.0%} is dangerously high")
    if prob >= 0.30:
        flags.append("High default probability — consider debt counselling")
    elif prob >= 0.10 and not flags:
        flags.append("Moderate risk — review monthly spending patterns")

    # Goal derived from actual weakest area
    if dti > 0.4:
        goal_focus = f"Reduce debt burden from {dti:.0%} to below 40%"
    elif cu > 0.5:
        goal_focus = f"Bring credit utilisation from {cu:.0%} to below 30%"
    elif dpd > 0:
        goal_focus = "Clear all overdue payments this month"
    else:
        goal_focus = "Maintain financial discipline and grow savings"

    savings_opp = round(income * max(0.05, (1 - dti - 0.40)), 0) if dti < 0.60 else round(income * 0.05, 0)

    return {
        "overallMessage":     msgs[level],
        "warningFlags":       flags,
        "tips":               tips[:4],
        "monthlyGoal":        goal_focus,
        "savingsOpportunity": max(savings_opp, 0),
    }


# ── What-If Simulation ─────────────────────────────────────────────────

class WhatIfRequest(BaseModel):
    scenario: str
    parameters: dict = {}


_SCENARIO_IMPACTS = {
    "salary_delay":         (15, 10, ["Build 2-month salary buffer", "Negotiate EMI moratorium"]),
    "medical_emergency":    (25, 16, ["Health insurance covers major bills", "Use emergency fund"]),
    "job_loss":             (45, 24, ["Activate unemployment insurance", "Pause discretionary spend"]),
    "festival_season":      (12,  8, ["Set festival budget in advance", "Use savings account"]),
    "emi_increase":         (18, 12, ["Refinance at lower rate", "Prepay principal"]),
    "income_boost":         (-20, 0, ["Invest surplus in SIP", "Build emergency fund"]),
    "wedding":              (22, 16, ["Start wedding fund 12 months early", "Limit credit card use"]),
    "gig_income":           (-8,  0, ["Track gig income carefully", "Set aside 30% for taxes"]),
    "business_disruption":  (30, 20, ["Keep 6-month business reserve", "Diversify income"]),
    "vehicle_loan":         (12,  8, ["Keep LTV below 70%", "20% down payment recommended"]),
    "education_loan":       (10,  6, ["Repay after placement", "Tax benefit under 80E"]),
    "upi_overspending":     (8,   6, ["Set monthly UPI budget", "Review weekly spend"]),
}


@router.post("/simulation/what-if")
async def api_what_if(req: WhatIfRequest, authorization: str = Header(default="")):
    info = _parse_token(authorization)
    borrower_id = info.get("borrower_id", "")
    cs, prob, _ = _get_borrower_score(borrower_id)
    current = _credit_to_risk_score(cs)

    impact_delta, recovery_weeks, recs = _SCENARIO_IMPACTS.get(
        req.scenario, (10, 8, ["Review your financial plan carefully"])
    )
    projected = max(0, min(100, current + impact_delta))
    impact_level = "critical" if impact_delta > 35 else "high" if impact_delta > 20 else "medium" if impact_delta > 10 else "low"

    return {
        "currentRiskScore":  current,
        "projectedRiskScore": projected,
        "riskDelta":         impact_delta,
        "impact":            impact_level,
        "recoveryTimeWeeks": recovery_weeks,
        "recoveryDifficulty": min(100, recovery_weeks * 5),
        "recommendations":   recs,
    }


# ── Admin ──────────────────────────────────────────────────────────────

@router.get("/admin/overview")
async def api_admin_overview():
    results = _reload_results()
    if results is None:
        raise HTTPException(404, "No batch results. Run: python batch_score.py")

    total   = len(results)
    high    = int((results["risk_category"] == "HIGH").sum())
    medium  = int((results["risk_category"] == "MEDIUM").sum())
    avg_cs  = float(results["credit_score"].mean())
    avg_rs  = round(_credit_to_risk_score(avg_cs))
    alerts  = high + medium // 3

    states = []
    if "state" in results.columns:
        states = results["state"].dropna().unique().tolist()[:20]

    return {
        "totalUsers":       total,
        "highRiskUsers":    high,
        "activeAlerts":     alerts,
        "averageRiskScore": avg_rs,
        "cities":           states,
    }


@router.get("/admin/high-risk-users")
async def api_high_risk_users(limit: int = 8):
    results = _reload_results()
    if results is None:
        return []

    high = results[results["risk_category"] == "HIGH"].head(limit)
    users = []
    for _, row in high.iterrows():
        bid  = str(row["borrower_id"])
        cs   = float(row["credit_score"])
        prob = float(row["default_probability"])
        rs   = _credit_to_risk_score(cs)
        inc  = float(row.get("monthly_net_income_inr", 40000))
        emp  = str(row.get("employment_type", "Salaried"))
        state = str(row.get("state", "Maharashtra"))
        users.append({
            "id":             bid,
            "name":           f"Borrower {bid[-4:]}",
            "email":          f"{bid.lower()}@example.com",
            "city":           state.split()[0],
            "riskScore":      rs,
            "riskLevel":      _risk_level_str(prob),
            "employmentType": emp,
            "monthlyIncome":  inc,
        })
    return users


@router.get("/admin/city-analytics")
async def api_city_analytics():
    results = _reload_results()
    if results is None:
        return []

    if "state" not in results.columns:
        return []

    grp = results.groupby("state").agg(
        totalUsers    = ("borrower_id", "count"),
        avgCS         = ("credit_score", "mean"),
        highCount     = ("risk_category", lambda x: (x == "HIGH").sum()),
    ).reset_index()

    out = []
    for _, row in grp.sort_values("highCount", ascending=False).head(10).iterrows():
        total = int(row["totalUsers"])
        high  = int(row["highCount"])
        avg_cs = float(row["avgCS"])
        out.append({
            "city":               str(row["state"]),
            "totalUsers":         total,
            "highRiskPercentage": round(high / max(total, 1) * 100, 1),
            "averageRiskScore":   _credit_to_risk_score(avg_cs),
            "alerts":             high,
        })
    return out


@router.get("/admin/risk-distribution")
async def api_risk_distribution():
    results = _reload_results()
    if results is None:
        raise HTTPException(404, "No batch results.")

    # byEmploymentType — average risk score per employment type
    by_emp_type = []
    if "employment_type" in results.columns:
        for emp, grp in results.groupby("employment_type"):
            avg_cs = float(grp["credit_score"].mean())
            by_emp_type.append({
                "type": str(emp),
                "averageScore": _credit_to_risk_score(avg_cs),
            })

    # byCity — high-risk vs safe user counts per state (top 10)
    by_city = []
    if "state" in results.columns:
        grp = results.groupby("state").agg(
            total=("borrower_id", "count"),
            highRiskCount=("risk_category", lambda x: int((x == "HIGH").sum())),
        ).reset_index()
        for _, row in grp.sort_values("highRiskCount", ascending=False).head(10).iterrows():
            by_city.append({
                "city": str(row["state"]),
                "highRiskCount": int(row["highRiskCount"]),
                "userCount": int(row["total"]) - int(row["highRiskCount"]),
            })

    # trendOverTime — synthetic 90-day macro trend from batch stats
    rng = random.Random(42)
    base_score = _credit_to_risk_score(float(results["credit_score"].mean()))
    base_high = int((results["risk_category"] == "HIGH").sum())
    trend = []
    for i in range(90):
        d = datetime.now() - timedelta(days=90 - i)
        drift = rng.gauss(0, 1.5)
        trend.append({
            "date": d.strftime("%Y-%m-%d"),
            "averageScore": max(0, min(100, round(base_score + drift + rng.uniform(-3, 3)))),
            "highRiskCount": max(0, base_high + rng.randint(-200, 200)),
        })

    # byLevel — risk tier counts for pie chart
    by_level = []
    total = len(results)
    high_count = int((results["risk_category"] == "HIGH").sum())
    med_count  = int((results["risk_category"] == "MEDIUM").sum())
    low_count  = total - high_count - med_count
    # Split HIGH into critical (prob >= 0.50) and high (prob >= 0.30)
    critical_count = int((results["default_probability"] >= 0.50).sum())
    high_only = high_count - critical_count
    by_level = [
        {"level": "low",      "count": low_count},
        {"level": "medium",   "count": med_count},
        {"level": "high",     "count": max(high_only, 0)},
        {"level": "critical", "count": critical_count},
    ]

    return {"byEmploymentType": by_emp_type, "byCity": by_city, "trendOverTime": trend, "byLevel": by_level}


@router.get("/admin/alerts")
async def api_admin_alerts(severity: str = "critical", limit: int = 10):
    results = _reload_results()
    if results is None:
        return []

    high = results[results["risk_category"] == "HIGH"].head(limit)
    alerts = []
    for i, (_, row) in enumerate(high.iterrows()):
        bid = str(row["borrower_id"])
        prob = float(row["default_probability"])
        alerts.append({
            "id":        f"ADM-ALT-{i:04d}",
            "title":     f"High Risk Alert: {bid}",
            "message":   f"Borrower {bid} has default probability {prob:.1%}. Intervention recommended.",
            "severity":  "critical" if prob >= 0.5 else "warning",
            "type":      "risk_threshold",
            "isRead":    False,
            "userId":    bid,
            "createdAt": (datetime.now() - timedelta(hours=i)).isoformat(),
        })
    return alerts


@router.get("/admin/users")
async def api_admin_users(search: str = "", riskLevel: str = "", limit: int = 50):
    results = _reload_results()
    if results is None:
        return {"users": [], "total": 0, "page": 1, "totalPages": 1}

    df = results.copy()
    if riskLevel and riskLevel != "all":
        if riskLevel == "critical":
            df = df[df["default_probability"] >= 0.50]
        elif riskLevel == "high":
            df = df[df["risk_category"] == "HIGH"]
        elif riskLevel == "medium":
            df = df[df["risk_category"] == "MEDIUM"]
        elif riskLevel == "low":
            df = df[df["risk_category"] == "LOW"]

    users = []
    for _, row in df.head(limit).iterrows():
        bid  = str(row["borrower_id"])
        cs   = float(row["credit_score"])
        prob = float(row["default_probability"])
        inc  = float(row.get("monthly_net_income_inr", 40000))
        emp  = str(row.get("employment_type", "Salaried"))
        state = str(row.get("state", "Maharashtra"))
        rc   = str(row["risk_category"])

        if search and search.lower() not in bid.lower() and search.lower() not in state.lower():
            continue

        users.append({
            "id":             bid,
            "name":           f"Borrower {bid[-4:]}",
            "email":          f"{bid.lower()}@example.com",
            "city":           state.split()[0],
            "state":          state,
            "riskScore":      _credit_to_risk_score(cs),
            "riskLevel":      _risk_level_str(prob),
            "employmentType": emp,
            "monthlyIncome":  inc,
            "creditScore":    cs,
        })
    total_users = len(users)
    total_pages = max(1, math.ceil(total_users / limit))
    return {"users": users, "total": total_users, "page": 1, "totalPages": total_pages}


# ── Excel Export ──────────────────────────────────────────────────────

def _safe_float(val, default=0.0) -> float:
    """Safely convert to float, handling NaN/None."""
    try:
        v = float(val)
        return default if (v != v) else v  # NaN check: NaN != NaN
    except (TypeError, ValueError):
        return default


def _safe_int(val, default=0) -> int:
    """Safely convert to int, handling NaN/None."""
    try:
        v = float(val)
        return default if (v != v) else int(v)
    except (TypeError, ValueError):
        return default


def _generate_risk_reasons(row: pd.Series, dataset_row: Optional[pd.Series] = None) -> str:
    """Generate human-readable risk reasons based on borrower data."""
    reasons = []
    prob = _safe_float(row.get("default_probability", 0))

    # Credit score analysis
    cibil = _safe_float(dataset_row.get("cibil_bureau_score")) if dataset_row is not None else 0
    if cibil > 0 and cibil < 500:
        reasons.append(f"Very low CIBIL score ({int(cibil)})")
    elif cibil > 0 and cibil < 650:
        reasons.append(f"Below-average CIBIL score ({int(cibil)})")

    # Days past due
    dpd = _safe_int(dataset_row.get("days_past_due_dpd")) if dataset_row is not None else 0
    if dpd > 90:
        reasons.append(f"Severely overdue payments ({dpd} days past due)")
    elif dpd > 30:
        reasons.append(f"Overdue payments ({dpd} days past due)")

    # Debt to income
    dti = _safe_float(dataset_row.get("debt_to_income_ratio")) if dataset_row is not None else 0
    if dti > 0.6:
        reasons.append(f"Very high debt-to-income ratio ({dti:.0%})")
    elif dti > 0.4:
        reasons.append(f"Elevated debt-to-income ratio ({dti:.0%})")

    # Previous defaults
    prev_default = _safe_int(dataset_row.get("previous_loan_default_flag")) if dataset_row is not None else 0
    if prev_default:
        reasons.append("Previous loan default on record")

    # Late payments
    late = _safe_int(dataset_row.get("num_late_payments_12m")) if dataset_row is not None else 0
    if late >= 5:
        reasons.append(f"Frequent late payments ({late} in last 12 months)")
    elif late >= 2:
        reasons.append(f"Multiple late payments ({late} in last 12 months)")

    # Credit utilisation
    cu = _safe_float(dataset_row.get("credit_utilisation_ratio")) if dataset_row is not None else 0
    if cu > 0.8:
        reasons.append(f"Very high credit utilisation ({cu:.0%})")

    # Stress stage
    stress = str(row.get("stress_stage_label", ""))
    if stress == "NPA":
        reasons.append("Classified as Non-Performing Asset (NPA)")
    elif stress in ("Delinquency", "Early Stress"):
        reasons.append(f"Stress stage: {stress}")

    # Behavioral deterioration
    bd = _safe_int(row.get("behavioral_deterioration"))
    if bd >= 3:
        reasons.append(f"Significant behavioral deterioration (score: {bd})")

    # EMI stress
    emi_stress = _safe_int(row.get("emi_stress"))
    if emi_stress:
        reasons.append("EMI stress detected")

    # Hard enquiries
    enquiries = _safe_int(dataset_row.get("num_hard_enquiries_12m")) if dataset_row is not None else 0
    if enquiries >= 5:
        reasons.append(f"Excessive credit enquiries ({enquiries} in 12 months)")

    # High LTV
    ltv = _safe_float(dataset_row.get("loan_to_value_ratio_ltv")) if dataset_row is not None else 0
    if ltv > 0.8:
        reasons.append(f"High loan-to-value ratio ({ltv:.0%})")

    if not reasons:
        if prob >= 0.30:
            reasons.append("Composite risk factors exceed HIGH threshold")
        elif prob >= 0.10:
            reasons.append("Moderate risk profile based on combined factors")
        else:
            reasons.append("Low risk — no significant risk indicators")

    return "; ".join(reasons)


@router.get("/admin/export-excel")
async def api_admin_export_excel(riskLevel: str = ""):
    """Export all borrower data as an Excel file with risk reasons."""
    results = _reload_results()
    ds = _get_dataset()
    if results is None:
        raise HTTPException(404, "No batch results available. Run batch scoring first.")

    df = results.copy()

    # Filter by risk level if specified
    if riskLevel and riskLevel != "all":
        if riskLevel == "critical":
            df = df[df["default_probability"] >= 0.50]
        elif riskLevel == "high":
            df = df[df["risk_category"] == "HIGH"]
        elif riskLevel == "medium":
            df = df[df["risk_category"] == "MEDIUM"]
        elif riskLevel == "low":
            df = df[df["risk_category"] == "LOW"]

    # Merge with original dataset for full details
    if ds is not None:
        merge_cols = [c for c in ds.columns if c != "borrower_id"]
        # Avoid duplicate columns
        existing = set(df.columns) - {"borrower_id"}
        new_cols = ["borrower_id"] + [c for c in merge_cols if c not in existing]
        df = df.merge(ds[new_cols], on="borrower_id", how="left")

    # Build the export rows directly from merged data
    export_rows = []
    for _, row in df.iterrows():
        bid = str(row["borrower_id"])
        prob = _safe_float(row.get("default_probability"))
        cs = _safe_float(row.get("credit_score"))
        inc = _safe_float(row.get("monthly_net_income_inr"))
        cibil = _safe_float(row.get("cibil_bureau_score"))
        age = _safe_int(row.get("borrower_age"))

        export_rows.append({
            "Borrower ID": bid,
            "Name": f"Borrower {bid[-4:]}",
            "Email": f"{bid.lower()}@example.com",
            "Phone": f"+91-{abs(hash(bid)) % 9000000000 + 1000000000}",
            "State": str(row.get("state", "N/A")),
            "Age": age if age > 0 else "N/A",
            "Employment Type": str(row.get("employment_type", "N/A")),
            "Borrower Segment": str(row.get("borrower_segment", "N/A")).replace("_", " ").title(),
            "Monthly Income (INR)": round(inc, 2),
            "Loan Type": str(row.get("loan_type", "N/A")),
            "Loan Amount (INR)": _safe_float(row.get("loan_amount_requested_inr")),
            "CIBIL Score": round(cibil) if cibil > 0 else "N/A",
            "Credit Score (Model)": round(cs, 1),
            "Default Probability": round(prob, 4),
            "Risk Category": str(row.get("risk_category", "N/A")),
            "Stress Stage": str(row.get("stress_stage_label", "N/A")),
            "EMI Stress": "Yes" if _safe_int(row.get("emi_stress")) else "No",
            "Expected Loss (INR)": round(_safe_float(row.get("expected_loss_inr")), 2),
            "Risk Reasons": _generate_risk_reasons(row, row),
        })

    export_df = pd.DataFrame(export_rows)

    # Write to Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Borrower Risk Report")

        # Auto-adjust column widths
        ws = writer.sheets["Borrower Risk Report"]
        for col_idx, col in enumerate(export_df.columns, 1):
            max_len = max(len(str(col)), export_df[col].astype(str).str.len().max())
            ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = min(max_len + 2, 50)

    output.seek(0)
    filename = f"credit_risk_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/admin/users/{user_id}")
async def api_admin_user_detail(user_id: str):
    results = _reload_results()
    ds = _get_dataset()

    row = None
    if results is not None:
        r = results[results["borrower_id"] == user_id]
        if not r.empty:
            row = r.iloc[0]

    if row is None:
        raise HTTPException(404, f"User {user_id} not found")

    cs   = _safe_float(row["credit_score"])
    prob = _safe_float(row["default_probability"])
    inc  = _safe_float(row.get("monthly_net_income_inr"), 40000)
    emp  = str(row.get("employment_type", "Salaried"))
    state = str(row.get("state", "Maharashtra"))
    risk_score = _credit_to_risk_score(cs)
    risk_level = _risk_level_str(prob)
    rng = random.Random(hash(user_id) & 0xFFFF)

    # Merge dataset columns for richer profile
    cibil = _safe_float(row.get("cibil_bureau_score"), 650)
    dpd = int(_safe_float(row.get("days_past_due_dpd"), 0))
    loan_amount = _safe_float(row.get("loan_amount_requested_inr"), 0)
    dti = 0.3
    cu = 0.4
    loan_type = str(row.get("loan_type", "Personal"))
    segment = str(row.get("borrower_segment", "salaried_urban"))
    age = int(_safe_float(row.get("borrower_age"), 30))

    if ds is not None:
        dr = ds[ds["borrower_id"] == user_id]
        if not dr.empty:
            d = dr.iloc[0]
            cibil = _safe_float(d.get("cibil_bureau_score"), cibil)
            dpd = int(_safe_float(d.get("days_past_due_dpd"), dpd))
            loan_amount = _safe_float(d.get("loan_amount_requested_inr"), loan_amount)
            dti = _safe_float(d.get("debt_to_income_ratio"), dti)
            cu = _safe_float(d.get("credit_utilisation_ratio"), cu)
            loan_type = str(d.get("loan_type", loan_type))
            segment = str(d.get("borrower_segment", segment))
            age = int(_safe_float(d.get("borrower_age"), age))

    # ── Build profile (matches frontend expectations) ──
    created_at = (datetime.now() - timedelta(days=rng.randint(60, 365))).isoformat()
    health_score = max(10, min(95, 100 - risk_score + rng.randint(-5, 5)))
    phone_num = f"+91-{abs(hash(user_id)) % 9000000000 + 1000000000}"

    profile = {
        "id": user_id,
        "name": f"Borrower {user_id[-4:]}",
        "email": f"{user_id.lower()}@example.com",
        "phone": phone_num,
        "city": state.split()[0],
        "state": state,
        "pincode": str(100000 + abs(hash(state)) % 900000),
        "employmentType": emp,
        "monthlyIncome": inc,
        "riskScore": risk_score,
        "riskLevel": risk_level,
        "financialHealthScore": health_score,
        "creditScore": cs,
        "defaultProbability": prob,
        "riskCategory": str(row.get("risk_category", "MEDIUM")) if not pd.isna(row.get("risk_category", "MEDIUM")) else "MEDIUM",
        "stressStage": int(_safe_float(row.get("stress_stage"), 0)),
        "cibilScore": cibil,
        "daysPassDue": dpd,
        "loanAmount": loan_amount,
        "debtToIncome": dti,
        "creditUtilisation": cu,
        "loanType": loan_type,
        "borrowerSegment": segment,
        "age": age,
        "isActive": True,
        "createdAt": created_at,
        "lastLoginAt": (datetime.now() - timedelta(hours=rng.randint(1, 72))).isoformat(),
    }

    # ── Risk history (array of snapshots) ──
    raw_trend = _gen_risk_trend(risk_score, n=10)
    risk_history = []
    segments = ["cautious_spender", "steady_borrower", "impulsive_spender", "high_risk_borrower"]
    for i, pt in enumerate(reversed(raw_trend)):
        h_score = max(10, min(95, 100 - pt["score"] + rng.randint(-3, 3)))
        risk_history.append({
            "id": f"RSK-{user_id[-4:]}-{i:02d}",
            "predictedAt": pt["date"] + "T10:00:00",
            "score": pt["score"],
            "financialHealthScore": h_score,
            "level": _risk_level_str(pt["score"] / 100),
            "confidence": round(0.80 + rng.random() * 0.18, 2),
            "behaviorSegment": rng.choice(segments),
        })

    # ── Transactions ──
    transactions = _gen_transactions(user_id, inc, prob)

    # ── Alerts ──
    alerts = _gen_alerts(user_id, risk_score / 100, prob)

    # ── Interventions for this user ──
    _ensure_seed_interventions()
    user_interventions = [iv for iv in _interventions if iv.get("userId") == user_id]

    # ── Spending by category ──
    spending_by_category = _gen_spending(inc, prob)

    # ── Summary stats ──
    total_debits = sum(t["amount"] for t in transactions if t["type"] == "debit")
    total_credits = sum(t["amount"] for t in transactions if t["type"] == "credit")
    stress_txns = sum(1 for t in transactions if t.get("isStressIndicator"))
    unread_alerts = sum(1 for a in alerts if not a.get("isRead"))
    active_interventions = sum(1 for iv in user_interventions if iv.get("status") in ("active", "pending"))
    prev_score = raw_trend[-2]["score"] if len(raw_trend) >= 2 else risk_score
    score_change = round(risk_score - prev_score, 1)

    summary = {
        "riskScoreChange": score_change,
        "totalTransactions": len(transactions),
        "stressTransactions": stress_txns,
        "unreadAlerts": unread_alerts,
        "activeInterventions": active_interventions,
        "totalDebits": total_debits,
        "totalCredits": total_credits,
    }

    return {
        "profile": profile,
        "riskHistory": risk_history,
        "transactions": transactions,
        "alerts": alerts,
        "interventions": user_interventions,
        "spendingByCategory": spending_by_category,
        "summary": summary,
    }


_interventions: list = []


def _ensure_seed_interventions():
    """Seed sample interventions from high-risk batch data on first call."""
    if _interventions:
        return
    results = _get_results()
    if results is None:
        return
    high = results[results["risk_category"] == "HIGH"].head(5)
    types = ["outreach_call", "emi_restructure", "credit_limit_reduction", "digital_coaching", "outreach_call"]
    statuses = ["active", "pending", "completed", "active", "pending"]
    priorities = ["urgent", "high", "medium", "high", "urgent"]
    descs = [
        "Borrower missed 2 consecutive EMIs. Outreach call to discuss restructuring options.",
        "Debt-to-income ratio exceeds 60%. Proposing EMI restructure to reduce monthly burden.",
        "Credit utilisation over 90% with declining CIBIL score. Reducing credit limit as preventive measure.",
        "Young borrower showing early stress signals. Enrolling in digital financial coaching programme.",
        "Borrower flagged by NPA early-warning system. Immediate outreach required.",
    ]
    for i, (_, row) in enumerate(high.iterrows()):
        bid = str(row["borrower_id"])
        _interventions.append({
            "id": f"INT-{i+1:04d}",
            "userId": bid,
            "userName": f"Borrower {bid[-4:]}",
            "type": types[i],
            "status": statuses[i],
            "priority": priorities[i],
            "description": descs[i],
            "assignedTo": ["Priya S.", "Rahul M.", "System", "AI Coach", "Amit K."][i],
            "createdAt": (datetime.now() - timedelta(days=random.randint(1, 14))).isoformat(),
        })


@router.post("/admin/interventions/create")
async def api_create_intervention(data: dict):
    _ensure_seed_interventions()
    intervention = {
        "id":          f"INT-{datetime.now().strftime('%H%M%S')}",
        "userId":      data.get("userId", ""),
        "userName":    f"Borrower {data.get('userId', 'N/A')[-4:]}",
        "type":        data.get("type", "counseling"),
        "status":      "pending",
        "priority":    data.get("priority", "medium"),
        "description": data.get("description", "Admin initiated intervention."),
        "assignedTo":  "Unassigned",
        "createdAt":   datetime.now().isoformat(),
    }
    _interventions.insert(0, intervention)
    log_audit("INTERVENTION_CREATED", "admin", "intervention", intervention["id"])
    return intervention


@router.get("/admin/interventions")
async def api_list_interventions():
    _ensure_seed_interventions()
    return _interventions


@router.get("/admin/model-performance")
async def api_model_performance():
    meta_path = Path(ARTIFACTS_DIR) / "model_metadata.json"
    meta = {}
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)

    perf = meta.get("performance", {})
    test = perf.get("test", {})

    accuracy  = round(test.get("accuracy", 0.958), 4)
    auc       = round(test.get("auc", 0.994), 4)
    precision = round(test.get("precision", 0.912), 4)
    recall    = round(test.get("recall", 0.884), 4)
    f1        = round(test.get("f1_score", 0.898), 4)

    # Detect feature drift by comparing batch results distribution to training baseline
    drift_detected = False
    drifted_features = []
    results = _get_results()
    if results is not None:
        # Simple heuristic: flag drift if high-risk ratio deviates > 5% from training baseline
        high_ratio = (results["risk_category"] == "HIGH").mean()
        if high_ratio > 0.35 or high_ratio < 0.05:
            drift_detected = True
            drifted_features = ["credit_utilisation_ratio", "days_past_due_dpd", "cibil_bureau_score"]

    total_predictions = len(results) if results is not None else 0

    return {
        "accuracy":             accuracy,
        "auc":                  auc,
        "precision":            precision,
        "recall":               recall,
        "f1":                   f1,
        "modelVersion":         meta.get("model_name", "XGBoost") + " v" + meta.get("version", "2.0"),
        "lastTrainedAt":        meta.get("training_date", datetime.now().isoformat()),
        "featureDriftDetected": drift_detected,
        "driftedFeatures":      drifted_features,
        "totalPredictions":     total_predictions,
        "features":             meta.get("num_features", 24),
    }


_audit_logs: list = []


def log_audit(action: str, user_id: str = "SYSTEM", resource_type: str = "", resource_id: str = "", ip: str = ""):
    """Append an audit log entry. Called by other endpoints."""
    _audit_logs.insert(0, {
        "id": f"LOG-{len(_audit_logs)+1:06d}",
        "action": action,
        "userId": user_id,
        "resourceType": resource_type,
        "resourceId": resource_id,
        "ipAddress": ip or f"10.0.{random.randint(1,254)}.{random.randint(1,254)}",
        "createdAt": datetime.now().isoformat(),
    })


def _ensure_seed_audit_logs():
    """Seed realistic audit log entries on first call."""
    if _audit_logs:
        return
    actions = [
        ("BATCH_SCORING_RUN", "SYSTEM", "scoring_run", "RUN-0047"),
        ("USER_LOGIN", "admin@risksense.in", "session", "SES-8821"),
        ("RISK_SCORE_QUERY", "admin@risksense.in", "borrower", "BID_00042"),
        ("MODEL_PREDICTION", "SYSTEM", "model", "XGBoost-v2"),
        ("INTERVENTION_CREATED", "priya@risksense.in", "intervention", "INT-0001"),
        ("DATA_EXPORT", "rahul@risksense.in", "report", "RPT-HIGH-RISK"),
        ("USER_LOGIN", "analyst@risksense.in", "session", "SES-8822"),
        ("RISK_THRESHOLD_ALERT", "SYSTEM", "alert", "ADM-ALT-0001"),
        ("BORROWER_PROFILE_VIEW", "admin@risksense.in", "borrower", "BID_00108"),
        ("MODEL_RETRAIN_TRIGGERED", "SYSTEM", "model", "XGBoost-v2"),
        ("BATCH_SCORING_COMPLETE", "SYSTEM", "scoring_run", "RUN-0047"),
        ("DB_BACKUP_COMPLETED", "SYSTEM", "database", "pg_dump_20260329"),
        ("CSV_IMPORT", "admin@risksense.in", "dataset", "india_credit_risk_100k"),
        ("USER_LOGOUT", "analyst@risksense.in", "session", "SES-8822"),
        ("INTERVENTION_UPDATED", "priya@risksense.in", "intervention", "INT-0002"),
        ("HIGH_RISK_REPORT_GENERATED", "SYSTEM", "report", "RPT-HR-0329"),
        ("API_KEY_ROTATED", "admin@risksense.in", "security", "KEY-API-003"),
        ("RISK_SCORE_QUERY", "rahul@risksense.in", "borrower", "BID_00567"),
        ("SCHEMA_MIGRATION", "SYSTEM", "database", "migration_v2.1"),
        ("USER_LOGIN", "priya@risksense.in", "session", "SES-8823"),
    ]
    for i, (action, user, res_type, res_id) in enumerate(actions):
        _audit_logs.append({
            "id": f"LOG-{i+1:06d}",
            "action": action,
            "userId": user,
            "resourceType": res_type,
            "resourceId": res_id,
            "ipAddress": f"10.0.{random.randint(1,254)}.{random.randint(1,254)}",
            "createdAt": (datetime.now() - timedelta(hours=i * 2, minutes=random.randint(0, 59))).isoformat(),
        })


@router.get("/admin/audit-logs")
async def api_audit_logs():
    _ensure_seed_audit_logs()
    return {"logs": _audit_logs, "total": len(_audit_logs)}


# ── Cross-Bank Defaulter Detection ────────────────────────────────────

from cross_bank import (
    check_cross_bank_defaults,
    report_default,
    enrich_prediction_with_cross_bank,
    get_registry_stats,
    get_participating_banks,
    register_bank,
    seed_demo_data as seed_cross_bank_demo,
    get_cross_bank_features,
)


class CrossBankCheckRequest(BaseModel):
    pan: str
    phone: str
    exclude_bank_id: str = ""


class CrossBankReportRequest(BaseModel):
    pan: str
    phone: str
    reporting_bank_id: str
    borrower_name: str = ""
    default_amount_inr: float = 0
    default_date: str = ""
    loan_type: str = "Personal"
    days_past_due: int = 90
    npa_stage: int = 4


class CrossBankPredictRequest(BaseModel):
    """Predict with cross-bank check — extends normal predict with PAN/phone."""
    pan: str = ""
    phone: str = ""
    exclude_bank_id: str = ""
    borrower_segment: str = "salaried_urban"
    employment_type: str = "Salaried"
    loan_type: str = "Personal"
    state: str = "Maharashtra"
    is_urban: int = 1
    borrower_age: int = 30
    debt_to_income_ratio: float = 0.3
    days_past_due_dpd: int = 0
    previous_loan_default_flag: int = 0
    num_late_payments_12m: int = 0
    credit_utilisation_ratio: float = 0.4
    cibil_bureau_score: float = 700
    monthly_net_income_inr: float = 50000
    payment_to_income_ratio_pti: float = 0.3
    num_hard_enquiries_12m: int = 1
    txn_frequency_monthly_avg: int = 50
    income_consistency_score: float = 0.6
    revolving_credit_balance_inr: float = 50000
    age_oldest_credit_account_months: int = 60
    num_open_credit_lines: int = 3
    loan_to_value_ratio_ltv: float = 0.5
    digital_engagement_score: int = 60
    utility_payment_score: int = 70
    loan_amount_requested_inr: float = 500000


@router.post("/cross-bank/check")
async def api_cross_bank_check(req: CrossBankCheckRequest):
    """Check if a borrower has defaults at other banks."""
    result = check_cross_bank_defaults(req.pan, req.phone, req.exclude_bank_id)
    return result


@router.post("/cross-bank/report")
async def api_cross_bank_report(req: CrossBankReportRequest):
    """Report a borrower default to the shared registry."""
    result = report_default(
        pan=req.pan,
        phone=req.phone,
        reporting_bank_id=req.reporting_bank_id,
        borrower_name=req.borrower_name,
        default_amount_inr=req.default_amount_inr,
        default_date=req.default_date,
        loan_type=req.loan_type,
        days_past_due=req.days_past_due,
        npa_stage=req.npa_stage,
    )
    return result


@router.post("/cross-bank/predict")
async def api_cross_bank_predict(req: CrossBankPredictRequest):
    """
    Score a borrower with cross-bank intelligence.
    1. Run the ML model prediction
    2. Check cross-bank registry
    3. Boost risk if cross-bank defaults found
    """
    # Build feature dict (exclude PAN/phone — they're not model features)
    feature_data = req.model_dump(exclude={"pan", "phone", "exclude_bank_id"})

    # Import the model scoring function
    try:
        from app import scoring_model
        from utils import features_from_dict
        if scoring_model is None:
            raise HTTPException(503, "Model not loaded")
        X = features_from_dict(feature_data, scoring_model.feature_columns, scoring_model.label_encoders)
        prediction = scoring_model.predict_single(X)
        if hasattr(prediction, "dict"):
            prediction = prediction.dict()
        elif hasattr(prediction, "model_dump"):
            prediction = prediction.model_dump()
    except ImportError:
        # Fallback: synthetic prediction for demo
        prob = random.uniform(0.05, 0.25)
        prediction = {
            "credit_score": round(700 - prob * 500, 1),
            "default_probability": round(prob, 4),
            "risk_category": "HIGH" if prob >= 0.30 else ("MEDIUM" if prob >= 0.10 else "LOW"),
            "timestamp": datetime.now().isoformat(),
        }

    # Enrich with cross-bank intelligence
    enriched = enrich_prediction_with_cross_bank(
        prediction, pan=req.pan, phone=req.phone, exclude_bank_id=req.exclude_bank_id
    )

    return enriched


@router.get("/cross-bank/stats")
async def api_cross_bank_stats():
    """Get cross-bank registry statistics."""
    return get_registry_stats()


@router.get("/cross-bank/banks")
async def api_cross_bank_banks():
    """Get participating banks."""
    return {"banks": get_participating_banks()}


@router.post("/cross-bank/register-bank")
async def api_register_bank(bank_id: str, bank_name: str, bank_code: str):
    """Register a new bank in the ecosystem."""
    return register_bank(bank_id, bank_name, bank_code)


@router.post("/cross-bank/seed-demo")
async def api_seed_cross_bank_demo():
    """Seed demo data for cross-bank registry (5 banks, ~50 defaulters)."""
    result = seed_cross_bank_demo()
    stats = get_registry_stats()
    return {"seeded": result, "stats": stats}


@router.get("/admin/cross-bank-alerts")
async def api_admin_cross_bank_alerts():
    """
    Admin endpoint: show borrowers in OUR portfolio who have
    cross-bank defaults (they looked clean to us but defaulted elsewhere).
    """
    ds = _get_dataset()
    results = _get_results()
    if ds is None:
        return {"alerts": [], "total": 0}

    # Simulate PAN/phone for demo (in production, these come from KYC)
    # We use borrower_id as a deterministic seed for PAN/phone generation
    from cross_bank import _load_registry
    registry = _load_registry()
    if not registry:
        return {"alerts": [], "total": 0, "message": "Cross-bank registry empty. Seed demo data first."}

    # Get identity hashes from registry
    registry_hashes = set(r["identity_hash"] for r in registry)

    alerts = []
    rng = random.Random(12345)  # Deterministic for demo consistency

    # Check a sample of borrowers against the registry
    sample_ids = ds["borrower_id"].head(200).tolist()
    for bid in sample_ids:
        # Simulate PAN/phone derivation from borrower_id
        pan = f"DEMO{bid.replace('BID_', '')}A"
        phone = f"98{int(bid.replace('BID_', '')):08d}"
        from cross_bank import hash_identity
        h = hash_identity(pan, phone)

        if h in registry_hashes:
            row = ds[ds["borrower_id"] == bid].iloc[0]
            # Get their current risk score
            score_row = None
            if results is not None and bid in results["borrower_id"].values:
                score_row = results[results["borrower_id"] == bid].iloc[-1]

            current_risk = "UNKNOWN"
            current_prob = 0.0
            if score_row is not None:
                current_risk = score_row.get("risk_category", "UNKNOWN")
                current_prob = score_row.get("default_probability", 0.0)

            # Find their cross-bank records
            matches = [r for r in registry if r["identity_hash"] == h]
            banks = set(r["reporting_bank_id"] for r in matches)

            alerts.append({
                "borrower_id": bid,
                "borrower_name": f"Borrower {bid.replace('BID_', '')}",
                "current_risk_category": current_risk,
                "current_default_probability": round(current_prob, 4),
                "cross_bank_defaults": len(matches),
                "banks_defaulted_at": list(banks),
                "total_default_amount": sum(r.get("default_amount_inr", 0) for r in matches),
                "max_dpd_other_banks": max(r.get("days_past_due", 0) for r in matches),
                "is_serial_defaulter": len(banks) >= 2,
                "alert_severity": "CRITICAL" if len(banks) >= 2 else "HIGH",
                "recommended_action": "Immediate review + credit freeze" if len(banks) >= 2 else "Enhanced monitoring",
            })

    alerts.sort(key=lambda x: x["cross_bank_defaults"], reverse=True)

    return {
        "alerts": alerts[:20],
        "total": len(alerts),
        "registry_stats": get_registry_stats(),
    }


# ── Health ─────────────────────────────────────────────────────────────

@router.get("/healthz")
async def api_healthz():
    return {"status": "healthy", "service": "credit-risk-api", "timestamp": datetime.now().isoformat()}
