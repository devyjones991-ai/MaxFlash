"""
Plotly Dash Web Interface для MaxFlash Trading System.
Оптимальное отображение всех индикаторов и сигналов.
"""

import contextlib
import os
import sys
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html

# Добавляем пути к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Импорт после добавления пути в sys.path (необходимо)
from utils.logger_config import setup_logging  # noqa: E402

# Импорт FreqtradeClient с обработкой ошибок
FreqtradeClient: Optional[type] = None
with contextlib.suppress(ImportError):
    from api.freqtrade_client import FreqtradeClient

# Настройка логирования
logger = setup_logging()


def fetch_market_data(symbol: str, timeframe: str = "15m", limit: int = 200):
    """
    Загружает рыночные данные для указанного символа.

    Args:
        symbol: Торговая пара (например, BTC/USDT)
        timeframe: Таймфрейм (15m, 1h, 4h, 1d)
        limit: Количество свечей

    Returns:
        DataFrame с OHLCV данными
    """
    from datetime import datetime, timedelta

    import numpy as np
    import pandas as pd

    try:
        # Пробуем загрузить через CCXT
        try:
            import ccxt

            exchange = ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "spot"}})

            # Конвертируем timeframe для CCXT
            tf_map = {"15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
            ccxt_tf = tf_map.get(timeframe, "15m")

            # Загружаем данные
            ohlcv = exchange.fetch_ohlcv(symbol, ccxt_tf, limit=limit)

            # Создаем DataFrame
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)

            logger.info(f"Загружены данные для {symbol}: {len(df)} свечей")
            return df

        except ImportError:
            logger.warning("CCXT не установлен, используем тестовые данные")
        except Exception as e:
            logger.warning("Ошибка загрузки через CCXT: %s, используем тестовые данные", str(e))

        # Fallback: генерируем тестовые данные с учетом символа
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=limit, freq="15min")
        # Разные данные для разных символов
        np.random.seed(hash(symbol) % 1000)

        # Базовые цены для популярных пар
        base_prices = {
            "BTC/USDT": 50000,
            "ETH/USDT": 3000,
            "BNB/USDT": 300,
            "SOL/USDT": 100,
        }
        base_price = base_prices.get(symbol, 1000)

        price_change = base_price * 0.01
        prices = base_price + np.cumsum(np.random.randn(limit) * price_change)

        df = pd.DataFrame(
            {
                "open": prices * 0.999,
                "high": prices * 1.002,
                "low": prices * 0.998,
                "close": prices,
                "volume": np.random.uniform(1000000, 5000000, limit),
            },
            index=dates,
        )

        logger.info("Сгенерированы тестовые данные для %s", symbol)
        return df

    except Exception as e:
        logger.error("Ошибка загрузки данных для %s: %s", symbol, str(e))
        # Возвращаем минимальный DataFrame
        dates = pd.date_range(start="2024-01-01", periods=100, freq="15min")
        return pd.DataFrame(
            {"open": [100] * 100, "high": [101] * 100, "low": [99] * 100, "close": [100] * 100, "volume": [1000] * 100},
            index=dates,
        )


# Инициализация Dash app с темной темой
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

app.title = "MaxFlash Trading System Dashboard"

# Инициализация Freqtrade клиента (если доступен)
ft_client = None
if FreqtradeClient is not None:
    with contextlib.suppress(Exception):
        ft_client = FreqtradeClient()

