"""
Multi-View компонент: одновременный просмотр нескольких графиков.
Синхронизация таймфреймов, сравнительный анализ.
"""
from typing import Dict, List, Optional, Any
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from utils.market_data_manager import MarketDataManager
from components.price_chart import create_price_chart_with_indicators


def create_multi_chart_view(
    data_manager: Optional[MarketDataManager] = None
) -> html.Div:
    """
    Создать компонент Multi-View для одновременного просмотра нескольких графиков.

    Args:
        data_manager: Менеджер данных рынка

    Returns:
        HTML компонент с мульти-экранным просмотром
    """
    if data_manager is None:
        data_manager = MarketDataManager()

    return html.Div([
        # Панель выбора пар
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📊 Выбор пар для сравнения"),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Пара 1:"),
                                dbc.InputGroup([
                                    dbc.Input(
                                        id="multi-symbol-1",
                                        placeholder="BTC/USDT",
                                        value="BTC/USDT",
                                        type="text"
                                    ),
                                    dbc.DropdownMenu(
                                        label="📋",
                                        children=[
                                            dbc.DropdownMenuItem("BTC/USDT", id="pair-1-btc"),
                                            dbc.DropdownMenuItem("ETH/USDT", id="pair-1-eth"),
                                            dbc.DropdownMenuItem("SOL/USDT", id="pair-1-sol"),
                                            dbc.DropdownMenuItem("BNB/USDT", id="pair-1-bnb"),
                                        ],
                                        toggle_style={"padding": "0.25rem 0.5rem"}
                                    )
                                ])
                            ], width=3),
                            dbc.Col([
                                dbc.Label("Пара 2:"),
                                dbc.InputGroup([
                                    dbc.Input(
                                        id="multi-symbol-2",
                                        placeholder="ETH/USDT",
                                        value="ETH/USDT",
                                        type="text"
                                    ),
                                    dbc.DropdownMenu(
                                        label="📋",
                                        children=[
                                            dbc.DropdownMenuItem("BTC/USDT", id="pair-2-btc"),
                                            dbc.DropdownMenuItem("ETH/USDT", id="pair-2-eth"),
                                            dbc.DropdownMenuItem("SOL/USDT", id="pair-2-sol"),
                                            dbc.DropdownMenuItem("BNB/USDT", id="pair-2-bnb"),
                                        ],
                                        toggle_style={"padding": "0.25rem 0.5rem"}
                                    )
                                ])
                            ], width=3),
                            dbc.Col([
                                dbc.Label("Пара 3:"),
                                dbc.InputGroup([
                                    dbc.Input(
                                        id="multi-symbol-3",
                                        placeholder="SOL/USDT",
                                        value="",
                                        type="text"
                                    ),
                                    dbc.DropdownMenu(
                                        label="📋",
                                        children=[
                                            dbc.DropdownMenuItem("BTC/USDT", id="pair-3-btc"),
                                            dbc.DropdownMenuItem("ETH/USDT", id="pair-3-eth"),
                                            dbc.DropdownMenuItem("SOL/USDT", id="pair-3-sol"),
                                            dbc.DropdownMenuItem("BNB/USDT", id="pair-3-bnb"),
                                        ],
                                        toggle_style={"padding": "0.25rem 0.5rem"}
                                    )
                                ])
                            ], width=3),
                            dbc.Col([
                                dbc.Label("Пара 4:"),
                                dbc.InputGroup([
                                    dbc.Input(
                                        id="multi-symbol-4",
                                        placeholder="BNB/USDT",
                                        value="",
                                        type="text"
                                    ),
                                    dbc.DropdownMenu(
                                        label="📋",
                                        children=[
                                            dbc.DropdownMenuItem("BTC/USDT", id="pair-4-btc"),
                                            dbc.DropdownMenuItem("ETH/USDT", id="pair-4-eth"),
                                            dbc.DropdownMenuItem("SOL/USDT", id="pair-4-sol"),
                                            dbc.DropdownMenuItem("BNB/USDT", id="pair-4-bnb"),
                                        ],
                                        toggle_style={"padding": "0.25rem 0.5rem"}
                                    )
                                ])
                            ], width=3)
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Таймфрейм:"),
                                dbc.ButtonGroup([
                                    dbc.Button("15m", id="multi-tf-15m",
                                              size="sm", outline=True),
                                    dbc.Button("1h", id="multi-tf-1h",
                                              size="sm", outline=True),
                                    dbc.Button("4h", id="multi-tf-4h",
                                              size="sm", outline=True),
                                    dbc.Button("1d", id="multi-tf-1d",
                                              size="sm", outline=True),
                                ], id="multi-timeframe-group")
                            ], width=12, className="mt-3")
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Button(
                                    "🔄 Обновить графики",
                                    id="multi-update-btn",
                                    color="primary",
                                    className="mt-3"
                                )
                            ])
                        ])
                    ])
                ])
            ])
        ], className="mb-4"),

        # Графики (2x2 сетка)
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                    html.H5("Chart 1", id="multi-chart-1-header", className="mb-0")
                ]),
                    dbc.CardBody([
                        dcc.Graph(
                            id="multi-chart-1",
                            style={"height": "400px"},
                            config={
                                "displayModeBar": True,
                                "displaylogo": False
                            }
                        )
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                    html.H5("Chart 2", id="multi-chart-2-header",
                           className="mb-0")
                ]),
                    dbc.CardBody([
                        dcc.Graph(
                            id="multi-chart-2",
                            style={"height": "400px"},
                            config={
                                "displayModeBar": True,
                                "displaylogo": False
                            }
                        )
                    ])
                ])
            ], width=6)
        ], className="mb-4"),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                    html.H5("Chart 3", id="multi-chart-3-header",
                           className="mb-0")
                ]),
                    dbc.CardBody([
                        dcc.Graph(
                            id="multi-chart-3",
                            style={"height": "400px"},
                            config={
                                "displayModeBar": True,
                                "displaylogo": False
                            }
                        )
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                    html.H5("Chart 4", id="multi-chart-4-header",
                           className="mb-0")
                ]),
                    dbc.CardBody([
                        dcc.Graph(
                            id="multi-chart-4",
                            style={"height": "400px"},
                            config={
                                "displayModeBar": True,
                                "displaylogo": False
                            }
                        )
                    ])
                ])
            ], width=6)
        ])
    ])


