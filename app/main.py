"""
Financial Stress Prediction API
FastAPI application for real-time risk scoring
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
import sys
from pathlib import Path
import yaml

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.scoring.scoring_service import RealTimeScoringService
from src.features.feature_engineering import FinancialFeatureEngine

# Initialize FastAPI app
app = FastAPI(
    title="Financial Stress Prediction API",
    description="Real-time risk scoring API for financial stress detection",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load configuration
config_path = Path(__file__).parent / "config.yaml"
if config_path.exists():
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
else:
    config = {}

# Initialize scoring service
scoring_service = RealTimeScoringService()

# Pydantic models for request/response
class CustomerFeatures(BaseModel):
    """Customer features for scoring"""
    customer_id: Optional[int] = None
    days_since_last_salary: float = 0
    avg_salary_amount: float = 0
    salary_delay_trend: float = 0
    salary_variance: float = 0
    months_with_salary: int = 0
    current_balance: float = 0
    min_balance_30d: float = 0
    balance_drop_pct_4weeks: float = 0
    balance_trend: float = 0
    avg_daily_balance: float = 0
    upi_to_loan_apps_pct: float = 0
    upi_to_loan_apps_count: int = 0
    total_upi_count: int = 0
    avg_upi_amount: float = 0
    upi_loan_amount_30d: float = 0
    essential_spend_ratio: float = 0
    discretionary_spend_ratio: float = 0
    cash_withdrawal_ratio: float = 0
    avg_bill_payment_day: float = 0
    bill_payment_delay_trend: float = 0
    failed_autopay_count: int = 0
    atm_withdrawal_count_30d: int = 0
    atm_withdrawal_amount_30d: float = 0
    avg_atm_amount: float = 0
    txn_count_30d: int = 0
    txn_count_7d: int = 0
    avg_txn_per_day: float = 0
    debit_count_30d: int = 0
    credit_count_30d: int = 0

class Transaction(BaseModel):
    """Transaction model"""
    customer_id: int
    transaction_date: str
    transaction_type: str
    amount: float
    category: str
    description: Optional[str] = ""

class RiskScoreResponse(BaseModel):
    """Risk score response"""
    customer_id: Optional[int]
    risk_score: float
    prediction: str
    risk_level: str
    explanation: Dict
    model_version: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class BatchScoreRequest(BaseModel):
    """Batch scoring request"""
    customers: List[CustomerFeatures]

class TransactionScoreRequest(BaseModel):
    """Transaction-based scoring request"""
    customer_id: int
    transactions: List[Transaction]

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("\n" + "="*60)
    print("🚀 Starting Financial Stress Prediction API")
    print("="*60)
    
    if scoring_service.initialize():
        print("✅ API ready to serve requests")
    else:
        print("⚠️ API started but scoring service failed to initialize")
        print("   Model training may be required. Run notebooks/model_training.ipynb")

# Root endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "Financial Stress Prediction API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "score": "/api/v1/score",
            "score_batch": "/api/v1/score/batch",
            "score_from_transactions": "/api/v1/score/transactions",
            "model_info": "/api/v1/model/info",
            "docs": "/docs"
        }
    }

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    status = scoring_service.get_service_status()
    return {
        "status": "healthy" if status.get('status') == 'ready' else "degraded",
        "service_status": status,
        "timestamp": datetime.now().isoformat()
    }

# Score a single customer
@app.post("/api/v1/score", response_model=RiskScoreResponse)
async def score_customer(features: CustomerFeatures):
    """
    Score a single customer based on their features
    
    Returns risk score, prediction, and SHAP explanation
    """
    try:
        # Convert to dictionary
        features_dict = features.dict()
        customer_id = features_dict.pop('customer_id', None)
        
        # Score customer
        result = scoring_service.score_with_features(features_dict)
        
        if 'error' in result:
            raise HTTPException(status_code=500, detail=result['error'])
        
        result['customer_id'] = customer_id
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Batch scoring
@app.post("/api/v1/score/batch")
async def score_batch(request: BatchScoreRequest):
    """
    Score multiple customers in batch
    
    Returns list of risk scores
    """
    try:
        customers_features = [customer.dict() for customer in request.customers]
        results = scoring_service.batch_score(customers_features)
        
        return {
            "total_customers": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Score from transactions
@app.post("/api/v1/score/transactions")
async def score_from_transactions(request: TransactionScoreRequest):
    """
    Score a customer from their transaction history
    
    Features are engineered automatically from transactions
    """
    try:
        transactions = [txn.dict() for txn in request.transactions]
        result = scoring_service.score_from_transactions(
            transactions, 
            request.customer_id
        )
        
        if 'error' in result:
            raise HTTPException(status_code=500, detail=result['error'])
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get model information
@app.get("/api/v1/model/info")
async def get_model_info():
    """Get model metadata and performance metrics"""
    try:
        info = scoring_service.model.get_model_info()
        
        if 'error' in info:
            raise HTTPException(status_code=404, detail=info['error'])
        
        return info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get risk thresholds
@app.get("/api/v1/config/thresholds")
async def get_risk_thresholds():
    """Get configured risk thresholds"""
    return {
        "high": scoring_service.get_risk_threshold("HIGH"),
        "medium": scoring_service.get_risk_threshold("MEDIUM"),
        "low": scoring_service.get_risk_threshold("LOW")
    }

# Example scoring endpoint
@app.get("/api/v1/score/example")
async def score_example():
    """
    Score an example customer with dummy data
    Useful for testing
    """
    example_features = {
        'days_since_last_salary': 45,
        'avg_salary_amount': 50000,
        'salary_delay_trend': 2.5,
        'balance_drop_pct_4weeks': 35,
        'upi_to_loan_apps_pct': 25,
        'failed_autopay_count': 3,
        'atm_withdrawal_count_30d': 10,
        'essential_spend_ratio': 0.65,
        'discretionary_spend_ratio': 0.15
    }
    
    result = scoring_service.score_with_features(example_features)
    result['note'] = "This is an example prediction with dummy data"
    
    return result

if __name__ == "__main__":
    import uvicorn
    
    # Get config
    host = config.get('api', {}).get('host', '0.0.0.0')
    port = config.get('api', {}).get('port', 8000)
    reload = config.get('api', {}).get('reload', True)
    
    print(f"\n🚀 Starting API server at http://{host}:{port}")
    print(f"📚 API documentation: http://{host}:{port}/docs")
    print(f"🔧 Alternative docs: http://{host}:{port}/redoc\n")
    
    uvicorn.run("main:app", host=host, port=port, reload=reload)