# Главный layout
app.layout = dbc.Container(
    [
        # Header с навигацией
        dbc.Navbar(
            [
                dbc.Container(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.H3("📊 MaxFlash Trading System", className="mb-0"),
                                        html.Small(
                                            "Smart Money + Footprint + Volume Profile + Market Profile + TPO",
                                            className="text-muted",
                                        ),
                                    ],
                                    width="auto",
                                ),
                                dbc.Col(
                                    [
                                        dbc.ButtonGroup(
                                            [
                                                dbc.Button(
                                                    "🔄 Refresh", id="refresh-btn", outline=True, color="primary"
                                                ),
                                                dbc.Button(
                                                    "⚙️ Settings", id="settings-btn", outline=True, color="secondary"
                                                ),
                                            ]
                                        )
                                    ],
                                    width="auto",
                                    className="ms-auto",
                                ),
                            ],
                            align="center",
                        )
                    ],
                    fluid=True,
                )
            ],
            color="dark",
            dark=True,
            className="mb-4",
        ),
        # Status bar
        dbc.Row([dbc.Col([dbc.Alert(id="status-alert", color="info", className="mb-3", dismissable=True)])]),
        # Основной контент
        dbc.Row(
            [
                # Главный график (левая колонка - 9 из 12)
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [html.H5("Price Chart with Order Blocks & FVG", className="mb-0")],
                                                    width="auto",
                                                ),
                                                dbc.Col(
                                                    [
                                                        dbc.InputGroup(
                                                            [
                                                                dbc.InputGroupText("💰"),
                                                                dbc.Input(
                                                                    id="symbol-input",
                                                                    placeholder="BTC/USDT",
                                                                    value="BTC/USDT",
                                                                    type="text",
                                                                    style={"maxWidth": "150px"},
                                                                ),
                                                                dbc.Button(
                                                                    "Load",
                                                                    id="load-symbol-btn",
                                                                    color="primary",
                                                                    size="sm",
                                                                ),
                                                            ],
                                                            size="sm",
                                                        )
                                                    ],
                                                    width="auto",
                                                    className="ms-auto",
                                                ),
                                                dbc.Col(
                                                    [
                                                        dbc.ButtonGroup(
                                                            [
                                                                dbc.Button("15m", id="tf-15m", size="sm", outline=True),
                                                                dbc.Button("1h", id="tf-1h", size="sm", outline=True),
                                                                dbc.Button("4h", id="tf-4h", size="sm", outline=True),
                                                                dbc.Button("1d", id="tf-1d", size="sm", outline=True),
                                                            ]
                                                        )
                                                    ],
                                                    width="auto",
                                                ),
                                            ],
                                            align="center",
                                        )
                                    ]
                                ),
                                dbc.CardBody(
                                    [
                                        dcc.Graph(
                                            id="price-chart",
                                            style={"height": "600px"},
                                            config={
                                                "displayModeBar": True,
                                                "displaylogo": False,
                                                "modeBarButtonsToAdd": ["drawline", "drawrect", "eraseshape"],
                                            },
                                        ),
                                        dcc.Interval(
                                            id="interval-component",
                                            interval=15 * 1000,  # 15 секунд
                                            n_intervals=0,
                                        ),
                                    ]
                                ),
                            ],
                            className="mb-4",
                        )
                    ],
                    width=9,
                ),
                # Боковая панель (правая колонка - 3 из 12)
                dbc.Col(
                    [
                        # Volume Profile
                        dbc.Card(
                            [
                                dbc.CardHeader("Volume Profile"),
                                dbc.CardBody([dcc.Graph(id="volume-profile", style={"height": "250px"})]),
                            ],
                            className="mb-3",
                        ),
                        # Active Signals
                        dbc.Card(
                            [dbc.CardHeader("🎯 Active Signals"), dbc.CardBody([html.Div(id="signals-panel")])],
                            className="mb-3",
                        ),
                        # Quick Metrics
                        dbc.Card([dbc.CardHeader("📈 Quick Metrics"), dbc.CardBody([html.Div(id="metrics-panel")])]),
                    ],
                    width=3,
                ),
            ]
        ),
        # Tabs для дополнительных виджетов
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        dbc.Tabs(
                                            [
                                                dbc.Tab(
                                                    label="📊 Footprint Chart",
                                                    tab_id="footprint",
                                                    activeTabClassName="fw-bold",
                                                ),
                                                dbc.Tab(
                                                    label="📈 Market Profile",
                                                    tab_id="market-profile",
                                                    activeTabClassName="fw-bold",
                                                ),
                                                dbc.Tab(
                                                    label="🔗 Confluence Zones",
                                                    tab_id="confluence",
                                                    activeTabClassName="fw-bold",
                                                ),
                                                dbc.Tab(
                                                    label="📉 Backtest Results",
                                                    tab_id="backtest",
                                                    activeTabClassName="fw-bold",
                                                ),
                                                dbc.Tab(
                                                    label="⚡ Real-time Signals",
                                                    tab_id="signals",
                                                    activeTabClassName="fw-bold",
                                                ),
                                            ],
                                            id="tabs",
                                            active_tab="footprint",
                                        ),
                                        html.Div(id="tab-content", className="mt-3"),
                                    ]
                                )
                            ],
                            className="mt-4",
                        )
                    ]
                )
            ]
        ),
    ],
    fluid=True,
    className="p-4",
)


