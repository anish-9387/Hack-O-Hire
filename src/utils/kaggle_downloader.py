"""
Kaggle Dataset Downloader for Financial Stress Prediction
Downloads datasets from Kaggle competitions
"""
import os
import opendatasets as od
import pandas as pd
from pathlib import Path

class KaggleDownloader:
    """Download and prepare Kaggle datasets"""
    
    def __init__(self, data_dir: str = "data/raw"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def download_give_me_credit(self):
        """
        Download GiveMeSomeCredit dataset
        URL: https://www.kaggle.com/c/GiveMeSomeCredit
        """
        print("Downloading GiveMeSomeCredit dataset...")
        try:
            dataset_url = "https://www.kaggle.com/c/GiveMeSomeCredit"
            od.download(dataset_url, data_dir=str(self.data_dir / "give_me_credit"))
            print("✅ GiveMeSomeCredit dataset downloaded successfully")
            
            # Load and return the data
            data_path = self.data_dir / "give_me_credit" / "cs-training.csv"
            if data_path.exists():
                df = pd.read_csv(data_path)
                print(f"Loaded {len(df)} records with {len(df.columns)} columns")
                return df
            else:
                print("⚠️ Training data file not found in expected location")
                return None
                
        except Exception as e:
            print(f"❌ Error downloading GiveMeSomeCredit: {e}")
            print("Note: You may need to set up Kaggle API credentials")
            print("Place kaggle.json in ~/.kaggle/ directory")
            return None
    
    def download_home_credit(self):
        """
        Download Home Credit Default Risk dataset
        URL: https://www.kaggle.com/competitions/home-credit-default-risk
        """
        print("Downloading Home Credit Default Risk dataset...")
        try:
            dataset_url = "https://www.kaggle.com/competitions/home-credit-default-risk"
            od.download(dataset_url, data_dir=str(self.data_dir / "home_credit"))
            print("✅ Home Credit dataset downloaded successfully")
            
            # Load main application data
            data_path = self.data_dir / "home_credit" / "application_train.csv"
            if data_path.exists():
                df = pd.read_csv(data_path)
                print(f"Loaded {len(df)} records with {len(df.columns)} columns")
                return df
            else:
                print("⚠️ Application training data not found in expected location")
                return None
                
        except Exception as e:
            print(f"❌ Error downloading Home Credit: {e}")
            print("Note: You may need to set up Kaggle API credentials")
            return None
    
    def setup_kaggle_credentials(self):
        """
        Guide user to set up Kaggle API credentials
        """
        print("\n📋 Kaggle API Setup Instructions:")
        print("1. Go to https://www.kaggle.com/account")
        print("2. Scroll to 'API' section and click 'Create New Token'")
        print("3. This downloads kaggle.json")
        print("4. Place kaggle.json in:")
        print("   - Windows: C:\\Users\\<username>\\.kaggle\\kaggle.json")
        print("   - Linux/Mac: ~/.kaggle/kaggle.json")
        print("5. Run this script again")

if __name__ == "__main__":
    downloader = KaggleDownloader()
    
    # Try to download datasets
    give_me_credit_df = downloader.download_give_me_credit()
    home_credit_df = downloader.download_home_credit()
    
    if give_me_credit_df is None or home_credit_df is None:
        downloader.setup_kaggle_credentials()
