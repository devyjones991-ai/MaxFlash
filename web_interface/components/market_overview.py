"""
Market Overview компонент: обзор всего рынка.
Heatmap, таблица всех пар, метрики рынка.
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Optional, Any
from dash import html, dcc
import dash_bootstrap_components as dbc

import sys
from pathlib import Path

# Добавляем путь к корню проекта для импорта config
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.market_data_manager import MarketDataManager
from utils.market_analytics import MarketAnalytics
from utils.market_alerts import MarketAlerts

try:
    from config.market_config import (
        POPULAR_PAIRS, MARKET_OVERVIEW_CONFIG, get_sector_for_pair
    )
except ImportError:
    # Fallback значения если config не найден
    POPULAR_PAIRS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT']
    MARKET_OVERVIEW_CONFIG = {'top_pairs_count': 100, 'heatmap_resolution': '1h', 'update_interval_seconds': 60}
    def get_sector_for_pair(pair: str):
        return None


def create_market_overview(
    data_manager: Optional[MarketDataManager] = None,
    analytics: Optional[MarketAnalytics] = None,
    alerts: Optional[MarketAlerts] = None
) -> html.Div:
    """
    Создать компонент Market Overview.

    Args:
        data_manager: Менеджер данных рынка
        analytics: Аналитика рынка
        alerts: Система алертов

    Returns:
        HTML компонент с обзором рынка
    """
    if data_manager is None:
        data_manager = MarketDataManager()
    if analytics is None:
        analytics = MarketAnalytics(data_manager)
    if alerts is None:
        alerts = MarketAlerts(data_manager)

    # Получаем статистику рынка
    market_stats = data_manager.get_market_stats()

    # Получаем тикеры для популярных пар
    tickers = data_manager.get_tickers('binance', POPULAR_PAIRS[:100])

    return html.Div([
        # Метрики рынка
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Всего пар", className="card-title"),
                        html.H2(
                            f"{market_stats.get('total_pairs', 0):,}",
                            className="text-primary"
                        ),
                        html.Small(
                            f"Активных: {market_stats.get('active_pairs', 0)}",
                            className="text-muted"
                        )
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Объем 24ч", className="card-title"),
                        html.H2(
                            f"${market_stats.get('total_volume_24h', 0):,.0f}",
                            className="text-success"
                        )
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("BTC Доминирование", className="card-title"),
                        html.H2(
                            f"{market_stats.get('btc_dominance', 0):.1f}%",
                            className="text-warning"
                        )
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Рост 24ч", className="card-title"),
                        html.H2(
                            f"{market_stats.get('pairs_up_24h', 0)}",
                            className="text-success"
                        )
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Падение 24ч", className="card-title"),
                        html.H2(
                            f"{market_stats.get('pairs_down_24h', 0)}",
                            className="text-danger"
                        )
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Средняя цена", className="card-title"),
                        html.H2(
                            f"${market_stats.get('avg_price', 0):,.2f}",
                            className="text-info"
                        )
                    ])
                ])
            ], width=2)
        ], className="mb-4"),

        # Heatmap криптовалют и алерты
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📊 Crypto Heatmap"),
                    dbc.CardBody([
                        dcc.Graph(
                            id="crypto-heatmap",
                            figure=create_crypto_heatmap(tickers),
                            style={"height": "500px"}
                        ),
                        dcc.Interval(
                            id='heatmap-interval',
                            interval=120*1000,  # Обновление каждые 2 минуты (увеличено)
                            n_intervals=0
                        )
                    ])
                ])
            ], width=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🚨 Рыночные алерты"),
                    dbc.CardBody([
                        html.Div(id="market-alerts-list"),
                        dcc.Interval(
                            id='alerts-interval',
                            interval=30*1000,  # Обновление каждые 30 секунд
                            n_intervals=0
                        )
                    ])
                ])
            ], width=4)
        ], className="mb-4"),

        # Таблица всех пар
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("📈 Все торговые пары", className="mb-0"),
                               dbc.InputGroup([
                                   dbc.Input(
                                       id="pair-search-input",
                                       placeholder="Поиск пары...",
                                       type="text"
                                   ),
                                   dbc.Button("🔍", id="pair-search-btn"),
                                   dbc.Button(
                                       "📥 CSV", id="export-csv-btn",
                                       color="secondary", size="sm",
                                       title="Экспорт в CSV"
                                   )
                               ], size="sm", className="mt-2")
                           ]),
                           dbc.CardBody([
                               dcc.Store(id='pairs-data-store', data={}),
                               dcc.Download(id="download-csv"),
                               html.Div(
                                   create_pairs_table(tickers),
                                   id="pairs-table-container"
                               )
                           ])
                ])
            ])
        ])
    ])


def create_crypto_heatmap(tickers: Dict[str, Dict[str, Any]]) -> go.Figure:
    """
    Создать heatmap криптовалют.

    Args:
        tickers: Словарь с тикерами

    Returns:
        Plotly figure с heatmap
    """
    if not tickers:
        # Fallback пустой график
        fig = go.Figure()
        fig.add_annotation(
            text="Нет данных для отображения",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(template="plotly_dark")
        return fig

    # Подготавливаем данные для heatmap
    pairs = []
    changes = []
    volumes = []

    for symbol, ticker in tickers.items():
        pairs.append(symbol.replace('/USDT', ''))
        change = ticker.get('percentage', 0)
        changes.append(change)
        volumes.append(ticker.get('quoteVolume', 0))

    # Создаем DataFrame
    df = pd.DataFrame({
        'Pair': pairs,
        'Change_24h': changes,
        'Volume': volumes
    })

    # Сортируем по объему
    df = df.sort_values('Volume', ascending=False).head(50)

    # Создаем heatmap
    fig = go.Figure(data=go.Heatmap(
        z=[df['Change_24h'].values],
        x=df['Pair'].values,
        y=['24h Change'],
        colorscale=[
            [0, 'red'],
            [0.5, 'white'],
            [1, 'green']
        ],
        zmid=0,
        text=[[f"{v:.2f}%" for v in df['Change_24h'].values]],
        texttemplate='%{text}',
        textfont={"size": 10},
        colorbar=dict(title="% Change")
    ))

    fig.update_layout(
        title="Crypto Heatmap - Top 50 by Volume",
        template="plotly_dark",
        height=500,
        xaxis=dict(title="Trading Pairs"),
        yaxis=dict(title="")
    )

    return fig


def create_pairs_table(
    tickers: Dict[str, Dict[str, Any]],
    search_query: Optional[str] = None,
    display_limit: int = 50
) -> html.Div:
    """
    Создать таблицу всех торговых пар.

    Args:
        tickers: Словарь с тикерами
        search_query: Поисковый запрос

    Returns:
        DataTable с парами
    """
    if not tickers:
        return html.Div([
            dbc.Alert("Нет данных для отображения", color="info")
        ])

    # Подготавливаем данные
    table_data = []
    for symbol, ticker in tickers.items():
        if search_query and search_query.lower() not in symbol.lower():
            continue

        change_24h = ticker.get('percentage', 0)
        volume_24h = ticker.get('quoteVolume', 0)
        price = ticker.get('last', 0)

        table_data.append({
            'Pair': symbol,
            'Price': price if price else 0,
            'Change 24h': change_24h,
            'Volume 24h': volume_24h if volume_24h else 0,
            'High 24h': ticker.get('high', 0),
            'Low 24h': ticker.get('low', 0),
            'Sector': get_sector_for_pair(symbol) or "Other"
        })

    # Сортируем по объему
    table_data.sort(key=lambda x: x['Volume 24h'], reverse=True)

    # Виртуализация: показываем только первые N, остальные lazy load
    display_data = table_data[:display_limit]
    total_count = len(table_data)
    has_more = total_count > display_limit

    return html.Div([
        # Информация о количестве
        html.Div([
            html.P(
                f"Показано {len(display_data)} из {total_count} пар",
                className="text-muted mb-2"
            ),
            dbc.Badge(
                f"Всего: {total_count}",
                color="info",
                className="ms-2"
            )
        ], className="mb-2"),
        
        # Таблица с виртуализацией
        html.Div([
            dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th([
                            "Pair",
                            dbc.Button(
                                "⇅", id="sort-pair-btn",
                                size="sm", color="link", className="ms-1 p-0"
                            )
                        ], style={"cursor": "pointer"}),
                        html.Th([
                            "Price",
                            dbc.Button(
                                "⇅", id="sort-price-btn",
                                size="sm", color="link", className="ms-1 p-0"
                            )
                        ], style={"cursor": "pointer"}),
                        html.Th([
                            "Change 24h",
                            dbc.Button(
                                "⇅", id="sort-change-btn",
                                size="sm", color="link", className="ms-1 p-0"
                            )
                        ], style={"cursor": "pointer"}),
                        html.Th([
                            "Volume 24h",
                            dbc.Button(
                                "⇅", id="sort-volume-btn",
                                size="sm", color="link", className="ms-1 p-0"
                            )
                        ], style={"cursor": "pointer"}),
                        html.Th("High 24h"),
                        html.Th("Low 24h"),
                        html.Th("Sector")
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td(row['Pair']),
                        html.Td(f"${row['Price']:,.4f}"),
                        html.Td(
                            html.Span(
                                f"{row['Change 24h']:.2f}%",
                                className="text-success" if row['Change 24h'] > 0 else "text-danger"
                            )
                        ),
                        html.Td(f"${row['Volume 24h']:,.0f}"),
                        html.Td(f"${row['High 24h']:,.4f}"),
                        html.Td(f"${row['Low 24h']:,.4f}"),
                        html.Td(row['Sector'])
                    ]) for row in display_data
                ])
            ], striped=True, bordered=True, hover=True, responsive=True, dark=True,
               style={"maxHeight": "600px", "overflowY": "auto"})
        ], style={"maxHeight": "600px", "overflowY": "auto"}),
        
        # Кнопка загрузки еще (lazy loading)
        html.Div([
            dbc.Button(
                f"Загрузить еще {display_limit} (осталось {total_count - len(display_data)})",
                id="load-more-pairs-btn",
                color="secondary",
                size="sm",
                className="mt-2",
                disabled=not has_more
            ) if has_more else html.Div([
                dbc.Badge("Все пары загружены", color="success", className="mt-2")
            ])
        ])
    ], id="pairs-table-wrapper")

