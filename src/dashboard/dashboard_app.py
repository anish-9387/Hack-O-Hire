"""
Financial Stress Prediction Dashboard
Modernized UI version (Scrollable Table Upgrade)
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

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.scoring.scoring_service import RealTimeScoringService

# -------------------- APP INITIALIZATION --------------------

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY]
)
app.title = "Financial Stress Prediction Dashboard"

# Custom styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                background-color: #f4f6f9;
            }
            .card {
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.06);
            }
            .kpi-number {
                font-size: 2.2rem;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# -------------------- SCORING SERVICE --------------------

scoring_service = RealTimeScoringService()
scoring_service.initialize()

# -------------------- DATA LOADING --------------------

def load_dashboard_data():
    features_path = Path('data/processed/engineered_features.csv')

    if features_path.exists():
        df = pd.read_csv(features_path)

        if scoring_service.is_loaded:
            risk_scores = []
            risk_levels = []
            
            for _, row in df.iterrows():
                features = row.to_dict()
                features = {k: v for k, v in features.items()
                            if k not in ['customer_id', 'is_stressed', 'timestamp', 'location']}

                result = scoring_service.score_with_features(features)
                risk_scores.append(result.get('risk_score', 0))

            df['risk_score'] = risk_scores
            df['risk_level'] = risk_levels
        else:
            df['risk_score'] = df['is_stressed'].apply(lambda x: 0.8 if x == 1 else 0.2)

        return df

    else:
        return pd.DataFrame({
            'customer_id': range(1, n+1),
            'risk_score': risk_scores,
            'risk_level': pd.cut(risk_scores, bins=[0, 0.4, 0.6, 0.8, 1.0], 
                                labels=['Low', 'Medium', 'High', 'Critical']),
            'is_stressed': (risk_scores > 0.6).astype(int),
            'balance_drop_4w': np.random.uniform(0, 0.6, n),
            'upi_to_loan_apps_pct': np.random.uniform(0, 0.4, n),
            'salary_delay_trend': np.random.uniform(0, 20, n),
            'failed_autopay_count': np.random.randint(0, 8, n)
        })

df = load_dashboard_data()

# -------------------- LAYOUT --------------------

app.layout = dbc.Container([

    html.H1("🏦 Financial Stress Monitoring Dashboard",
            className="text-center text-primary mb-4 mt-4"),

    # KPI Cards
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("👥 Total Customers", className="text-muted"),
            html.H2(f"{len(df):,}", className="kpi-number text-primary")
        ])), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("🚨 High Risk", className="text-muted"),
            html.H2(f"{len(df[df['risk_score'] >= 0.75]):,}",
                    className="kpi-number text-danger")
        ])), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("⚠️ Medium Risk", className="text-muted"),
            html.H2(f"{len(df[(df['risk_score'] >= 0.5) & (df['risk_score'] < 0.75)]):,}",
                    className="kpi-number text-warning")
        ])), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("✅ Low Risk", className="text-muted"),
            html.H2(f"{len(df[df['risk_score'] < 0.5]):,}",
                    className="kpi-number text-success")
        ])), width=3),
    ], className="mb-4"),

    # Filter
    dbc.Card(dbc.CardBody([
        html.H6("Filter by Risk Level"),
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
    ]), className="mb-4"),

    # Charts
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Risk Distribution"),
            dcc.Loading(dcc.Graph(id='risk-distribution'))
        ])), width=6),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Risk Breakdown"),
            dcc.Loading(dcc.Graph(id='risk-breakdown'))
        ])), width=6),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Balance Drop vs Risk"),
            dcc.Loading(dcc.Graph(id='balance-scatter'))
        ])), width=6),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("UPI to Loan Apps vs Risk"),
            dcc.Loading(dcc.Graph(id='upi-scatter'))
        ])), width=6),
    ], className="mb-4"),

    # Risk Gauge
    dbc.Card(dbc.CardBody([
        html.H6("Average Portfolio Risk"),
        dcc.Graph(id='risk-gauge')
    ]), className="mb-4"),

    # Top Risk Table (Scrollable Fix)
    dbc.Card(dbc.CardBody([
        html.H6("🚨 Top 20 At-Risk Customers"),
        html.Div(id='top-risk-table', style={"overflowX": "auto"})
    ]), className="mb-4"),

    # Customer Analysis
    dbc.Card(dbc.CardBody([
        html.H6("Customer Risk Analysis"),
        dbc.Input(id='customer-id-input', type='number',
                  placeholder='Enter customer ID'),
        dbc.Button("Analyze", id='analyze-btn',
                   color='primary', className='mt-2'),
        html.Hr(),
        html.Div(id='customer-detail')
    ])),

], fluid=True)

# -------------------- CALLBACKS --------------------

@app.callback(
    [Output('risk-distribution', 'figure'),
     Output('risk-breakdown', 'figure'),
     Output('balance-scatter', 'figure'),
     Output('upi-scatter', 'figure'),
     Output('top-risk-table', 'children'),
     Output('risk-gauge', 'figure')],
    [Input('risk-filter', 'value')]
)
def update_dashboard(risk_filter):

    filtered_df = df.copy()

    if risk_filter == 'high':
        filtered_df = filtered_df[filtered_df['risk_score'] >= 0.75]
    elif risk_filter == 'medium':
        filtered_df = filtered_df[(filtered_df['risk_score'] >= 0.5) &
                                  (filtered_df['risk_score'] < 0.75)]
    elif risk_filter == 'low':
        filtered_df = filtered_df[filtered_df['risk_score'] < 0.5]

    fig1 = px.histogram(filtered_df, x='risk_score', nbins=30)
    fig1.update_layout(template="plotly_white")

    filtered_df['risk_level'] = pd.cut(
        filtered_df['risk_score'],
        bins=[0, 0.5, 0.75, 1.0],
        labels=['Low', 'Medium', 'High']
    )
    fig1.update_traces(marker_line_width=1, marker_line_color='#003D5C', opacity=0.9)

    # Figure 2: Risk Breakdown Donut Chart
    risk_counts = filtered_df['risk_level'].value_counts()

    fig2 = px.pie(values=risk_counts.values,
                  names=risk_counts.index)
    fig2.update_layout(template="plotly_white")

    fig3 = px.scatter(filtered_df,
                      x='balance_drop_pct_4weeks',
                      y='risk_score',
                      color='risk_score',
                      hover_data=['customer_id'])

    fig4 = px.scatter(filtered_df,
                      x='upi_to_loan_apps_pct',
                      y='risk_score',
                      color='risk_score',
                      hover_data=['customer_id'])

    avg_risk = filtered_df['risk_score'].mean()
    gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avg_risk,
        gauge={'axis': {'range': [0, 1]}}
    ))

    # Scrollable DataTable
    top_risk = filtered_df.nlargest(20, 'risk_score')

    table = dash_table.DataTable(
        data=top_risk.to_dict('records'),
        columns=[{"name": i, "id": i} for i in top_risk.columns],

        page_size=10,

        style_table={
            'overflowX': 'auto',
            'overflowY': 'auto',
            'maxHeight': '400px',
            'width': '100%',
        },

        style_cell={
            'minWidth': '120px',
            'width': '150px',
            'maxWidth': '250px',
            'whiteSpace': 'normal',
            'textAlign': 'left',
            'padding': '8px'
        },

        style_header={
            'backgroundColor': '#2c3e50',
            'color': 'white',
            'fontWeight': 'bold',
            'position': 'sticky',
            'top': 0,
            'zIndex': 1
        },
    )

    return fig1, fig2, fig3, fig4, table, gauge


@app.callback(
    Output('customer-detail', 'children'),
    [Input('analyze-btn', 'n_clicks')],
    [State('customer-id-input', 'value')]
)
def analyze_customer(n_clicks, customer_id):

    if n_clicks is None or customer_id is None:
        return html.P("Enter a customer ID and click Analyze")

    customer_data = df[df['customer_id'] == customer_id]

    if len(customer_data) == 0:
        return dbc.Alert(f"Customer ID {customer_id} not found",
                         color="warning")

    customer = customer_data.iloc[0]

    return dbc.Alert([
        html.H6(f"Customer ID: {customer['customer_id']}"),
        html.P(f"Risk Score: {customer['risk_score']:.4f}")
    ], color="info")


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
