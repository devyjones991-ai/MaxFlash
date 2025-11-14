"""
Компонент для отслеживания монет (Watchlist).
Позволяет добавлять монеты в список отслеживания и видеть их цены в реальном времени.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from utils.market_data_manager import MarketDataManager
from utils.market_alerts import MarketAlerts


def create_watchlist_panel(
    data_manager: Optional[MarketDataManager] = None,
    alerts: Optional[MarketAlerts] = None
) -> html.Div:
    """
    Создать панель отслеживания монет.

    Args:
        data_manager: Менеджер данных рынка
        alerts: Система алертов

    Returns:
        HTML компонент с панелью отслеживания
    """
    if data_manager is None:
        data_manager = MarketDataManager()
    if alerts is None:
        alerts = MarketAlerts(data_manager)

    return html.Div([
        dbc.Card([
            dbc.CardHeader([
                html.H5("⭐ Отслеживаемые монеты", className="mb-0"),
                dbc.InputGroup([
                    dbc.Input(
                        id="watchlist-symbol-input",
                        placeholder="BTC/USDT",
                        type="text",
                        style={"maxWidth": "200px"}
                    ),
                    dbc.Button(
                        "➕ Добавить", id="watchlist-add-btn",
                        color="success", size="sm"
                    )
                ], size="sm", className="mt-2")
            ]),
            dbc.CardBody([
                dcc.Store(id='watchlist-store', data={'symbols': ['BTC/USDT', 'ETH/USDT']}),
                html.Div(id="watchlist-items"),
                dcc.Interval(
                    id='watchlist-interval',
                    interval=5*1000,  # Обновление каждые 5 секунд
                    n_intervals=0
                )
            ])
        ])
    ])


def create_watchlist_item(
    symbol: str,
    ticker: Optional[Dict[str, Any]] = None
) -> html.Div:
    """
    Создать элемент списка отслеживания.

    Args:
        symbol: Торговая пара
        ticker: Данные тикера

    Returns:
        HTML компонент элемента
    """
    if ticker is None:
        price = 0
        change_24h = 0
        volume_24h = 0
    else:
        price = ticker.get('last', 0)
        change_24h = ticker.get('percentage', 0)
        volume_24h = ticker.get('quoteVolume', 0)

    change_color = "success" if change_24h >= 0 else "danger"
    change_icon = "📈" if change_24h >= 0 else "📉"

    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Button(
                        symbol,
                        id={"type": "watchlist-load", "symbol": symbol},
                        className="btn btn-link p-0 text-start text-decoration-none",
                        style={"color": "inherit", "font-weight": "bold", "border": "none", "background": "none"}
                    ),
                    html.Br(),
                    html.Small(
                        f"{change_icon} {change_24h:+.2f}%",
                        className=f"text-{change_color}"
                    )
                ], width=6),
                dbc.Col([
                    html.Strong(f"${price:,.2f}", className="text-primary"),
                    html.Br(),
                    html.Small(
                        f"Vol: ${volume_24h:,.0f}",
                        className="text-muted"
                    )
                ], width=5, className="text-end"),
                dbc.Col([
                    dbc.Button(
                        "❌", id={"type": "watchlist-remove", "symbol": symbol},
                        color="danger", size="sm", outline=True
                    )
                ], width=1)
            ], align="center")
        ])
    ], className="mb-2", style={"cursor": "pointer"})


def create_watchlist_items(
    symbols: List[str],
    data_manager: MarketDataManager
) -> html.Div:
    """
    Создать список элементов отслеживания.

    Args:
        symbols: Список символов для отслеживания
        data_manager: Менеджер данных рынка

    Returns:
        HTML компонент со списком
    """
    if not symbols:
        return html.Div([
            dbc.Alert("Нет отслеживаемых монет. Добавьте монету выше.", color="info")
        ])

    items = []
    tickers = data_manager.get_tickers('binance', symbols, max_workers=10)

    for symbol in symbols:
        ticker = tickers.get(symbol)
        items.append(create_watchlist_item(symbol, ticker))

    return html.Div(items)

