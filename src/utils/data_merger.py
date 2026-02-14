"""
Data Merger - Combines Kaggle datasets with synthetic transaction data
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional

class DataMerger:
    """Merge and prepare datasets for feature engineering"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    def load_kaggle_data(self) -> Optional[pd.DataFrame]:
        """Load and combine Kaggle datasets"""
        dfs = []
        
        # Try to load GiveMeSomeCredit
        gmc_path = self.raw_dir / "give_me_credit" / "cs-training.csv"
        if gmc_path.exists():
            print(f"Loading GiveMeSomeCredit from {gmc_path}")
            gmc_df = pd.read_csv(gmc_path)
            
            # Rename columns for consistency
            gmc_df = gmc_df.rename(columns={
                'SeriousDlqin2yrs': 'target',
                'RevolvingUtilizationOfUnsecuredLines': 'revolving_utilization',
                'age': 'age',
                'NumberOfTime30-59DaysPastDueNotWorse': 'past_due_30_59_days',
                'DebtRatio': 'debt_ratio',
                'MonthlyIncome': 'monthly_income',
                'NumberOfOpenCreditLinesAndLoans': 'open_credit_lines',
                'NumberOfTimes90DaysLate': 'times_90_days_late',
                'NumberRealEstateLoansOrLines': 'real_estate_loans',
                'NumberOfTime60-89DaysPastDueNotWorse': 'past_due_60_89_days',
                'NumberOfDependents': 'dependents'
            })
            
            # Add source
            gmc_df['data_source'] = 'givemesomecredit'
            dfs.append(gmc_df)
            print(f"   Loaded {len(gmc_df)} records")
        
        # Try to load Home Credit
        hc_path = self.raw_dir / "home_credit" / "application_train.csv"
        if hc_path.exists():
            print(f"Loading Home Credit from {hc_path}")
            hc_df = pd.read_csv(hc_path)
            
            # Select relevant columns and rename
            hc_subset = pd.DataFrame({
                'target': hc_df['TARGET'],
                'age': (hc_df['DAYS_BIRTH'] / -365).astype(int),
                'monthly_income': hc_df['AMT_INCOME_TOTAL'] / 12,
                'debt_ratio': hc_df['AMT_CREDIT'] / hc_df['AMT_INCOME_TOTAL'].replace(0, 1),
                'dependents': hc_df['CNT_CHILDREN'],
                'data_source': 'homecredit'
            })
            
            dfs.append(hc_subset)
            print(f"   Loaded {len(hc_subset)} records")
        
        if len(dfs) == 0:
            print("⚠️ No Kaggle datasets found")
            return None
        
        # Combine datasets
        combined_df = pd.concat(dfs, ignore_index=True)
        print(f"✅ Combined Kaggle data: {len(combined_df)} total records")
        
        return combined_df
    
    def load_synthetic_data(self) -> Optional[pd.DataFrame]:
        """Load synthetic transaction data"""
        synthetic_path = self.raw_dir / "synthetic_transactions.csv"
        
        if synthetic_path.exists():
            print(f"Loading synthetic data from {synthetic_path}")
            df = pd.read_csv(synthetic_path)
            df['transaction_date'] = pd.to_datetime(df['transaction_date'])
            print(f"✅ Loaded {len(df)} synthetic transactions")
            return df
        else:
            print("⚠️ Synthetic data not found")
            return None
    
    def merge_datasets(self, kaggle_df: pd.DataFrame, 
                      synthetic_df: pd.DataFrame) -> pd.DataFrame:
        """
        Merge Kaggle customer data with synthetic transactions
        Creates customer IDs and assigns transactions
        """
        print("\nMerging datasets...")
        
        # Prepare Kaggle data
        kaggle_df = kaggle_df.copy()
        kaggle_df['customer_id'] = kaggle_df.index + 10000  # Offset to avoid conflicts
        
        # Get unique customers from synthetic data
        synthetic_customers = synthetic_df.groupby('customer_id').first().reset_index()
        
        # Combine customer profiles
        kaggle_customers = kaggle_df[['customer_id', 'age', 'monthly_income', 'target', 
                                       'debt_ratio', 'data_source']].copy()
        kaggle_customers['is_stressed'] = kaggle_customers['target']
        
        synthetic_customers_profile = synthetic_customers[
            ['customer_id', 'age', 'monthly_income', 'location', 
             'account_age_months', 'is_stressed', 'credit_score']
        ]
        
        # Get all transactions for synthetic customers
        all_transactions = synthetic_df.copy()
        
        print(f"   Kaggle customers: {len(kaggle_customers)}")
        print(f"   Synthetic customers: {len(synthetic_customers_profile)}")
        print(f"   Total transactions: {len(all_transactions)}")
        
        # Save merged data
        kaggle_customers.to_csv(
            self.processed_dir / "customer_profiles_kaggle.csv", 
            index=False
        )
        synthetic_customers_profile.to_csv(
            self.processed_dir / "customer_profiles_synthetic.csv",
            index=False
        )
        all_transactions.to_csv(
            self.processed_dir / "all_transactions.csv",
            index=False
        )
        
        print(f"\n✅ Saved processed data to {self.processed_dir}")
        
        return all_transactions
    
    def prepare_final_dataset(self):
        """Complete data preparation pipeline"""
        print("=" * 60)
        print("DATA PREPARATION PIPELINE")
        print("=" * 60)
        
        # Load data
        kaggle_df = self.load_kaggle_data()
        synthetic_df = self.load_synthetic_data()
        
        # If no Kaggle data, just use synthetic
        if kaggle_df is None:
            print("\n⚠️ Using only synthetic data")
            if synthetic_df is not None:
                synthetic_df.to_csv(
                    self.processed_dir / "all_transactions.csv",
                    index=False
                )
                customers = synthetic_df.groupby('customer_id').first().reset_index()
                customers.to_csv(
                    self.processed_dir / "customer_profiles_synthetic.csv",
                    index=False
                )
                return synthetic_df
            else:
                print("❌ No data available")
                return None
        
        # Merge if both exist
        if synthetic_df is not None:
            merged_df = self.merge_datasets(kaggle_df, synthetic_df)
            return merged_df
        else:
            print("\n⚠️ Using only Kaggle data")
            kaggle_df.to_csv(
                self.processed_dir / "customer_profiles_kaggle.csv",
                index=False
            )
            return kaggle_df

if __name__ == "__main__":
    merger = DataMerger()
    final_df = merger.prepare_final_dataset()
    
    if final_df is not None:
        print("\n" + "=" * 60)
        print("DATASET SUMMARY")
        print("=" * 60)
        print(f"Total records: {len(final_df)}")
        print(f"\nColumns: {list(final_df.columns)}")
        print(f"\nSample data:")
        print(final_df.head())
