"""
Financial Stress Prediction Dashboard
Interactive Dash dashboard for risk monitoring and visualization
"""
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.scoring.scoring_service import RealTimeScoringService

# Initialize Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Financial Stress Prediction Dashboard"

# Initialize scoring service
scoring_service = RealTimeScoringService()
scoring_service.initialize()

# Load data
def load_dashboard_data():
    """Load feature data for dashboard"""
    features_path = Path('data/processed/engineered_features.csv')
    
    if features_path.exists():
        df = pd.read_csv(features_path)
        
        # Add risk scores
        if scoring_service.is_loaded:
            risk_scores = []
            for _, row in df.iterrows():
                features = row.to_dict()
                features = {k: v for k, v in features.items() 
                           if k not in ['customer_id', 'is_stressed', 'timestamp', 'location']}
                
                result = scoring_service.score_with_features(features)
                risk_scores.append(result.get('risk_score', 0))
            
            df['risk_score'] = risk_scores
        else:
            # Use is_stressed as proxy
            df['risk_score'] = df['is_stressed'].apply(lambda x: 0.8 if x == 1 else 0.2)
        
        return df
    else:
        # Return dummy data
        return pd.DataFrame({
            'customer_id': range(1, 101),
            'risk_score': np.random.uniform(0, 1, 100),
            'is_stressed': np.random.choice([0, 1], 100),
            'age': np.random.randint(25, 65, 100),
            'monthly_income': np.random.uniform(30000, 150000, 100),
            'balance_drop_pct_4weeks': np.random.uniform(0, 50, 100),
            'upi_to_loan_apps_pct': np.random.uniform(0, 40, 100),
            'failed_autopay_count': np.random.randint(0, 5, 100)
        })

# Load data
df = load_dashboard_data()

# Dashboard Layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("🏦 Financial Stress Prediction Dashboard", 
                   className="text-center text-primary mb-4 mt-4"),
            html.Hr()
        ])
    ]),
    
    # Summary Cards
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Total Customers", className="card-title"),
                    html.H2(f"{len(df):,}", className="text-primary")
                ])
            ])
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("High Risk", className="card-title"),
                    html.H2(f"{len(df[df['risk_score'] >= 0.75]):,}", 
                           className="text-danger")
                ])
            ])
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Medium Risk", className="card-title"),
                    html.H2(f"{len(df[(df['risk_score'] >= 0.5) & (df['risk_score'] < 0.75)]):,}", 
                           className="text-warning")
                ])
            ])
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Low Risk", className="card-title"),
                    html.H2(f"{len(df[df['risk_score'] < 0.5]):,}", 
                           className="text-success")
                ])
            ])
        ], width=3),
    ], className="mb-4"),
    
    # Filters
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Filters", className="card-title"),
                    html.Label("Risk Level:"),
                    dcc.Dropdown(
                        id='risk-filter',
                        options=[
                            {'label': 'All', 'value': 'all'},
                            {'label': 'High Risk (>0.75)', 'value': 'high'},
                            {'label': 'Medium Risk (0.5-0.75)', 'value': 'medium'},
                            {'label': 'Low Risk (<0.5)', 'value': 'low'}
                        ],
                        value='all',
                        clearable=False
                    )
                ])
            ])
        ], width=12)
    ], className="mb-4"),
    
    # Main Charts Row 1
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Risk Score Distribution", className="card-title"),
                    dcc.Graph(id='risk-distribution')
                ])
            ])
        ], width=6),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Risk Level Breakdown", className="card-title"),
                    dcc.Graph(id='risk-breakdown')
                ])
            ])
        ], width=6),
    ], className="mb-4"),
    
    # Main Charts Row 2
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Balance Drop vs Risk Score", className="card-title"),
                    dcc.Graph(id='balance-scatter')
                ])
            ])
        ], width=6),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("UPI to Loan Apps vs Risk Score", className="card-title"),
                    dcc.Graph(id='upi-scatter')
                ])
            ])
        ], width=6),
    ], className="mb-4"),
    
    # Top At-Risk Customers
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("🚨 Top 20 At-Risk Customers", className="card-title"),
                    html.Div(id='top-risk-table')
                ])
            ])
        ])
    ], className="mb-4"),
    
    # Customer Detail Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Customer Risk Analysis", className="card-title"),
                    html.Label("Enter Customer ID:"),
                    dbc.Input(id='customer-id-input', type='number', 
                             placeholder='Enter customer ID'),
                    dbc.Button("Analyze", id='analyze-btn', color='primary', 
                              className='mt-2'),
                    html.Hr(),
                    html.Div(id='customer-detail')
                ])
            ])
        ])
    ], className="mb-4"),
    
    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(),
            html.P("© 2026 Financial Stress Prediction System | "
                  "Real-time Risk Monitoring Dashboard",
                  className="text-center text-muted")
        ])
    ])
    
], fluid=True)

