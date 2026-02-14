"""
Kafka Consumer - Processes real-time transaction events
"""
import json
import time
from typing import Dict, Callable, List
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.features.feature_engineering import FinancialFeatureEngine

class TransactionEventConsumer:
    """Consumes and processes transaction events from Kafka"""
    
    def __init__(self, bootstrap_servers: List[str] = ['localhost:9092'],
                 topic: str = 'bank-transactions',
                 group_id: str = 'transaction-processor'):
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.consumer = None
        self.feature_engine = FinancialFeatureEngine()
        
        # In-memory transaction store (for demo)
        self.transaction_buffer = []
        self.customer_transactions = {}
        
    def connect(self):
        """Connect to Kafka broker"""
        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda m: m.decode('utf-8') if m else None,
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            print(f"✅ Connected to Kafka topic '{self.topic}'")
            print(f"   Bootstrap servers: {self.bootstrap_servers}")
            print(f"   Consumer group: {self.group_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Kafka: {e}")
            return False
    
    def process_transaction(self, transaction: Dict) -> Dict:
        """
        Process single transaction event
        Returns processed transaction with enrichments
        """
        # Add processing timestamp
        transaction['processed_at'] = datetime.now().isoformat()
        
        # Store in buffer
        self.transaction_buffer.append(transaction)
        
        # Store by customer
        customer_id = transaction['customer_id']
        if customer_id not in self.customer_transactions:
            self.customer_transactions[customer_id] = []
        self.customer_transactions[customer_id].append(transaction)
        
        # Basic validation
        if abs(transaction['amount']) > 1000000:
            transaction['alert'] = 'HIGH_VALUE_TRANSACTION'
        
        return transaction
    
    def calculate_customer_features(self, customer_id: int) -> Dict:
        """Calculate real-time features for a customer"""
        if customer_id not in self.customer_transactions:
            return {}
        
        # Convert customer transactions to DataFrame
        txns_df = pd.DataFrame(self.customer_transactions[customer_id])
        txns_df['transaction_date'] = pd.to_datetime(txns_df['transaction_date'])
        
        # Add dummy customer_id column for feature engineering
        txns_df['customer_id'] = customer_id
        
        # Engineer features
        try:
            features = self.feature_engine.engineer_features(txns_df, customer_id)
            if len(features) > 0:
                return features.iloc[0].to_dict()
            else:
                return {}
        except Exception as e:
            print(f"❌ Error calculating features for customer {customer_id}: {e}")
            return {}
    
    def consume_events(self, callback: Callable = None, max_messages: int = None):
        """
        Consume events from Kafka topic
        
        Args:
            callback: Optional function to call for each message
            max_messages: Max number of messages to process (None = infinite)
        """
        if self.consumer is None:
            if not self.connect():
                return
        
        print(f"\n{'='*60}")
        print(f"Consuming messages from topic '{self.topic}'")
        if max_messages:
            print(f"Will process up to {max_messages} messages")
        else:
            print("Press Ctrl+C to stop")
        print(f"{'='*60}\n")
        
        message_count = 0
        
        try:
            for message in self.consumer:
                transaction = message.value
                
                # Process transaction
                processed = self.process_transaction(transaction)
                
                # Print transaction details
                print(f"\n📨 Received Transaction #{message_count + 1}")
                print(f"   Customer ID: {transaction['customer_id']}")
                print(f"   Type: {transaction['transaction_type']}")
                print(f"   Amount: ₹{transaction['amount']:.2f}")
                print(f"   Category: {transaction['category']}")
                print(f"   Time: {transaction['transaction_date']}")
                
                # Check for alerts
                if 'alert' in processed:
                    print(f"   🚨 ALERT: {processed['alert']}")
                
                # Call custom callback if provided
                if callback:
                    callback(processed)
                
                message_count += 1
                
                # Check if we've reached max messages
                if max_messages and message_count >= max_messages:
                    print(f"\n✅ Processed {message_count} messages. Stopping.")
                    break
                
        except KeyboardInterrupt:
            print(f"\n\n⏹️  Stopped consumer after processing {message_count} messages")
        
        finally:
            self.close()
    
    def consume_and_score(self, scoring_callback: Callable):
        """
        Consume events and score each transaction for risk
        
        Args:
            scoring_callback: Function that takes customer_id and features, returns risk score
        """
        if self.consumer is None:
            if not self.connect():
                return
        
        print(f"\n{'='*60}")
        print(f"Real-time Transaction Monitoring & Risk Scoring")
        print(f"{'='*60}\n")
        
        try:
            for message in self.consumer:
                transaction = message.value
                customer_id = transaction['customer_id']
                
                # Process transaction
                self.process_transaction(transaction)
                
                # Calculate features every N transactions
                if len(self.customer_transactions[customer_id]) % 5 == 0:
                    features = self.calculate_customer_features(customer_id)
                    
                    if features:
                        # Score customer
                        risk_score = scoring_callback(customer_id, features)
                        
                        print(f"\n📊 Risk Assessment for Customer {customer_id}")
                        print(f"   Transactions processed: {len(self.customer_transactions[customer_id])}")
                        print(f"   Risk Score: {risk_score:.4f}")
                        
                        if risk_score > 0.75:
                            print(f"   🚨 HIGH RISK DETECTED!")
                
        except KeyboardInterrupt:
            print(f"\n\n⏹️  Stopped real-time scoring")
        
        finally:
            self.close()
    
    def get_statistics(self) -> Dict:
        """Get consumer statistics"""
        return {
            'total_transactions': len(self.transaction_buffer),
            'unique_customers': len(self.customer_transactions),
            'avg_transactions_per_customer': len(self.transaction_buffer) / max(len(self.customer_transactions), 1)
        }
    
    def save_buffer_to_file(self, filepath: str):
        """Save transaction buffer to CSV file"""
        if len(self.transaction_buffer) > 0:
            df = pd.DataFrame(self.transaction_buffer)
            df.to_csv(filepath, index=False)
            print(f"✅ Saved {len(df)} transactions to {filepath}")
        else:
            print("⚠️ No transactions to save")
    
    def close(self):
        """Close Kafka consumer connection"""
        if self.consumer:
            self.consumer.close()
            print("\n✅ Kafka consumer closed")
            
            # Print statistics
            stats = self.get_statistics()
            print(f"\n📊 Session Statistics:")
            print(f"   Total transactions: {stats['total_transactions']}")
            print(f"   Unique customers: {stats['unique_customers']}")
            print(f"   Avg transactions/customer: {stats['avg_transactions_per_customer']:.1f}")

def custom_processor(transaction: Dict):
    """Example custom transaction processor"""
    # Add custom logic here
    if transaction['transaction_type'] == 'upi_debit':
        if 'loan' in transaction['description'].lower():
            print(f"   ⚠️ Loan app transaction detected")

if __name__ == "__main__":
    consumer = TransactionEventConsumer()
    
    # Option 1: Simple consumption with custom processor
    consumer.consume_events(callback=custom_processor, max_messages=20)
    
    # Option 2: Save consumed transactions
    # consumer.save_buffer_to_file('data/raw/consumed_transactions.csv')
