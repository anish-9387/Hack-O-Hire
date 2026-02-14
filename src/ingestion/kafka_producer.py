"""
Kafka Producer - Simulates real-time transaction events
"""
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List
from kafka import KafkaProducer
from kafka.errors import KafkaError
import pandas as pd
import numpy as np

class TransactionEventProducer:
    """Produces transaction events to Kafka topic"""
    
    def __init__(self, bootstrap_servers: List[str] = ['localhost:9092'],
                 topic: str = 'bank-transactions'):
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        
    def connect(self):
        """Connect to Kafka broker"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda v: str(v).encode('utf-8') if v else None
            )
            print(f"✅ Connected to Kafka at {self.bootstrap_servers}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Kafka: {e}")
            print("Note: Make sure Kafka is running locally")
            return False
    
    def create_transaction_event(self, customer_id: int, 
                                 transaction_type: str = None) -> Dict:
        """Create a random transaction event"""
        
        if transaction_type is None:
            transaction_type = random.choice([
                'salary_credit', 'upi_debit', 'atm_withdrawal',
                'bill_payment', 'pos_debit'
            ])
        
        # Generate transaction based on type
        if transaction_type == 'salary_credit':
            amount = random.uniform(25000, 150000)
            category = 'income'
            description = 'Monthly Salary Credit'
        
        elif transaction_type == 'upi_debit':
            categories = ['loan_apps', 'food_delivery', 'ecommerce', 
                         'entertainment', 'bills', 'peer_transfer']
            category = random.choice(categories)
            
            if category == 'loan_apps':
                amount = -random.uniform(500, 5000)
                description = f'UPI to {random.choice(["MoneyTap", "CashBean", "EarlySalary"])}'
            else:
                amount = -random.uniform(50, 2000)
                description = f'UPI to {category}_merchant_{random.randint(1, 100)}'
        
        elif transaction_type == 'atm_withdrawal':
            amount = -random.uniform(1000, 8000)
            category = 'cash_withdrawal'
            description = 'ATM Cash Withdrawal'
        
        elif transaction_type == 'bill_payment':
            bills = ['electricity', 'internet', 'mobile', 'water', 'rent']
            category = random.choice(bills)
            amount = -random.uniform(500, 5000)
            description = f'{category.title()} Bill Payment'
        
        else:  # pos_debit
            categories = ['dining', 'entertainment', 'shopping', 'travel']
            category = random.choice(categories)
            amount = -random.uniform(300, 5000)
            description = f'{category.title()} Purchase'
        
        # Create event
        event = {
            'customer_id': customer_id,
            'transaction_id': f'TXN_{int(time.time() * 1000)}_{random.randint(1000, 9999)}',
            'transaction_date': datetime.now().isoformat(),
            'transaction_type': transaction_type,
            'amount': round(amount, 2),
            'category': category,
            'description': description,
            'merchant_id': f'MERCH_{random.randint(1000, 9999)}',
            'status': 'completed'
        }
        
        return event
    
    def send_event(self, event: Dict):
        """Send transaction event to Kafka"""
        if self.producer is None:
            if not self.connect():
                return False
        
        try:
            # Send event with customer_id as key for partitioning
            future = self.producer.send(
                self.topic,
                key=event['customer_id'],
                value=event
            )
            
            # Wait for send to complete
            record_metadata = future.get(timeout=10)
            
            print(f"✅ Sent: {event['transaction_type']} | "
                  f"Customer: {event['customer_id']} | "
                  f"Amount: ₹{event['amount']:.2f}")
            
            return True
            
        except KafkaError as e:
            print(f"❌ Failed to send event: {e}")
            return False
    
    def simulate_customer_activity(self, customer_id: int, 
                                   num_transactions: int = 10,
                                   delay_seconds: float = 1.0):
        """Simulate transaction activity for a customer"""
        print(f"\n{'='*60}")
        print(f"Simulating {num_transactions} transactions for customer {customer_id}")
        print(f"{'='*60}")
        
        for i in range(num_transactions):
            event = self.create_transaction_event(customer_id)
            self.send_event(event)
            time.sleep(delay_seconds)
        
        print(f"\n✅ Completed simulation for customer {customer_id}")
    
    def simulate_multiple_customers(self, customer_ids: List[int],
                                   transactions_per_customer: int = 5,
                                   delay_seconds: float = 0.5):
        """Simulate transactions for multiple customers"""
        print(f"\n{'='*60}")
        print(f"Simulating transactions for {len(customer_ids)} customers")
        print(f"{'='*60}")
        
        for customer_id in customer_ids:
            for _ in range(transactions_per_customer):
                event = self.create_transaction_event(customer_id)
                self.send_event(event)
                time.sleep(delay_seconds)
        
        print(f"\n✅ Simulation completed for all customers")
    
    def simulate_continuous_stream(self, customer_ids: List[int],
                                  rate_per_second: int = 10):
        """
        Continuously generate transaction events
        Press Ctrl+C to stop
        """
        print(f"\n{'='*60}")
        print(f"Starting continuous transaction stream")
        print(f"Rate: {rate_per_second} transactions/second")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*60}\n")
        
        delay = 1.0 / rate_per_second
        
        try:
            while True:
                customer_id = random.choice(customer_ids)
                event = self.create_transaction_event(customer_id)
                self.send_event(event)
                time.sleep(delay)
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopped continuous stream")
            self.close()
    
    def close(self):
        """Close Kafka producer connection"""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            print("✅ Kafka producer closed")

if __name__ == "__main__":
    # Example usage
    producer = TransactionEventProducer()
    
    if producer.connect():
        # Simulate transactions for a few customers
        customer_ids = [1001, 1002, 1003, 1004, 1005]
        
        # Option 1: Fixed number of transactions
        # producer.simulate_multiple_customers(customer_ids, transactions_per_customer=5)
        
        # Option 2: Continuous stream (uncomment to use)
        producer.simulate_continuous_stream(customer_ids, rate_per_second=5)
