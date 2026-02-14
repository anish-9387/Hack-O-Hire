"""
Real-time Scoring Service
Provides risk scoring for customers based on their features
"""
import sys
from pathlib import Path
from typing import Dict, List
import pandas as pd

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.model.model_wrapper import FinancialStressModel
from src.features.feature_engineering import FinancialFeatureEngine

class RealTimeScoringService:
    """Service for real-time customer risk scoring"""
    
    def __init__(self):
        self.model = FinancialStressModel()
        self.feature_engine = FinancialFeatureEngine()
        self.is_loaded = False
        
    def initialize(self):
        """Initialize the scoring service"""
        print("Initializing Real-Time Scoring Service...")
        
        # Load model
        if self.model.load_model():
            self.is_loaded = True
            print("✅ Scoring service initialized successfully")
            return True
        else:
            print("❌ Failed to initialize scoring service")
            return False
    
    def score_with_features(self, features: Dict) -> Dict:
        """
        Score a customer given pre-computed features
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            Scoring result with risk score and explanation
        """
        if not self.is_loaded:
            return {"error": "Service not initialized"}
        
        try:
            result = self.model.score_customer(features)
            return result
        except Exception as e:
            return {"error": f"Scoring failed: {str(e)}"}
    
    def score_from_transactions(self, transactions: List[Dict], 
                               customer_id: int) -> Dict:
        """
        Score a customer from raw transaction data
        
        Args:
            transactions: List of transaction dictionaries
            customer_id: Customer ID
            
        Returns:
            Scoring result with risk score and explanation
        """
        if not self.is_loaded:
            return {"error": "Service not initialized"}
        
        try:
            # Convert transactions to DataFrame
            txns_df = pd.DataFrame(transactions)
            txns_df['transaction_date'] = pd.to_datetime(txns_df['transaction_date'])
            txns_df['customer_id'] = customer_id
            
            # Engineer features
            features_df = self.feature_engine.engineer_features(txns_df, customer_id)
            
            if len(features_df) == 0:
                return {"error": "Failed to engineer features"}
            
            # Convert to dictionary
            features = features_df.iloc[0].to_dict()
            
            # Remove non-feature columns
            features = {k: v for k, v in features.items() 
                       if k not in ['customer_id', 'timestamp', 'is_stressed']}
            
            # Score customer
            result = self.model.score_customer(features)
            result['customer_id'] = customer_id
            result['num_transactions'] = len(transactions)
            
            return result
            
        except Exception as e:
            return {"error": f"Scoring failed: {str(e)}"}
    
    def batch_score(self, customers_features: List[Dict]) -> List[Dict]:
        """
        Score multiple customers in batch
        
        Args:
            customers_features: List of feature dictionaries
            
        Returns:
            List of scoring results
        """
        if not self.is_loaded:
            return [{"error": "Service not initialized"}]
        
        results = []
        for features in customers_features:
            customer_id = features.get('customer_id', 'unknown')
            result = self.score_with_features(features)
            result['customer_id'] = customer_id
            results.append(result)
        
        return results
    
    def get_risk_threshold(self, risk_level: str = "HIGH") -> float:
        """Get risk score threshold for different risk levels"""
        thresholds = {
            "HIGH": 0.75,
            "MEDIUM": 0.50,
            "LOW": 0.25
        }
        return thresholds.get(risk_level.upper(), 0.75)
    
    def get_service_status(self) -> Dict:
        """Get service status and statistics"""
        status = {
            'service': 'Real-Time Scoring Service',
            'status': 'ready' if self.is_loaded else 'not initialized',
            'model_loaded': self.model.model is not None,
            'explainer_available': self.model.explainer is not None
        }
        
        if self.is_loaded:
            model_info = self.model.get_model_info()
            status.update(model_info)
        
        return status

# Singleton instance for the API
scoring_service = RealTimeScoringService()

if __name__ == "__main__":
    # Test scoring service
    service = RealTimeScoringService()
    
    if service.initialize():
        # Test with dummy features
        test_features = {
            'days_since_last_salary': 50,
            'avg_salary_amount': 45000,
            'salary_delay_trend': 2.5,
            'balance_drop_pct_4weeks': 40,
            'upi_to_loan_apps_pct': 30,
            'failed_autopay_count': 4,
            'atm_withdrawal_count_30d': 12,
            'essential_spend_ratio': 0.7,
            'discretionary_spend_ratio': 0.1
        }
        
        print("\n📊 Testing scoring service...")
        result = service.score_with_features(test_features)
        
        print(f"\n📈 Scoring Result:")
        print(f"   Risk Score: {result.get('risk_score', 'N/A')}")
        print(f"   Prediction: {result.get('prediction', 'N/A')}")
        print(f"   Risk Level: {result.get('risk_level', 'N/A')}")
        
        print(f"\n📋 Service Status:")
        status = service.get_service_status()
        for key, value in status.items():
            print(f"   {key}: {value}")
