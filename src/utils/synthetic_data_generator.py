"""
Synthetic Transaction Data Generator
Generates realistic banking transaction patterns with stress signals
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
import random

class SyntheticTransactionGenerator:
    """Generate synthetic transaction data for financial stress detection"""
    
    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        random.seed(seed)
        
        # Transaction categories
        self.upi_categories = [
            'loan_apps', 'food_delivery', 'ecommerce', 'entertainment',
            'bills', 'peer_transfer', 'groceries', 'transport'
        ]
        
        self.loan_apps = [
            'MoneyTap', 'CashBean', 'EarlySalary', 'mPokket', 
            'PaySense', 'CreditBee', 'Navi', 'KreditBee'
        ]
        
    def generate_customer_profile(self, customer_id: int, is_stressed: bool = False) -> Dict:
        """Generate customer demographic profile"""
        base_income = np.random.choice([25000, 35000, 50000, 75000, 100000, 150000])
        
        profile = {
            'customer_id': customer_id,
            'age': np.random.randint(22, 65),
            'monthly_income': base_income,
            'location': np.random.choice(['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad']),
            'account_age_months': np.random.randint(6, 120),
            'is_stressed': is_stressed,
            'credit_score': np.random.randint(300, 850) if not is_stressed else np.random.randint(300, 650)
        }
        
        return profile
    
    def generate_salary_credits(self, customer_id: int, monthly_income: float, 
                                num_months: int = 6, is_stressed: bool = False) -> pd.DataFrame:
        """Generate salary credit transactions"""
        transactions = []
        base_date = datetime.now() - timedelta(days=num_months * 30)
        
        for month in range(num_months):
            # Normal: salary on 1st-5th of month
            # Stressed: delays increase over time
            if is_stressed and month >= num_months // 2:
                salary_day = np.random.randint(1, 15)  # Increasing delays
            else:
                salary_day = np.random.randint(1, 6)
            
            salary_date = base_date + timedelta(days=month * 30 + salary_day)
            
            # Salary amount variation
            salary_variance = np.random.uniform(0.95, 1.05)
            amount = monthly_income * salary_variance
            
            transactions.append({
                'customer_id': customer_id,
                'transaction_date': salary_date,
                'transaction_type': 'salary_credit',
                'amount': amount,
                'category': 'income',
                'description': 'Monthly Salary Credit'
            })
        
        return pd.DataFrame(transactions)
    
    def generate_upi_transactions(self, customer_id: int, monthly_income: float,
                                  num_days: int = 180, is_stressed: bool = False) -> pd.DataFrame:
        """Generate UPI transaction history"""
        transactions = []
        base_date = datetime.now() - timedelta(days=num_days)
        
        # UPI frequency: 3-10 transactions per day
        daily_txn_count = np.random.randint(3, 10)
        
        for day in range(num_days):
            current_date = base_date + timedelta(days=day)
            
            for _ in range(daily_txn_count):
                # Determine category
                if is_stressed and day > num_days // 2:
                    # Increase loan app usage for stressed customers
                    if np.random.random() < 0.3:  # 30% chance
                        category = 'loan_apps'
                        merchant = np.random.choice(self.loan_apps)
                    else:
                        category = np.random.choice(self.upi_categories)
                        merchant = f"{category}_merchant_{np.random.randint(1, 100)}"
                else:
                    category = np.random.choice(self.upi_categories)
                    merchant = f"{category}_merchant_{np.random.randint(1, 100)}"
                
                # Transaction amount based on category
                if category == 'loan_apps':
                    amount = np.random.uniform(500, 5000)
                elif category in ['ecommerce', 'entertainment']:
                    amount = np.random.uniform(200, 3000)
                elif category == 'food_delivery':
                    amount = np.random.uniform(100, 800)
                else:
                    amount = np.random.uniform(50, 1500)
                
                transactions.append({
                    'customer_id': customer_id,
                    'transaction_date': current_date + timedelta(hours=np.random.randint(0, 24)),
                    'transaction_type': 'upi_debit',
                    'amount': -amount,
                    'category': category,
                    'description': f'UPI to {merchant}'
                })
        
        return pd.DataFrame(transactions)
    
    def generate_atm_withdrawals(self, customer_id: int, monthly_income: float,
                                 num_months: int = 6, is_stressed: bool = False) -> pd.DataFrame:
        """Generate ATM withdrawal patterns"""
        transactions = []
        base_date = datetime.now() - timedelta(days=num_months * 30)
        
        # Withdrawals per month
        monthly_withdrawals = 4 if not is_stressed else 8
        
        for month in range(num_months):
            for _ in range(monthly_withdrawals):
                withdrawal_date = base_date + timedelta(
                    days=month * 30 + np.random.randint(0, 30)
                )
                
                # Stressed customers withdraw more frequently
                if is_stressed:
                    amount = np.random.uniform(2000, 8000)
                else:
                    amount = np.random.uniform(1000, 5000)
                
                transactions.append({
                    'customer_id': customer_id,
                    'transaction_date': withdrawal_date,
                    'transaction_type': 'atm_withdrawal',
                    'amount': -amount,
                    'category': 'cash_withdrawal',
                    'description': 'ATM Cash Withdrawal'
                })
        
        return pd.DataFrame(transactions)
    
    def generate_bill_payments(self, customer_id: int, monthly_income: float,
                               num_months: int = 6, is_stressed: bool = False) -> pd.DataFrame:
        """Generate utility bill payments"""
        transactions = []
        base_date = datetime.now() - timedelta(days=num_months * 30)
        
        bills = {
            'electricity': np.random.uniform(1000, 3000),
            'internet': np.random.uniform(500, 1500),
            'mobile': np.random.uniform(300, 800),
            'water': np.random.uniform(200, 600),
            'rent': monthly_income * 0.3  # 30% of income
        }
        
        for month in range(num_months):
            for bill_type, base_amount in bills.items():
                # Stressed customers delay payments
                if is_stressed and month >= num_months // 2:
                    payment_day = np.random.randint(10, 30)  # Late payments
                else:
                    payment_day = np.random.randint(1, 10)
                
                payment_date = base_date + timedelta(days=month * 30 + payment_day)
                amount = base_amount * np.random.uniform(0.9, 1.1)
                
                transactions.append({
                    'customer_id': customer_id,
                    'transaction_date': payment_date,
                    'transaction_type': 'bill_payment',
                    'amount': -amount,
                    'category': bill_type,
                    'description': f'{bill_type.title()} Bill Payment'
                })
        
        return pd.DataFrame(transactions)
    
    def generate_discretionary_spends(self, customer_id: int, monthly_income: float,
                                      num_months: int = 6, is_stressed: bool = False) -> pd.DataFrame:
        """Generate discretionary spending (entertainment, dining)"""
        transactions = []
        base_date = datetime.now() - timedelta(days=num_months * 30)
        
        categories = {
            'dining': (300, 2000),
            'entertainment': (500, 3000),
            'shopping': (1000, 5000),
            'travel': (2000, 10000)
        }
        
        for month in range(num_months):
            # Stressed customers reduce discretionary spending
            if is_stressed and month >= num_months // 2:
                txn_multiplier = 0.3  # 70% reduction
            else:
                txn_multiplier = 1.0
            
            for category, (min_amt, max_amt) in categories.items():
                num_txns = int(np.random.randint(2, 8) * txn_multiplier)
                
                for _ in range(num_txns):
                    txn_date = base_date + timedelta(
                        days=month * 30 + np.random.randint(0, 30)
                    )
                    amount = np.random.uniform(min_amt, max_amt)
                    
                    transactions.append({
                        'customer_id': customer_id,
                        'transaction_date': txn_date,
                        'transaction_type': 'pos_debit',
                        'amount': -amount,
                        'category': category,
                        'description': f'{category.title()} Purchase'
                    })
        
        return pd.DataFrame(transactions)
    
    def generate_complete_customer_data(self, customer_id: int, 
                                       is_stressed: bool = False) -> pd.DataFrame:
        """Generate complete transaction history for a customer"""
        # Generate profile
        profile = self.generate_customer_profile(customer_id, is_stressed)
        
        # Generate all transaction types
        transactions = []
        
        transactions.append(self.generate_salary_credits(
            customer_id, profile['monthly_income'], is_stressed=is_stressed
        ))
        
        transactions.append(self.generate_upi_transactions(
            customer_id, profile['monthly_income'], is_stressed=is_stressed
        ))
        
        transactions.append(self.generate_atm_withdrawals(
            customer_id, profile['monthly_income'], is_stressed=is_stressed
        ))
        
        transactions.append(self.generate_bill_payments(
            customer_id, profile['monthly_income'], is_stressed=is_stressed
        ))
        
        transactions.append(self.generate_discretionary_spends(
            customer_id, profile['monthly_income'], is_stressed=is_stressed
        ))
        
        # Combine all transactions
        all_txns = pd.concat(transactions, ignore_index=True)
        all_txns = all_txns.sort_values('transaction_date').reset_index(drop=True)
        
        # Add profile columns
        for key, value in profile.items():
            all_txns[key] = value
        
        return all_txns
    
    def generate_dataset(self, num_customers: int = 1000, 
                        stress_ratio: float = 0.3) -> pd.DataFrame:
        """Generate complete synthetic dataset"""
        print(f"Generating synthetic data for {num_customers} customers...")
        
        num_stressed = int(num_customers * stress_ratio)
        num_normal = num_customers - num_stressed
        
        all_customer_data = []
        
        # Generate normal customers
        for i in range(num_normal):
            if i % 100 == 0:
                print(f"Generated {i} normal customers...")
            customer_data = self.generate_complete_customer_data(i, is_stressed=False)
            all_customer_data.append(customer_data)
        
        # Generate stressed customers
        for i in range(num_stressed):
            if i % 100 == 0:
                print(f"Generated {i} stressed customers...")
            customer_id = num_normal + i
            customer_data = self.generate_complete_customer_data(customer_id, is_stressed=True)
            all_customer_data.append(customer_data)
        
        # Combine all data
        final_df = pd.concat(all_customer_data, ignore_index=True)
        
        print(f"✅ Generated {len(final_df)} transactions for {num_customers} customers")
        print(f"   - Normal customers: {num_normal}")
        print(f"   - Stressed customers: {num_stressed}")
        
        return final_df

if __name__ == "__main__":
    generator = SyntheticTransactionGenerator()
    
    # Generate dataset
    df = generator.generate_dataset(num_customers=1000, stress_ratio=0.3)
    
    # Save to file
    output_path = "data/raw/synthetic_transactions.csv"
    df.to_csv(output_path, index=False)
    print(f"\n✅ Saved synthetic data to {output_path}")
    
    # Display sample
    print("\nSample transactions:")
    print(df.head(20))
    
    print("\nTransaction type distribution:")
    print(df['transaction_type'].value_counts())
