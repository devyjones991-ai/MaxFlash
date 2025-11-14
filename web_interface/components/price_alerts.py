"""
Компонент для настройки уведомлений о ценах.
Позволяет устанавливать целевые цены и получать алерты.
"""
from typing import Dict, List, Optional, Any
from dash import html, dcc
import dash_bootstrap_components as dbc


def create_price_alerts_panel() -> html.Div:
    """
    Создать панель для настройки уведомлений о ценах.

    Returns:
        HTML компонент с панелью алертов
    """
    return html.Div([
        dbc.Card([
            dbc.CardHeader("🔔 Уведомления о ценах"),
            dbc.CardBody([
                dbc.InputGroup([
                    dbc.Input(
                        id="alert-symbol-input",
                        placeholder="BTC/USDT",
                        type="text",
                        size="sm"
                    ),
                    dbc.Input(
                        id="alert-price-input",
                        placeholder="Целевая цена",
                        type="number",
                        size="sm"
                    ),
                    dbc.Select(
                        id="alert-type-select",
                        options=[
                            {"label": "Выше", "value": "above"},
                            {"label": "Ниже", "value": "below"}
                        ],
                        value="above",
                        size="sm"
                    ),
                    dbc.Button(
                        "➕", id="alert-add-btn",
                        color="success", size="sm"
                    )
                ], size="sm", className="mb-3"),
                html.Div(id="active-alerts-list"),
                dcc.Store(id='alerts-store', data={'alerts': []})
            ])
        ])
    ])