# Callbacks
@app.callback(
    [Output('risk-distribution', 'figure'),
     Output('risk-breakdown', 'figure'),
     Output('balance-scatter', 'figure'),
     Output('upi-scatter', 'figure'),
     Output('top-risk-table', 'children')],
    [Input('risk-filter', 'value')]
)
def update_dashboard(risk_filter):
    """Update all dashboard components based on filter"""
    
    # Filter data
    filtered_df = df.copy()
    
    if risk_filter == 'high':
        filtered_df = filtered_df[filtered_df['risk_score'] >= 0.75]
    elif risk_filter == 'medium':
        filtered_df = filtered_df[(filtered_df['risk_score'] >= 0.5) & 
                                  (filtered_df['risk_score'] < 0.75)]
    elif risk_filter == 'low':
        filtered_df = filtered_df[filtered_df['risk_score'] < 0.5]
    
    # Risk Distribution Histogram
    fig1 = px.histogram(
        filtered_df,
        x='risk_score',
        nbins=30,
        title='',
        labels={'risk_score': 'Risk Score'},
        color_discrete_sequence=['#3498db']
    )
    fig1.update_layout(showlegend=False)
    
    # Risk Level Pie Chart
    filtered_df['risk_level'] = pd.cut(
        filtered_df['risk_score'],
        bins=[0, 0.5, 0.75, 1.0],
        labels=['Low', 'Medium', 'High']
    )
    risk_counts = filtered_df['risk_level'].value_counts()
    
    fig2 = px.pie(
        values=risk_counts.values,
        names=risk_counts.index,
        title='',
        color=risk_counts.index,
        color_discrete_map={'Low': '#2ecc71', 'Medium': '#f39c12', 'High': '#e74c3c'}
    )
    
    # Balance Drop Scatter
    fig3 = px.scatter(
        filtered_df,
        x='balance_drop_pct_4weeks',
        y='risk_score',
        color='risk_score',
        title='',
        labels={
            'balance_drop_pct_4weeks': 'Balance Drop (4 weeks) %',
            'risk_score': 'Risk Score'
        },
        color_continuous_scale='Reds',
        hover_data=['customer_id']
    )
    
    # UPI Loan Apps Scatter
    fig4 = px.scatter(
        filtered_df,
        x='upi_to_loan_apps_pct',
        y='risk_score',
        color='risk_score',
        title='',
        labels={
            'upi_to_loan_apps_pct': 'UPI to Loan Apps %',
            'risk_score': 'Risk Score'
        },
        color_continuous_scale='Reds',
        hover_data=['customer_id']
    )
    
    # Top Risk Table
    top_risk = filtered_df.nlargest(20, 'risk_score')[[
        'customer_id', 'risk_score', 'balance_drop_pct_4weeks',
        'upi_to_loan_apps_pct', 'failed_autopay_count'
    ]].round(4)
    
    table = dash_table.DataTable(
        data=top_risk.to_dict('records'),
        columns=[
            {'name': 'Customer ID', 'id': 'customer_id'},
            {'name': 'Risk Score', 'id': 'risk_score'},
            {'name': 'Balance Drop %', 'id': 'balance_drop_pct_4weeks'},
            {'name': 'UPI to Loan Apps %', 'id': 'upi_to_loan_apps_pct'},
            {'name': 'Failed Autopay', 'id': 'failed_autopay_count'}
        ],
        style_cell={'textAlign': 'left'},
        style_data_conditional=[
            {
                'if': {'filter_query': '{risk_score} >= 0.75'},
                'backgroundColor': '#ffcccc',
                'color': 'black'
            }
        ],
        style_header={
            'backgroundColor': '#3498db',
            'color': 'white',
            'fontWeight': 'bold'
        },
        page_size=10
    )
    
    return fig1, fig2, fig3, fig4, table

@app.callback(
    Output('customer-detail', 'children'),
    [Input('analyze-btn', 'n_clicks')],
    [State('customer-id-input', 'value')]
)
def analyze_customer(n_clicks, customer_id):
    """Analyze specific customer"""
    if n_clicks is None or customer_id is None:
        return html.P("Enter a customer ID and click Analyze", 
                     className="text-muted")
    
    # Find customer
    customer_data = df[df['customer_id'] == customer_id]
    
    if len(customer_data) == 0:
        return dbc.Alert(f"Customer ID {customer_id} not found", color="warning")
    
    customer = customer_data.iloc[0]
    
    # Create detail view
    detail = dbc.Row([
        dbc.Col([
            html.H6("Customer Information"),
            html.P(f"Customer ID: {customer['customer_id']}"),
            html.P(f"Risk Score: {customer['risk_score']:.4f}"),
            html.P(f"Risk Level: {'HIGH' if customer['risk_score'] >= 0.75 else 'MEDIUM' if customer['risk_score'] >= 0.5 else 'LOW'}",
                  className='text-danger' if customer['risk_score'] >= 0.75 else 'text-warning' if customer['risk_score'] >= 0.5 else 'text-success'),
        ], width=6),
        
        dbc.Col([
            html.H6("Key Metrics"),
            html.P(f"Balance Drop: {customer.get('balance_drop_pct_4weeks', 0):.2f}%"),
            html.P(f"UPI to Loan Apps: {customer.get('upi_to_loan_apps_pct', 0):.2f}%"),
            html.P(f"Failed Autopay: {customer.get('failed_autopay_count', 0)}"),
        ], width=6)
    ])
    
    return detail

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Starting Financial Stress Prediction Dashboard")
    print("="*60)
    print("📊 Dashboard URL: http://localhost:8050")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    app.run_server(debug=True, host='0.0.0.0', port=8050)
