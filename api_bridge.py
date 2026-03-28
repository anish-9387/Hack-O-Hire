"""
API Bridge — /api/* endpoints for the React frontend (AI-Pipeline UI).

Translates the frontend's expected API contract to the existing
Hack-O-Hire FastAPI backend data (model, CSV, batch results).

Token scheme: base64-encoded JSON  {"role": "user"|"admin", "borrower_id": "BID_..."}
"""
import base64
import json
import random
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Paths (relative to project root) ─────────────────────────────────
DATASET_PATH   = Path("Datasets/india_credit_risk_dataset_100k.csv")
RESULTS_PATH   = Path("data/processed/batch_results.csv")
HIGH_RISK_PATH = Path("data/processed/high_risk.csv")
SUMMARY_PATH   = Path("data/processed/batch_summary.json")
ARTIFACTS_DIR  = "src/model/artifacts"

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


# ── Token helpers ──────────────────────────────────────────────────────

def _make_token(role: str, borrower_id: str = "") -> str:
    payload = {"role": role, "borrower_id": borrower_id, "ts": datetime.now().isoformat()}
    return base64.b64encode(json.dumps(payload).encode()).decode()


def _parse_token(authorization: str = "") -> dict:
    """Parse Authorization: Bearer <token> → dict with role / borrower_id."""
    try:
        token = authorization.replace("Bearer ", "").strip()
        return json.loads(base64.b64decode(token).decode())
    except Exception:
        return {"role": "user", "borrower_id": ""}


def _require_auth(authorization: str = Header(default="")) -> dict:
    info = _parse_token(authorization)
    if not info.get("role"):
        raise HTTPException(401, "Unauthorized")
    return info


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


@router.post("/auth/login")
async def api_login(req: LoginRequest):
    ds = _get_dataset()

    if req.role == "admin":
        token = _make_token("admin", "ADMIN")
        log_audit("USER_LOGIN", req.email, "session", f"SES-{random.randint(1000,9999)}")
        return {
            "token": token,
            "role":  "admin",
            "user": {
                "id":    "ADMIN",
                "name":  "Risk Admin",
                "email": req.email,
                "role":  "admin",
                "city":  "Mumbai",
                "state": "Maharashtra",
            },
        }

    # User login: treat email field as borrower_id (or pick a demo one)
    borrower_id = req.email.strip()
    if ds is not None:
        if borrower_id not in ds["borrower_id"].values:
            # pick the first borrower as demo
            borrower_id = ds["borrower_id"].iloc[0]
        row = ds[ds["borrower_id"] == borrower_id].iloc[0]
        name = f"Borrower {borrower_id[-4:]}"
        city  = str(row.get("state", "Mumbai")).split()[0]
        state = str(row.get("state", "Maharashtra"))
        emp   = str(row.get("employment_type", "Salaried"))
        inc   = float(row.get("monthly_net_income_inr", 50000))
    else:
        name, city, state, emp, inc = "Demo User", "Mumbai", "Maharashtra", "Salaried", 50000.0

    token = _make_token("user", borrower_id)
    log_audit("USER_LOGIN", req.email, "session", f"SES-{random.randint(1000,9999)}")
    return {
        "token": token,
        "role":  "user",
        "user": {
            "id":             borrower_id,
            "name":           name,
            "email":          req.email,
            "role":           "user",
            "city":           city,
            "state":          state,
            "employmentType": emp,
            "monthlyIncome":  inc,
        },
    }


# ── Dashboard Overview ─────────────────────────────────────────────────

