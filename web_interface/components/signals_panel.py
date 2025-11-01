"""
Компонент панели торговых сигналов.
"""
import dash_bootstrap_components as dbc
from dash import html
from typing import List, Dict
from datetime import datetime


def create_signals_panel(signals: List[Dict] = None) -> List:
    """
    Создает панель с активными торговыми сигналами.
    
    Args:
        signals: Список сигналов с ключами: type, strength, confluence, zone, etc.
        
    Returns:
        List of Dash components
    """
    # Тестовые данные если не предоставлены
    if signals is None:
        signals = [
            {
                "type": "Long",
                "strength": "Strong",
                "confluence": 5,
                "zone": 50000.0,
                "entry": 50000.0,
                "stop_loss": 49000.0,
                "take_profit": 52000.0,
                "risk_reward": 2.0,
                "timeframe": "15m",
                "timestamp": datetime.now()
            },
            {
                "type": "Short",
                "strength": "Medium",
                "confluence": 3,
                "zone": 51000.0,
                "entry": 51000.0,
                "stop_loss": 52000.0,
                "take_profit": 49500.0,
                "risk_reward": 1.5,
                "timeframe": "1h",
                "timestamp": datetime.now()
            }
        ]
    
    if not signals:
        return [
            dbc.Alert("No active signals at the moment", color="secondary", className="mb-2")
        ]
    
    children = []
    
    for i, sig in enumerate(signals):
        # Определение цвета по типу и силе
        if sig["type"] == "Long":
            color = "success" if sig["strength"] == "Strong" else "info"
            icon = "📈"
        else:
            color = "danger" if sig["strength"] == "Strong" else "warning"
            icon = "📉"
        
        # Confluence badges
        confluence_badges = []
        for j in range(5):
            badge_color = "success" if j < sig.get("confluence", 0) else "secondary"
            confluence_badges.append(
                dbc.Badge("●", color=badge_color, className="me-1")
            )
        
        # Card для сигнала
        card = dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.H6([
                        html.Span(icon, className="me-2"),
                        f"{sig['type']} Signal",
                        dbc.Badge(sig['strength'], color=color, className="ms-2")
                    ], className=f"text-{color} mb-2"),
                    
                    html.Div([
                        html.Strong("Zone: "),
                        html.Span(f"${sig.get('zone', 0):,.2f}", className="float-end")
                    ], className="mb-1"),
                    
                    html.Div([
                        html.Strong("Entry: "),
                        html.Span(f"${sig.get('entry', 0):,.2f}", className="float-end")
                    ], className="mb-1"),
                    
                    html.Div([
                        html.Strong("Stop Loss: "),
                        html.Span(f"${sig.get('stop_loss', 0):,.2f}", className="float-end text-danger")
                    ], className="mb-1"),
                    
                    html.Div([
                        html.Strong("Take Profit: "),
                        html.Span(f"${sig.get('take_profit', 0):,.2f}", className="float-end text-success")
                    ], className="mb-2"),
                    
                    html.Hr(className="my-2"),
                    
                    html.Div([
                        html.Strong("Confluence: "),
                        html.Div(confluence_badges, className="float-end")
                    ], className="mb-1"),
                    
                    html.Div([
                        html.Strong("R:R Ratio: "),
                        html.Span(f"{sig.get('risk_reward', 0):.2f}", className="float-end")
                    ], className="mb-1"),
                    
                    html.Small(
                        f"TF: {sig.get('timeframe', 'N/A')} | "
                        f"Time: {sig.get('timestamp', datetime.now()).strftime('%H:%M')}",
                        className="text-muted"
                    )
                ])
            ])
        ], className="mb-3", color=color, outline=True)
        
        children.append(card)
    
    return children if children else [
        dbc.Alert("No active signals", color="secondary")
    ]

