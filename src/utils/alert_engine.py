"""
Alert Engine for Financial Stress Detection
Triggers alerts when risk thresholds are exceeded
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import json

class AlertEngine:
    """Manages alerts for high-risk customers"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.alert_threshold = self.config.get('high_risk_threshold', 0.75)
        self.email_enabled = self.config.get('email_enabled', False)
        self.sms_enabled = self.config.get('sms_enabled', False)
        self.log_enabled = self.config.get('log_enabled', True)
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Alert history
        self.alert_history = []
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for alerts"""
        logger = logging.getLogger('AlertEngine')
        logger.setLevel(logging.INFO)
        
        # Create logs directory
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # File handler
        fh = logging.FileHandler(log_dir / 'alerts.log')
        fh.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def check_risk_level(self, risk_score: float) -> str:
        """Determine risk level from score"""
        if risk_score >= 0.75:
            return "HIGH"
        elif risk_score >= 0.50:
            return "MEDIUM"
        else:
            return "LOW"
    
    def should_alert(self, risk_score: float, risk_level: str = None) -> bool:
        """Determine if an alert should be triggered"""
        if risk_level is None:
            risk_level = self.check_risk_level(risk_score)
        
        return risk_level == "HIGH"
    
    def create_alert(self, customer_id: int, risk_score: float, 
                    explanation: Dict, additional_info: Dict = None) -> Dict:
        """Create alert object"""
        alert = {
            'alert_id': f"ALERT_{int(datetime.now().timestamp())}_{customer_id}",
            'customer_id': customer_id,
            'risk_score': risk_score,
            'risk_level': self.check_risk_level(risk_score),
            'timestamp': datetime.now().isoformat(),
            'explanation': explanation,
            'top_risk_factors': [],
            'recommended_actions': []
        }
        
        # Extract top risk factors
        if 'top_10_contributors' in explanation:
            alert['top_risk_factors'] = list(explanation['top_10_contributors'].items())[:5]
        
        # Generate recommended actions
        alert['recommended_actions'] = self._generate_recommendations(
            risk_score, explanation
        )
        
        # Add additional info
        if additional_info:
            alert.update(additional_info)
        
        return alert
    
    def _generate_recommendations(self, risk_score: float, 
                                 explanation: Dict) -> List[str]:
        """Generate intervention recommendations"""
        recommendations = []
        
        top_factors = explanation.get('top_10_contributors', {})
        
        # Check top risk factors
        for factor, contribution in top_factors.items():
            if 'loan_app' in factor.lower() and contribution > 0.1:
                recommendations.append(
                    "High usage of loan apps detected - Consider debt consolidation counseling"
                )
            
            if 'balance_drop' in factor.lower() and contribution > 0.1:
                recommendations.append(
                    "Significant balance decline - Offer financial planning assistance"
                )
            
            if 'salary_delay' in factor.lower() and contribution > 0.1:
                recommendations.append(
                    "Salary delays observed - Check employment stability"
                )
            
            if 'failed_autopay' in factor.lower() or 'payment_delay' in factor.lower():
                recommendations.append(
                    "Payment delays detected - Suggest payment holiday or restructuring"
                )
            
            if 'atm_withdrawal' in factor.lower() and contribution > 0.1:
                recommendations.append(
                    "Increased cash withdrawals - Monitor for liquidity stress"
                )
        
        # General recommendations
        if risk_score >= 0.85:
            recommendations.append(
                "URGENT: Immediate outreach required - Assign relationship manager"
            )
        elif risk_score >= 0.75:
            recommendations.append(
                "Proactive engagement recommended - Schedule customer meeting"
            )
        
        return list(set(recommendations))[:5]  # Max 5 unique recommendations
    
    def trigger_alert(self, customer_id: int, risk_score: float,
                     explanation: Dict, additional_info: Dict = None):
        """Trigger alert through configured channels"""
        
        # Check if alert should be triggered
        if not self.should_alert(risk_score):
            return None
        
        # Create alert
        alert = self.create_alert(customer_id, risk_score, explanation, additional_info)
        
        # Store in history
        self.alert_history.append(alert)
        
        # Send through enabled channels
        if self.log_enabled:
            self._log_alert(alert)
        
        if self.email_enabled:
            self._send_email_alert(alert)
        
        if self.sms_enabled:
            self._send_sms_alert(alert)
        
        return alert
    
    def _log_alert(self, alert: Dict):
        """Log alert to file"""
        self.logger.warning(
            f"🚨 HIGH RISK ALERT | Customer: {alert['customer_id']} | "
            f"Risk Score: {alert['risk_score']:.4f}"
        )
        
        self.logger.info(f"Top Risk Factors:")
        for factor, contribution in alert.get('top_risk_factors', [])[:3]:
            self.logger.info(f"  - {factor}: {contribution:.4f}")
        
        self.logger.info(f"Recommended Actions:")
        for action in alert.get('recommended_actions', []):
            self.logger.info(f"  • {action}")
        
        # Save to JSON file
        alerts_dir = Path('logs/alerts')
        alerts_dir.mkdir(parents=True, exist_ok=True)
        
        alert_file = alerts_dir / f"alert_{alert['alert_id']}.json"
        with open(alert_file, 'w') as f:
            json.dump(alert, f, indent=2)
    
    def _send_email_alert(self, alert: Dict):
        """Send email alert"""
        # Mock implementation
        self.logger.info(f"📧 Email alert sent for customer {alert['customer_id']}")
        
        # In production, implement actual email sending:
        # smtp_server = "smtp.gmail.com"
        # smtp_port = 587
        # sender_email = "alerts@bank.com"
        # receiver_email = "risk-team@bank.com"
        # 
        # msg = MIMEMultipart()
        # msg['Subject'] = f"HIGH RISK ALERT - Customer {alert['customer_id']}"
        # msg['From'] = sender_email
        # msg['To'] = receiver_email
        # 
        # body = self._format_email_body(alert)
        # msg.attach(MIMEText(body, 'html'))
        # 
        # with smtplib.SMTP(smtp_server, smtp_port) as server:
        #     server.starttls()
        #     server.login(sender_email, password)
        #     server.send_message(msg)
    
    def _send_sms_alert(self, alert: Dict):
        """Send SMS alert"""
        # Mock implementation
        self.logger.info(f"📱 SMS alert sent for customer {alert['customer_id']}")
        
        # In production, use SMS gateway like Twilio:
        # from twilio.rest import Client
        # client = Client(account_sid, auth_token)
        # message = client.messages.create(
        #     body=f"HIGH RISK: Customer {alert['customer_id']} - Score: {alert['risk_score']:.2f}",
        #     from_='+1234567890',
        #     to='+0987654321'
        # )
    
    def _format_email_body(self, alert: Dict) -> str:
        """Format email body HTML"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #e74c3c; color: white; padding: 20px; }}
                .content {{ padding: 20px; }}
                .risk-score {{ font-size: 24px; font-weight: bold; color: #e74c3c; }}
                .factors {{ background-color: #f8f9fa; padding: 15px; margin: 10px 0; }}
                .actions {{ background-color: #fff3cd; padding: 15px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚨 HIGH RISK ALERT</h1>
            </div>
            <div class="content">
                <p><strong>Alert ID:</strong> {alert['alert_id']}</p>
                <p><strong>Customer ID:</strong> {alert['customer_id']}</p>
                <p><strong>Risk Score:</strong> <span class="risk-score">{alert['risk_score']:.4f}</span></p>
                <p><strong>Timestamp:</strong> {alert['timestamp']}</p>
                
                <div class="factors">
                    <h3>Top Risk Factors:</h3>
                    <ul>
                        {"".join([f"<li>{factor}: {contribution:.4f}</li>" for factor, contribution in alert.get('top_risk_factors', [])[:5]])}
                    </ul>
                </div>
                
                <div class="actions">
                    <h3>Recommended Actions:</h3>
                    <ul>
                        {"".join([f"<li>{action}</li>" for action in alert.get('recommended_actions', [])])}
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    def get_alert_history(self, limit: int = 10) -> List[Dict]:
        """Get recent alerts"""
        return self.alert_history[-limit:]
    
    def get_alert_statistics(self) -> Dict:
        """Get alert statistics"""
        if not self.alert_history:
            return {
                'total_alerts': 0,
                'avg_risk_score': 0,
                'unique_customers': 0
            }
        
        return {
            'total_alerts': len(self.alert_history),
            'avg_risk_score': sum(a['risk_score'] for a in self.alert_history) / len(self.alert_history),
            'unique_customers': len(set(a['customer_id'] for a in self.alert_history)),
            'latest_alert': self.alert_history[-1]['timestamp'] if self.alert_history else None
        }

if __name__ == "__main__":
    # Test alert engine
    config = {
        'high_risk_threshold': 0.75,
        'email_enabled': False,
        'sms_enabled': False,
        'log_enabled': True
    }
    
    engine = AlertEngine(config)
    
    # Test alert
    test_alert = engine.trigger_alert(
        customer_id=12345,
        risk_score=0.85,
        explanation={
            'top_10_contributors': {
                'upi_to_loan_apps_pct': 0.25,
                'balance_drop_pct_4weeks': 0.20,
                'salary_delay_trend': 0.15,
                'failed_autopay_count': 0.12,
                'days_since_last_salary': 0.10
            }
        },
        additional_info={'account_type': 'savings'}
    )
    
    if test_alert:
        print("\n✅ Test alert triggered successfully")
        print(f"\nAlert ID: {test_alert['alert_id']}")
        print(f"Risk Score: {test_alert['risk_score']}")
        print(f"\nRecommendations:")
        for rec in test_alert['recommended_actions']:
            print(f"  • {rec}")
