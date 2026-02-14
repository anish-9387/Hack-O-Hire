"""
ML Model Wrapper for Financial Stress Prediction
Loads and serves the trained model with SHAP explanations
"""
import joblib
import numpy as np
import pandas as pd
import shap
from pathlib import Path
from typing import Dict, List, Optional
import json

class FinancialStressModel:
    """Wrapper for financial stress prediction model"""
    
    def __init__(self, models_dir: str = "src/model/artifacts"):
        self.models_dir = Path(models_dir)
        self.model = None
        self.feature_columns = None
        self.explainer = None
        self.metadata = None
        
    def load_model(self):
        """Load trained model and associated artifacts"""
        try:
            # Load model
            model_path = self.models_dir / 'financial_stress_model.joblib'
            if model_path.exists():
                self.model = joblib.load(model_path)
                print(f"✅ Model loaded from {model_path}")
            else:
                print(f"❌ Model not found at {model_path}")
                return False
            
            # Load feature columns
            feature_path = self.models_dir / 'feature_columns.joblib'
            if feature_path.exists():
                self.feature_columns = joblib.load(feature_path)
                print(f"✅ Feature columns loaded ({len(self.feature_columns)} features)")
            else:
                print(f"⚠️ Feature columns file not found")
            
            # Load SHAP explainer
            explainer_path = self.models_dir / 'shap_explainer.joblib'
            if explainer_path.exists():
                self.explainer = joblib.load(explainer_path)
                print(f"✅ SHAP explainer loaded")
            else:
                print(f"⚠️ SHAP explainer not found")
            
            # Load metadata
            metadata_path = self.models_dir / 'model_metadata.json'
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    self.metadata = json.load(f)
                print(f"✅ Model metadata loaded")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            return False
    
    def prepare_features(self, features_dict: Dict) -> pd.DataFrame:
        """Prepare features for prediction"""
        # Create DataFrame from features
        features_df = pd.DataFrame([features_dict])
        
        # Ensure all required columns exist
        if self.feature_columns:
            for col in self.feature_columns:
                if col not in features_df.columns:
                    features_df[col] = 0  # Default value for missing features
            
            # Select and order columns
            features_df = features_df[self.feature_columns]
        
        # Handle missing values
        features_df = features_df.fillna(0)
        
        # Handle infinite values
        features_df = features_df.replace([np.inf, -np.inf], 0)
        
        return features_df
    
    def predict_proba(self, features: pd.DataFrame) -> float:
        """
        Predict probability of financial stress
        Returns: Probability [0-1]
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load_model() first.")
        
        try:
            probabilities = self.model.predict_proba(features)
            return float(probabilities[0][1])  # Probability of stress class
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            return 0.0
    
    def predict(self, features: pd.DataFrame) -> int:
        """
        Predict binary stress label
        Returns: 0 (not stressed) or 1 (stressed)
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load_model() first.")
        
        try:
            prediction = self.model.predict(features)
            return int(prediction[0])
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            return 0
    
    def explain_prediction(self, features: pd.DataFrame) -> Dict:
        """
        Get SHAP explanation for a prediction
        Returns: Dictionary with feature contributions
        """
        if self.explainer is None:
            return {"error": "SHAP explainer not available"}
        
        try:
            # Calculate SHAP values
            shap_values = self.explainer.shap_values(features)
            
            # Get feature contributions
            feature_names = features.columns.tolist()
            
            if isinstance(shap_values, list):
                shap_values = shap_values[1]  # For multi-class, get positive class
            
            contributions = {}
            for i, feature in enumerate(feature_names):
                contributions[feature] = float(shap_values[0][i])
            
            # Sort by absolute contribution
            sorted_contributions = dict(
                sorted(contributions.items(), 
                      key=lambda x: abs(x[1]), 
                      reverse=True)
            )
            
            # Get top 10 contributors
            top_10 = dict(list(sorted_contributions.items())[:10])
            
            return {
                'base_value': float(self.explainer.expected_value),
                'all_contributions': contributions,
                'top_10_contributors': top_10
            }
            
        except Exception as e:
            print(f"❌ Explanation error: {e}")
            return {"error": str(e)}
    
    def score_customer(self, features_dict: Dict) -> Dict:
        """
        Complete scoring pipeline for a customer
        Returns: Risk score, prediction, and explanation
        """
        # Prepare features
        features_df = self.prepare_features(features_dict)
        
        # Get prediction
        risk_score = self.predict_proba(features_df)
        prediction = self.predict(features_df)
        
        # Get explanation
        explanation = self.explain_prediction(features_df)
        
        # Determine risk level
        if risk_score >= 0.75:
            risk_level = "HIGH"
        elif risk_score >= 0.50:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            'risk_score': round(risk_score, 4),
            'prediction': 'Stressed' if prediction == 1 else 'Not Stressed',
            'risk_level': risk_level,
            'explanation': explanation,
            'model_version': self.metadata.get('model_type', 'Unknown') if self.metadata else 'Unknown'
        }
    
    def get_model_info(self) -> Dict:
        """Get model metadata and performance metrics"""
        if self.metadata is None:
            return {"error": "Model metadata not available"}
        
        return {
            'model_type': self.metadata.get('model_type'),
            'test_auc': self.metadata.get('test_auc'),
            'test_f1': self.metadata.get('test_f1'),
            'test_accuracy': self.metadata.get('test_acc'),
            'n_features': self.metadata.get('n_features'),
            'training_date': self.metadata.get('training_date'),
            'features': self.feature_columns[:10] if self.feature_columns else []
        }

if __name__ == "__main__":
    # Test model loading and prediction
    model = FinancialStressModel()
    
    if model.load_model():
        print("\n📊 Model Information:")
        info = model.get_model_info()
        for key, value in info.items():
            print(f"   {key}: {value}")
        
        # Test prediction with dummy features
        print("\n🧪 Testing prediction with dummy features...")
        dummy_features = {
            'days_since_last_salary': 45,
            'avg_salary_amount': 50000,
            'balance_drop_pct_4weeks': 35,
            'upi_to_loan_apps_pct': 25,
            'failed_autopay_count': 3
        }
        
        result = model.score_customer(dummy_features)
        
        print(f"\n📈 Prediction Result:")
        print(f"   Risk Score: {result['risk_score']}")
        print(f"   Prediction: {result['prediction']}")
        print(f"   Risk Level: {result['risk_level']}")
        
        if 'top_10_contributors' in result['explanation']:
            print(f"\n🔍 Top Risk Factors:")
            for feature, contribution in list(result['explanation']['top_10_contributors'].items())[:5]:
                print(f"   {feature}: {contribution:.4f}")
