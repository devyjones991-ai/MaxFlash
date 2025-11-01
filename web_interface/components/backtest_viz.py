"""
Компонент визуализации результатов бэктестинга.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.graph_objects as go
from typing import Dict, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def create_backtest_results(backtest_data: Optional[Dict] = None) -> list:
    """
    Создает панель с результатами бэктестинга.
    
    Args:
        backtest_data: Dictionary с результатами бэктеста
        
    Returns:
        List of Dash components
    """
    # Тестовые данные
    if backtest_data is None:
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        equity_curve = 10000 + np.cumsum(np.random.randn(100) * 50)
        equity_curve = np.maximum(equity_curve, 9500)  # Минимальный баланс
        
        backtest_data = {
            'equity_curve': equity_curve,
            'dates': dates,
            'total_trades': 150,
            'win_rate': 60.0,
            'profit_factor': 3.00,
            'sharpe_ratio': 8.20,
            'total_return': 8.00,
            'max_drawdown': -1.83,
            'avg_win': 200.0,
            'avg_loss': -100.0
        }
    
    # Equity curve график
    equity_fig = go.Figure()
    
    equity_fig.add_trace(go.Scatter(
        x=backtest_data['dates'],
        y=backtest_data['equity_curve'],
        mode='lines',
        name='Equity',
        line=dict(color='green', width=2),
        fill='tozeroy',
        fillcolor='rgba(0, 255, 0, 0.1)'
    ))
    
    # Initial balance line
    initial = backtest_data['equity_curve'][0]
    equity_fig.add_hline(
        y=initial,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Initial: ${initial:,.2f}"
    )
    
    equity_fig.update_layout(
        template="plotly_dark",
        title="Equity Curve",
        xaxis_title="Date",
        yaxis_title="Equity ($)",
        height=300,
        margin=dict(l=50, r=20, t=60, b=40)
    )
    
    # Метрики в таблице
    metrics_table = dash_table.DataTable(
        columns=[
            {"name": "Metric", "id": "metric"},
            {"name": "Value", "id": "value"}
        ],
        data=[
            {"metric": "Total Trades", "value": f"{backtest_data['total_trades']}"},
            {"metric": "Win Rate", "value": f"{backtest_data['win_rate']:.2f}%"},
            {"metric": "Profit Factor", "value": f"{backtest_data['profit_factor']:.2f}"},
            {"metric": "Sharpe Ratio", "value": f"{backtest_data['sharpe_ratio']:.2f}"},
            {"metric": "Total Return", "value": f"{backtest_data['total_return']:.2f}%"},
            {"metric": "Max Drawdown", "value": f"{backtest_data['max_drawdown']:.2f}%"},
            {"metric": "Average Win", "value": f"${backtest_data['avg_win']:.2f}"},
            {"metric": "Average Loss", "value": f"${backtest_data['avg_loss']:.2f}"},
        ],
        style_table={'overflowX': 'auto'},
        style_cell={
            'backgroundColor': 'rgb(30, 30, 30)',
            'color': 'white',
            'textAlign': 'left',
            'fontFamily': 'Arial'
        },
        style_header={
            'backgroundColor': 'rgb(60, 60, 60)',
            'fontWeight': 'bold'
        }
    )
    
    return [
        dbc.Row([
            dbc.Col([
                dcc.Graph(figure=equity_fig)
            ], width=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Performance Metrics"),
                    dbc.CardBody([
                        metrics_table
                    ])
                ])
            ], width=4)
        ])
    ]

