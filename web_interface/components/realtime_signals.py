"""
Компонент панели real-time сигналов.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc
from datetime import datetime, timedelta
from typing import List, Dict, Optional


def create_realtime_signals_panel(signals: List[Dict] = None) -> list:
    """
    Создает панель с real-time сигналами и их статусом.
    
    Args:
        signals: List of real-time signals
        
    Returns:
        List of Dash components
    """
    # Тестовые данные
    if signals is None:
        signals = [
            {
                "pair": "BTC/USDT",
                "type": "Long",
                "timeframe": "15m",
                "confluence": 5,
                "entry_price": 50000.0,
                "current_price": 50100.0,
                "status": "pending",
                "timestamp": datetime.now(),
                "indicators": ["Order Block", "Volume Profile POC", "Positive Delta", "Market Profile VAL", "FVG"]
            },
            {
                "pair": "ETH/USDT",
                "type": "Short",
                "timeframe": "1h",
                "confluence": 4,
                "entry_price": 3500.0,
                "current_price": 3480.0,
                "status": "active",
                "timestamp": datetime.now() - timedelta(minutes=5),
                "indicators": ["Order Block", "Negative Delta", "Market Profile VAH", "FVG"]
            }
        ]
    
    if not signals:
        return [
            dbc.Alert("No real-time signals", color="info")
        ]
    
    children = []
    
    for sig in signals:
        # Определение цвета по статусу
        if sig['status'] == 'active':
            status_color = "success"
            status_icon = "✅"
        elif sig['status'] == 'pending':
            status_color = "warning"
            status_icon = "⏳"
        else:
            status_color = "secondary"
            status_icon = "❌"
        
        # Тип сигнала
        type_color = "success" if sig['type'] == 'Long' else "danger"
        
        # P/L если активен
        if sig['status'] == 'active':
            if sig['type'] == 'Long':
                pnl_pct = ((sig['current_price'] - sig['entry_price']) / sig['entry_price']) * 100
            else:
                pnl_pct = ((sig['entry_price'] - sig['current_price']) / sig['entry_price']) * 100
            
            pnl_color = "success" if pnl_pct > 0 else "danger"
            pnl_text = f"{pnl_pct:+.2f}%"
        else:
            pnl_text = "N/A"
            pnl_color = "secondary"
        
        # Card
        card = dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col([
                        html.H6([
                            html.Span(status_icon, className="me-2"),
                            sig['pair'],
                            dbc.Badge(sig['type'], color=type_color, className="ms-2"),
                            dbc.Badge(f"TF: {sig['timeframe']}", color="info", className="ms-1")
                        ])
                    ]),
                    dbc.Col([
                        dbc.Badge(pnl_text, color=pnl_color, className="float-end")
                    ], width="auto")
                ])
            ]),
            dbc.CardBody([
                html.Div([
                    html.Strong("Entry Price: "),
                    html.Span(f"${sig['entry_price']:,.2f}", className="float-end")
                ], className="mb-2"),
                
                html.Div([
                    html.Strong("Current Price: "),
                    html.Span(f"${sig['current_price']:,.2f}", className="float-end")
                ], className="mb-2"),
                
                html.Hr(),
                
                html.Div([
                    html.Strong("Confluence: "),
                    html.Span(f"{sig['confluence']}/5", className="float-end")
                ], className="mb-2"),
                
                html.Div([
                    html.Strong("Indicators: "),
                    html.Small(", ".join(sig.get('indicators', [])), className="text-muted d-block mt-1")
                ], className="mb-2"),
                
                html.Small(
                    f"Time: {sig['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}",
                    className="text-muted"
                )
            ])
        ], className="mb-3", color=status_color, outline=True)
        
        children.append(card)
    
    return children