# Callback для обновления всех компонентов
@app.callback(
    [
        Output("price-chart", "figure"),
        Output("volume-profile", "figure"),
        Output("signals-panel", "children"),
        Output("metrics-panel", "children"),
        Output("status-alert", "children"),
        Output("status-alert", "color"),
    ],
    [
        Input("interval-component", "n_intervals"),
        Input("refresh-btn", "n_clicks"),
        Input("load-symbol-btn", "n_clicks"),
    ],
    [State("price-chart", "figure"), State("symbol-input", "value")],
    prevent_initial_call=False,
)
def update_dashboard(_n_intervals, _refresh_clicks, _load_clicks, _existing_figure, symbol):
    """
    Обновление всех компонентов dashboard.
    """
    try:
        # Получаем символ (по умолчанию BTC/USDT)
        # Обрабатываем случай, когда symbol может быть None
        if symbol is None or (isinstance(symbol, str) and symbol.strip() == ""):
            symbol = "BTC/USDT"
        else:
            symbol = str(symbol).strip().upper()

        # Импортируем компоненты для создания графиков с fallback
        try:
            from components.price_chart import (
                create_price_chart_with_indicators,
            )

            # Загружаем данные для выбранного символа
            dataframe = fetch_market_data(symbol)
            price_fig = create_price_chart_with_indicators(dataframe=dataframe)
            price_fig.update_layout(title=f"{symbol} - Price Chart")
        except ImportError:
            price_fig = go.Figure().add_trace(go.Scatter(x=[1, 2, 3], y=[1, 2, 3], name="Price"))
            price_fig.update_layout(template="plotly_dark", title="Price Chart")

        try:
            from components.volume_profile_viz import (
                create_volume_profile_chart,
            )

            # Используем данные для volume profile
            if dataframe is not None and not dataframe.empty:
                # Извлекаем данные из dataframe для volume profile
                price_levels = dataframe["close"].values
                volumes = dataframe["volume"].values
                volume_fig = create_volume_profile_chart(price_levels=price_levels, volumes=volumes)
            else:
                volume_fig = create_volume_profile_chart()
        except ImportError:
            volume_fig = go.Figure().add_trace(go.Bar(x=[1, 2, 3], y=[1, 2, 3], name="Volume"))
            volume_fig.update_layout(template="plotly_dark", title="Volume Profile")

        # Signals panel
        signals: Union[html.Div, list[Any]] = html.Div("Сигналы загружаются...")
        try:
            from components.signals_panel import create_signals_panel

            signals_result = create_signals_panel()
            # Проверяем тип результата
            if isinstance(signals_result, (html.Div, list)):
                signals = signals_result
        except ImportError:
            pass

        # Metrics panel
        metrics: Union[html.Div, list[Any]] = html.Div("Метрики загружаются...")
        try:
            from components.metrics_panel import create_metrics_panel

            metrics_result = create_metrics_panel()
            # Проверяем тип результата
            if isinstance(metrics_result, (html.Div, list)):
                metrics = metrics_result
        except ImportError:
            pass

        # Status
        status_msg = f"✅ System Online | Symbol: {symbol} | Last update: {datetime.now().strftime('%H:%M:%S')}"
        status_color = "success"

        return (price_fig, volume_fig, signals, metrics, status_msg, status_color)

    except (ImportError, AttributeError, KeyError, ValueError) as e:
        logger.error("Error updating dashboard: %s", str(e), exc_info=True)
        error_msg = f"❌ Error: {e!s}"
        # Возвращаем простые fallback графики
        fallback_fig = go.Figure()
        fallback_fig.add_trace(go.Scatter(x=[1], y=[1], name="Error"))
        fallback_fig.update_layout(template="plotly_dark", title="Error")
        return (fallback_fig, fallback_fig, html.Div(error_msg), html.Div(""), error_msg, "danger")