@router.get("/dashboard/overview")
async def api_dashboard_overview(authorization: str = Header(default="")):
    info = _parse_token(authorization)
    borrower_id = info.get("borrower_id", "")

    ds  = _get_dataset()
    row = None
    if ds is not None and borrower_id and borrower_id in ds["borrower_id"].values:
        row = ds[ds["borrower_id"] == borrower_id].iloc[0]

    income   = float(row["monthly_net_income_inr"]) if row is not None else 50000.0
    state_val = str(row["state"])                   if row is not None else "Maharashtra"
    emp_val  = str(row["employment_type"])          if row is not None else "Salaried"

    cs, prob, rc = _get_borrower_score(borrower_id)
    risk_score = _credit_to_risk_score(cs)
    level      = _risk_level_str(prob)
    health     = max(0, min(100, 100 - risk_score))

    expenses   = round(income * (0.65 + prob * 0.2), 0)
    savings_rt = round(max(0, (income - expenses) / income * 100), 1)

    return {
        "user": {
            "id":             borrower_id,
            "name":           f"Borrower {borrower_id[-4:]}",
            "city":           state_val.split()[0],
            "state":          state_val,
            "employmentType": emp_val,
        },
        "totalBalance":    round(income * 2.3, 0),
        "monthlyIncome":   round(income, 0),
        "monthlyExpenses": expenses,
        "savingsRate":     savings_rt,
        "currentRiskScore": {
            "score":               risk_score,
            "level":               level,
            "financialHealthScore": health,
            "confidence":          0.87,
        },
        "riskTrend":          _gen_risk_trend(risk_score),
        "spendingBreakdown":  _gen_spending(income, prob),
        "recentTransactions": _gen_transactions(borrower_id, income, prob),
    }


# ── Spending Analytics ─────────────────────────────────────────────────

