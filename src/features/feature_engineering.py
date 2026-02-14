"""
Feature Engineering for Financial Stress Prediction
Calculates behavioral patterns from transaction data
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List

class FinancialFeatureEngine:
    """Extract features from transaction data for stress prediction"""
    
    def __init__(self):
        self.loan_apps = [
            'MoneyTap', 'CashBean', 'EarlySalary', 'mPokket', 
            'PaySense', 'CreditBee', 'Navi', 'KreditBee'
        ]
    
    def calculate_salary_features(self, transactions: pd.DataFrame) -> Dict:
        """Calculate salary-related features"""
        salary_txns = transactions[transactions['transaction_type'] == 'salary_credit'].copy()
        
        if len(salary_txns) == 0:
            return {
                'days_since_last_salary': 999,
                'avg_salary_amount': 0,
                'salary_delay_trend': 0,
                'salary_variance': 0,
                'months_with_salary': 0
            }
        
        salary_txns = salary_txns.sort_values('transaction_date')
        
        # Days since last salary
        last_salary_date = salary_txns['transaction_date'].max()
        days_since_last = (datetime.now() - last_salary_date).days
        
        # Average salary amount
        avg_salary = salary_txns['amount'].mean()
        salary_variance = salary_txns['amount'].std() / (avg_salary + 1)
        
        # Salary delay trend (are salary dates getting later in month?)
        salary_txns['day_of_month'] = salary_txns['transaction_date'].dt.day
        if len(salary_txns) >= 3:
            salary_delay_trend = np.polyfit(range(len(salary_txns)), 
                                           salary_txns['day_of_month'], 1)[0]
        else:
            salary_delay_trend = 0
        
        return {
            'days_since_last_salary': days_since_last,
            'avg_salary_amount': avg_salary,
            'salary_delay_trend': salary_delay_trend,
            'salary_variance': float(salary_variance),
            'months_with_salary': len(salary_txns)
        }
    
    def calculate_balance_features(self, transactions: pd.DataFrame) -> Dict:
        """Calculate balance and spending patterns"""
        transactions = transactions.sort_values('transaction_date')
        
        # Calculate running balance
        transactions['running_balance'] = transactions['amount'].cumsum()
        
        # Weekly balance trends
        transactions['week'] = transactions['transaction_date'].dt.isocalendar().week
        weekly_balance = transactions.groupby('week')['running_balance'].last()
        
        if len(weekly_balance) >= 4:
            recent_4_weeks = weekly_balance.tail(4)
            balance_drop_pct = ((recent_4_weeks.iloc[0] - recent_4_weeks.iloc[-1]) / 
                               (abs(recent_4_weeks.iloc[0]) + 1)) * 100
            
            # Week-over-week decline trend
            balance_trend = np.polyfit(range(len(recent_4_weeks)), recent_4_weeks, 1)[0]
        else:
            balance_drop_pct = 0
            balance_trend = 0
        
        # Current balance
        current_balance = transactions['running_balance'].iloc[-1]
        
        # Minimum balance in last 30 days
        last_30_days = transactions[
            transactions['transaction_date'] >= (datetime.now() - timedelta(days=30))
        ]
        min_balance_30d = last_30_days['running_balance'].min() if len(last_30_days) > 0 else 0
        
        return {
            'current_balance': current_balance,
            'min_balance_30d': min_balance_30d,
            'balance_drop_pct_4weeks': balance_drop_pct,
            'balance_trend': balance_trend,
            'avg_daily_balance': transactions['running_balance'].mean()
        }
    
    def calculate_upi_features(self, transactions: pd.DataFrame) -> Dict:
        """Calculate UPI spending patterns"""
        upi_txns = transactions[transactions['transaction_type'] == 'upi_debit'].copy()
        
        if len(upi_txns) == 0:
            return {
                'upi_to_loan_apps_pct': 0,
                'upi_to_loan_apps_count': 0,
                'total_upi_count': 0,
                'avg_upi_amount': 0,
                'upi_loan_amount_30d': 0
            }
        
        # Identify loan app transactions
        upi_txns['is_loan_app'] = upi_txns['description'].apply(
            lambda x: any(app in str(x) for app in self.loan_apps)
        ) | (upi_txns['category'] == 'loan_apps')
        
        loan_app_txns = upi_txns[upi_txns['is_loan_app']]
        
        # Percentage of UPI to loan apps
        total_upi_count = len(upi_txns)
        loan_app_count = len(loan_app_txns)
        loan_app_pct = (loan_app_count / total_upi_count * 100) if total_upi_count > 0 else 0
        
        # Last 30 days loan app spending
        last_30_days = datetime.now() - timedelta(days=30)
        recent_loan_txns = loan_app_txns[loan_app_txns['transaction_date'] >= last_30_days]
        loan_amount_30d = abs(recent_loan_txns['amount'].sum())
        
        return {
            'upi_to_loan_apps_pct': loan_app_pct,
            'upi_to_loan_apps_count': loan_app_count,
            'total_upi_count': total_upi_count,
            'avg_upi_amount': abs(upi_txns['amount'].mean()),
            'upi_loan_amount_30d': loan_amount_30d
        }
    
    def calculate_spend_category_ratios(self, transactions: pd.DataFrame) -> Dict:
        """Calculate spending distribution across categories"""
        # Get all debit transactions
        debits = transactions[transactions['amount'] < 0].copy()
        total_spending = abs(debits['amount'].sum())
        
        if total_spending == 0:
            return {
                'essential_spend_ratio': 0,
                'discretionary_spend_ratio': 0,
                'cash_withdrawal_ratio': 0
            }
        
        # Essential categories
        essential_categories = ['bills', 'electricity', 'internet', 'mobile', 'water', 'rent', 'groceries']
        essential_spending = abs(debits[debits['category'].isin(essential_categories)]['amount'].sum())
        
        # Discretionary categories
        discretionary_categories = ['dining', 'entertainment', 'shopping', 'travel', 'food_delivery']
        discretionary_spending = abs(debits[debits['category'].isin(discretionary_categories)]['amount'].sum())
        
        # Cash withdrawals
        cash_spending = abs(debits[debits['transaction_type'] == 'atm_withdrawal']['amount'].sum())
        
        return {
            'essential_spend_ratio': essential_spending / total_spending,
            'discretionary_spend_ratio': discretionary_spending / total_spending,
            'cash_withdrawal_ratio': cash_spending / total_spending
        }
    
    def calculate_payment_behavior(self, transactions: pd.DataFrame) -> Dict:
        """Calculate bill payment patterns"""
        bill_txns = transactions[transactions['transaction_type'] == 'bill_payment'].copy()
        
        if len(bill_txns) == 0:
            return {
                'avg_bill_payment_day': 0,
                'bill_payment_delay_trend': 0,
                'failed_autopay_count': 0
            }
        
        bill_txns = bill_txns.sort_values('transaction_date')
        bill_txns['day_of_month'] = bill_txns['transaction_date'].dt.day
        
        avg_payment_day = bill_txns['day_of_month'].mean()
        
        # Payment delay trend
        if len(bill_txns) >= 3:
            payment_trend = np.polyfit(range(len(bill_txns)), 
                                       bill_txns['day_of_month'], 1)[0]
        else:
            payment_trend = 0
        
        # Simulate failed autopay (payments after day 20)
        late_payments = len(bill_txns[bill_txns['day_of_month'] > 20])
        
        return {
            'avg_bill_payment_day': avg_payment_day,
            'bill_payment_delay_trend': payment_trend,
            'failed_autopay_count': late_payments
        }
    
    def calculate_atm_features(self, transactions: pd.DataFrame) -> Dict:
        """Calculate ATM withdrawal patterns"""
        atm_txns = transactions[transactions['transaction_type'] == 'atm_withdrawal'].copy()
        
        if len(atm_txns) == 0:
            return {
                'atm_withdrawal_count_30d': 0,
                'atm_withdrawal_amount_30d': 0,
                'avg_atm_amount': 0
            }
        
        # Last 30 days
        last_30_days = datetime.now() - timedelta(days=30)
        recent_atm = atm_txns[atm_txns['transaction_date'] >= last_30_days]
        
        return {
            'atm_withdrawal_count_30d': len(recent_atm),
            'atm_withdrawal_amount_30d': abs(recent_atm['amount'].sum()),
            'avg_atm_amount': abs(atm_txns['amount'].mean())
        }
    
    def calculate_transaction_velocity(self, transactions: pd.DataFrame) -> Dict:
        """Calculate transaction frequency patterns"""
        # Last 30 days
        last_30_days = datetime.now() - timedelta(days=30)
        recent_txns = transactions[transactions['transaction_date'] >= last_30_days]
        
        # Last 7 days
        last_7_days = datetime.now() - timedelta(days=7)
        very_recent_txns = transactions[transactions['transaction_date'] >= last_7_days]
        
        return {
            'txn_count_30d': len(recent_txns),
            'txn_count_7d': len(very_recent_txns),
            'avg_txn_per_day': len(recent_txns) / 30 if len(recent_txns) > 0 else 0,
            'debit_count_30d': len(recent_txns[recent_txns['amount'] < 0]),
            'credit_count_30d': len(recent_txns[recent_txns['amount'] > 0])
        }
    
    def engineer_features(self, transactions: pd.DataFrame, customer_id: int) -> pd.DataFrame:
        """
        Generate all features for a customer
        Returns a single-row DataFrame with all features
        """
        customer_txns = transactions[transactions['customer_id'] == customer_id].copy()
        
        if len(customer_txns) == 0:
            return pd.DataFrame()
        
        # Calculate all feature groups
        features = {
            'customer_id': customer_id,
            'timestamp': datetime.now()
        }
        
        # Add customer profile features
        profile_cols = ['age', 'monthly_income', 'location', 'account_age_months', 
                       'is_stressed', 'credit_score']
        for col in profile_cols:
            if col in customer_txns.columns:
                features[col] = customer_txns[col].iloc[0]
        
        # Calculate behavioral features
        features.update(self.calculate_salary_features(customer_txns))
        features.update(self.calculate_balance_features(customer_txns))
        features.update(self.calculate_upi_features(customer_txns))
        features.update(self.calculate_spend_category_ratios(customer_txns))
        features.update(self.calculate_payment_behavior(customer_txns))
        features.update(self.calculate_atm_features(customer_txns))
        features.update(self.calculate_transaction_velocity(customer_txns))
        
        return pd.DataFrame([features])
    
    def engineer_features_batch(self, transactions: pd.DataFrame) -> pd.DataFrame:
        """Engineer features for all customers in batch"""
        print("Engineering features for all customers...")
        
        customer_ids = transactions['customer_id'].unique()
        all_features = []
        
        for i, customer_id in enumerate(customer_ids):
            if i % 100 == 0:
                print(f"  Processed {i}/{len(customer_ids)} customers...")
            
            customer_features = self.engineer_features(transactions, customer_id)
            if len(customer_features) > 0:
                all_features.append(customer_features)
        
        features_df = pd.concat(all_features, ignore_index=True)
        print(f"✅ Engineered {len(features_df.columns)} features for {len(features_df)} customers")
        
        return features_df

if __name__ == "__main__":
    from pathlib import Path
    
    # Load transaction data
    data_path = Path("data/processed/all_transactions.csv")
    
    if data_path.exists():
        print(f"Loading transactions from {data_path}")
        transactions = pd.read_csv(data_path)
        transactions['transaction_date'] = pd.to_datetime(transactions['transaction_date'])
        
        # Engineer features
        engine = FinancialFeatureEngine()
        features = engine.engineer_features_batch(transactions)
        
        # Save features
        output_path = Path("data/processed/engineered_features.csv")
        features.to_csv(output_path, index=False)
        print(f"\n✅ Saved features to {output_path}")
        
        print("\nFeature columns:")
        for col in features.columns:
            print(f"  - {col}")
        
        print("\nSample features:")
        print(features.head())
    else:
        print(f"❌ Transaction data not found at {data_path}")
        print("Please run the data generation scripts first")