# Callback для табов
@app.callback(Output("tab-content", "children"), [Input("tabs", "active_tab")])
def update_tab_content(active_tab):
    """
    Обновление контента выбранного таба.
    """
    try:
        if active_tab == "footprint":
            try:
                from components.footprint_viz import create_footprint_chart

                return html.Div([dcc.Graph(figure=create_footprint_chart(), style={"height": "400px"})])
            except ImportError:
                msg = "Footprint компонент не найден"
                return html.Div([dbc.Alert(msg, color="info")])

        elif active_tab == "market-profile":
            try:
                from components.market_profile_viz import (
                    create_market_profile_chart,
                )

                return html.Div([dcc.Graph(figure=create_market_profile_chart(), style={"height": "400px"})])
            except ImportError:
                msg = "Market Profile компонент не найден"
                return html.Div([dbc.Alert(msg, color="info")])

        if active_tab == "confluence":
            try:
                from components.confluence_viz import create_confluence_map

                return html.Div([dcc.Graph(figure=create_confluence_map(), style={"height": "400px"})])
            except ImportError:
                msg = "Confluence компонент не найден"
                return html.Div([dbc.Alert(msg, color="info")])

        if active_tab == "backtest":
            try:
                from components.backtest_viz import create_backtest_results

                return create_backtest_results()
            except ImportError:
                msg = "Backtest компонент не найден"
                return html.Div([dbc.Alert(msg, color="info")])

        if active_tab == "signals":
            try:
                from components.realtime_signals import (
                    create_realtime_signals_panel,
                )

                return create_realtime_signals_panel()
            except ImportError:
                msg = "Signals компонент не найден"
                return html.Div([dbc.Alert(msg, color="info")])

    except (ImportError, AttributeError, KeyError, ValueError) as e:
        logger.error("Error in tab content: %s", str(e), exc_info=True)
        error_text = f"Error loading {active_tab}: {e!s}"
        return html.Div([dbc.Alert(error_text, color="danger")])

    return html.Div()


if __name__ == "__main__":

    def open_browser_delayed():
        """Открывает браузер после небольшой задержки."""
        time.sleep(3)  # Даем серверу время запуститься
        url = "http://localhost:8050"
        try:
            webbrowser.open(url)
            logger.info("Браузер открыт: %s", url)
        except (OSError, RuntimeError) as e:
            logger.warning("Не удалось открыть браузер: %s", str(e))

    logger.info("Starting MaxFlash Trading System Dashboard")
    logger.info("Dashboard available at: http://localhost:8050")

    # Запускаем открытие браузера в фоне
    # (если не запущено через run.py)
    if not os.environ.get("MAXFLASH_NO_BROWSER"):
        browser_thread = threading.Thread(target=open_browser_delayed, daemon=True)
        browser_thread.start()

    # Production конфигурация
    app.run(
        debug=False,  # В production debug=False
        host="0.0.0.0",
        port=8050,
        dev_tools_ui=False,  # Отключаем dev tools в production
        dev_tools_props_check=False,
    )