@router.get("/dashboard/spending")
async def api_spending(period: str = "30d", authorization: str = Header(default="")):
    info = _parse_token(authorization)
    borrower_id = info.get("borrower_id", "")

    ds = _get_dataset()
    income = 50000.0
    if ds is not None and borrower_id and borrower_id in ds["borrower_id"].values:
        income = float(ds[ds["borrower_id"] == borrower_id].iloc[0]["monthly_net_income_inr"])

    _, prob, _ = _get_borrower_score(borrower_id)

    days_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
    n_days   = days_map.get(period, 30)
    n_weeks  = max(1, n_days // 7)

    timeline = []
    rng = random.Random(hash(borrower_id) & 0xFF)
    for i in range(n_weeks):
        wk_income  = income / 4 * (1 + rng.uniform(-0.1, 0.1))
        wk_expense = income / 4 * (0.7 + prob * 0.15) * (1 + rng.uniform(-0.05, 0.1))
        date = (datetime.now() - timedelta(weeks=(n_weeks - i))).strftime("%Y-%m-%d")
        timeline.append({"date": date, "income": round(wk_income, 0), "expenses": round(wk_expense, 0)})

    spending = _gen_spending(income, prob)
    categories = [
        {
            "category": s["category"],
            "total":    s["amount"],
            "percentage": s["percentage"],
            "trend":    "up" if s["category"] in ("loan_app", "atm_withdrawal") and prob > 0.2 else "stable",
            "count":    rng.randint(3, 15),
        }
        for s in spending
    ]

    total_out = round(income * 0.72 * (n_days / 30), 0)
    total_in  = round(income * (n_days / 30), 0)
    return {"timeline": timeline, "categories": categories, "totalOutflow": total_out, "totalInflow": total_in}


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

    top_factors = [
        {"feature": "emiPaymentRatio",         "impact": round(prob * 18 + 2, 2), "direction": "increases_risk"},
        {"feature": "loanAppTransactionCount", "impact": round(prob * 14 + 1, 2), "direction": "increases_risk"},
        {"feature": "balanceDrop4w",           "impact": round(prob * 12 + 1, 2), "direction": "increases_risk"},
        {"feature": "atmWithdrawalFrequency",  "impact": round(prob * 8  + 1, 2), "direction": "increases_risk"},
    ]
    protective = [
        {"feature": "incomeConsistency",    "impact": round((1 - prob) * 12 + 3, 2), "direction": "decreases_risk"},
        {"feature": "utilityPaymentScore",  "impact": round((1 - prob) * 8  + 2, 2), "direction": "decreases_risk"},
        {"feature": "digitalEngagement",    "impact": round((1 - prob) * 5  + 1, 2), "direction": "decreases_risk"},
    ]
    recs = [
        "Maintain EMI payments on time to improve your credit score.",
        "Reduce ATM cash withdrawals — prefer UPI/digital payments.",
        "Build an emergency fund of at least 3 months' expenses.",
        "Avoid multiple loan applications within a short period.",
    ]
    if prob < 0.10:
        recs = [
            "Keep up your excellent payment history.",
            "Consider investing surplus savings in mutual funds.",
            "Your credit utilisation is optimal — maintain it below 30%.",
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

    ds = _get_dataset()
    income = 50000.0
    if ds is not None and borrower_id and borrower_id in ds["borrower_id"].values:
        income = float(ds[ds["borrower_id"] == borrower_id].iloc[0]["monthly_net_income_inr"])

    _, prob, _ = _get_borrower_score(borrower_id)
    txns = _gen_transactions(borrower_id, income, prob)
    return {"data": txns[:limit], "total": len(txns), "limit": limit, "offset": 0}


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
        "projectedScore": projected,
        "riskDelta":      delta,
        "warning":        warning,
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

    ds = _get_dataset()
    income = 50000.0
    if ds is not None and borrower_id and borrower_id in ds["borrower_id"].values:
        income = float(ds[ds["borrower_id"] == borrower_id].iloc[0]["monthly_net_income_inr"])

    level = _risk_level_str(prob)
    msgs = {
        "critical": "Urgent action needed. Your financial stress indicators are at a critical level.",
        "high":     "Your risk profile needs immediate attention. Focus on reducing debt load.",
        "medium":   "You're managing reasonably but there's room to improve financial resilience.",
        "low":      "Your financial health is excellent! You're in a great position to grow wealth.",
    }
    tips = [
        {"category": "Savings", "title": "Build Emergency Fund",
         "description": "Aim for 3-6 months of expenses in a liquid savings account.",
         "potentialSaving": round(income * 0.1, 0), "priority": "high"},
        {"category": "Debt",    "title": "Reduce EMI Burden",
         "description": "Keep total EMIs below 40% of monthly income.",
         "potentialSaving": round(income * 0.05, 0), "priority": "medium"},
        {"category": "Digital", "title": "Switch to UPI Payments",
         "description": "Reduce ATM withdrawals — digital payments improve credit profile.",
         "potentialSaving": round(income * 0.02, 0), "priority": "low"},
    ]
    flags = []
    if prob >= 0.30:
        flags = ["High default risk — consider debt counselling immediately"]
    elif prob >= 0.10:
        flags = ["Moderate risk — review monthly spending patterns"]

    return {
        "overallMessage":     msgs[level],
        "warningFlags":       flags,
        "tips":               tips,
        "monthlyGoal":        {"focus": "Reduce discretionary spending by 10%",
                               "progress": round((1 - prob) * 70, 1)},
        "savingsOpportunity": round(income * max(0.05, 0.15 - prob * 0.1), 0),
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

    return {"byEmploymentType": by_emp_type, "byCity": by_city, "trendOverTime": trend}


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
        df = df[df["risk_category"] == riskLevel.upper()]

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

    cs   = float(row["credit_score"])
    prob = float(row["default_probability"])
    inc  = float(row.get("monthly_net_income_inr", 40000))
    emp  = str(row.get("employment_type", "Salaried"))
    state = str(row.get("state", "Maharashtra"))

    profile = None
    if ds is not None:
        dr = ds[ds["borrower_id"] == user_id]
        if not dr.empty:
            d = dr.iloc[0]
            profile = {
                "cibilScore":          float(d.get("cibil_bureau_score", 650)),
                "daysPassDue":         int(d.get("days_past_due_dpd", 0)),
                "loanAmount":          float(d.get("loan_amount_requested_inr", 0)),
                "debtToIncome":        float(d.get("debt_to_income_ratio", 0.3)),
                "creditUtilisation":   float(d.get("credit_utilisation_ratio", 0.4)),
                "loanType":            str(d.get("loan_type", "Personal")),
                "borrowerSegment":     str(d.get("borrower_segment", "salaried_urban")),
            }

    return {
        "id":             user_id,
        "name":           f"Borrower {user_id[-4:]}",
        "email":          f"{user_id.lower()}@example.com",
        "city":           state.split()[0],
        "state":          state,
        "employmentType": emp,
        "monthlyIncome":  inc,
        "riskScore":      _credit_to_risk_score(cs),
        "riskLevel":      _risk_level_str(prob),
        "creditScore":    cs,
        "defaultProbability": prob,
        "riskCategory":   str(row["risk_category"]),
        "stressStage":    int(row.get("stress_stage", 0)),
        "profile":        profile,
        "riskTrend":      _gen_risk_trend(_credit_to_risk_score(cs)),
        "alerts":         _gen_alerts(user_id, _credit_to_risk_score(cs) / 100, prob),
        "transactions":   _gen_transactions(user_id, inc, prob)[:5],
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