def create_multi_chart_figure(
    symbol: str, timeframe: str = '15m',
    data_manager: Optional[MarketDataManager] = None
) -> go.Figure:
    """
    Создать график для мульти-экранного просмотра.

    Args:
        symbol: Торговая пара
        timeframe: Таймфрейм
        data_manager: Менеджер данных рынка

    Returns:
        Plotly figure
    """
    if not symbol or symbol.strip() == "":
        # Пустой график
        fig = go.Figure()
        fig.add_annotation(
            text="Выберите торговую пару",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(template="plotly_dark", title="No Data")
        return fig

    if data_manager is None:
        data_manager = MarketDataManager()

    try:
        # Загружаем данные
        dataframe = data_manager.get_ohlcv(
            symbol, timeframe, limit=200, exchange_id='binance'
        )

        if dataframe is None or dataframe.empty:
            fig = go.Figure()
            fig.add_annotation(
                text=f"Нет данных для {symbol}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(template="plotly_dark", title=symbol)
            return fig

        # Создаем график с индикаторами
        try:
            from components.price_chart import create_price_chart_with_indicators
            fig = create_price_chart_with_indicators(dataframe=dataframe)
            fig.update_layout(
                title=f"{symbol} - {timeframe}",
                height=400
            )
            return fig
        except ImportError:
            # Fallback простой график
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=dataframe.index,
                open=dataframe['open'],
                high=dataframe['high'],
                low=dataframe['low'],
                close=dataframe['close'],
                name=symbol
            ))
            fig.update_layout(
                template="plotly_dark",
                title=f"{symbol} - {timeframe}",
                height=400,
                xaxis_rangeslider_visible=False
            )
            return fig

    except Exception as e:
        # Ошибка - возвращаем пустой график с сообщением
        fig = go.Figure()
        fig.add_annotation(
            text=f"Ошибка загрузки {symbol}: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(template="plotly_dark", title=symbol)
        return fig

