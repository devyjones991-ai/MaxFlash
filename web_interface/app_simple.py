"""
Упрощенная версия dashboard для быстрого запуска.
Минимальные зависимости, максимальная простота.
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from datetime import datetime

    import dash
    import dash_bootstrap_components as dbc
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    from dash import Input, Output, dcc, html, dash_table
    from plotly.subplots import make_subplots

    from utils.market_data_manager import MarketDataManager
    from utils.signal_generator import SignalGenerator
    from utils.logger_config import setup_logging

    HAS_DEPS = True
    logger = setup_logging()

    # Инициализация менеджеров
    data_manager = MarketDataManager()
    signal_generator = SignalGenerator(data_manager=data_manager)

    # Топ 50 криптовалют по рыночной капитализации
    TOP_50_COINS = [
        "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
        "ADA/USDT", "AVAX/USDT", "DOGE/USDT", "DOT/USDT", "MATIC/USDT",
        "LINK/USDT", "UNI/USDT", "ATOM/USDT", "LTC/USDT", "NEAR/USDT",
        "APT/USDT", "ARB/USDT", "OP/USDT", "TIA/USDT", "FIL/USDT",
        "ICP/USDT", "STX/USDT", "IMX/USDT", "HBAR/USDT", "INJ/USDT",
        "VET/USDT", "SUI/USDT", "SEI/USDT", "RUNE/USDT", "MKR/USDT",
        "AAVE/USDT", "GRT/USDT", "FTM/USDT", "ALGO/USDT", "ETC/USDT",
        "THETA/USDT", "XLM/USDT", "FLOW/USDT", "EOS/USDT", "SAND/USDT",
        "MANA/USDT", "AXS/USDT", "KAVA/USDT", "WLD/USDT", "PEPE/USDT",
        "FET/USDT", "GALA/USDT", "CHZ/USDT", "ZIL/USDT", "ENJ/USDT"
    ]

    EXCHANGES = ["binance", "bybit", "okx", "kraken"]

except ImportError as e:
    HAS_DEPS = False
    MISSING = str(e).split("'")[1] if "'" in str(e) else "dash"


def create_simple_app():
    """Создает простое приложение."""
    if not HAS_DEPS:
        app = dash.Dash(__name__)
        app.layout = html.Div(
            [
                html.H1("❌ Зависимости не установлены"),
                html.P(f"Установите: pip install {MISSING} dash-bootstrap-components"),
                html.P("Или запустите: start_dashboard.bat (установит автоматически)"),
            ]
        )
        return app

    app = dash.Dash(
        __name__,
        external_stylesheets=[
            dbc.themes.DARKLY,
            "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap",
        ],
    )
    app.title = "MaxFlash Dashboard"

    # Добавляем кастомный CSS для dropdown меню
    app.index_string = '''
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%favicon%}
            {%css%}
            <style>
                /* === LIVE INDICATOR ANIMATION === */
                @keyframes pulse {
                    0% { opacity: 1; transform: scale(1); }
                    50% { opacity: 0.5; transform: scale(1.2); }
                    100% { opacity: 1; transform: scale(1); }
                }
                
                @keyframes glow {
                    0% { box-shadow: 0 0 5px #00ff00; }
                    50% { box-shadow: 0 0 20px #00ff00, 0 0 30px #00ff00; }
                    100% { box-shadow: 0 0 5px #00ff00; }
                }
                
                .live-dot {
                    display: inline-block;
                    width: 10px;
                    height: 10px;
                    background-color: #00ff00;
                    border-radius: 50%;
                    margin-right: 8px;
                    animation: pulse 1s infinite, glow 2s infinite;
                }

                /* === DROPDOWN DARK THEME - COMPLETE FIX === */
                
                /* Base Dash Dropdown Styling */
                .dash-dropdown {
                    background-color: #1a1a1a !important;
                }
                
                .dash-dropdown .Select-control {
                    background-color: #1a1a1a !important;
                    border: 1px solid #444 !important;
                    color: #ffffff !important;
                }
                
                .dash-dropdown .Select-menu-outer {
                    background-color: #1a1a1a !important;
                    border: 1px solid #444 !important;
                    z-index: 9999 !important;
                }
                
                .dash-dropdown .Select-menu {
                    background-color: #1a1a1a !important;
                    max-height: 300px !important;
                }
                
                .dash-dropdown .Select-option {
                    background-color: #1a1a1a !important;
                    color: #ffffff !important;
                    padding: 10px 12px !important;
                }
                
                .dash-dropdown .Select-option:hover,
                .dash-dropdown .Select-option.is-focused {
                    background-color: #00d4ff !important;
                    color: #000000 !important;
                }
                
                .dash-dropdown .Select-option.is-selected {
                    background-color: #006080 !important;
                    color: #ffffff !important;
                }
                
                .dash-dropdown .Select-value-label,
                .dash-dropdown .Select-value {
                    color: #ffffff !important;
                }
                
                .dash-dropdown .Select-placeholder {
                    color: #888 !important;
                }
                
                .dash-dropdown .Select-input input {
                    color: #ffffff !important;
                }
                
                .dash-dropdown .Select-arrow {
                    border-color: #888 transparent transparent !important;
                }
                
                .dash-dropdown .Select.is-open .Select-arrow {
                    border-color: transparent transparent #888 !important;
                }

                /* React-Select v5+ (VirtualizedSelect) - ENHANCED */
                .Select-control,
                div[class$="-control"],
                div[class*="-control "] {
                    background-color: #1a1a1a !important;
                    border-color: #444 !important;
                    min-height: 38px !important;
                    box-shadow: none !important;
                }
                
                div[class$="-control"]:hover {
                    border-color: #00d4ff !important;
                }

                /* Menu Container */
                .Select-menu-outer,
                div[class$="-menu"],
                div[class*="-menu "] {
                    background-color: #1a1a1a !important;
                    border: 1px solid #444 !important;
                    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.6) !important;
                    z-index: 9999 !important;
                    margin-top: 4px !important;
                }

                /* Menu List (scrollable area) */
                div[class$="-MenuList"],
                div[class*="-MenuList "],
                div[class$="-menuList"],
                div[class*="-menuList "] {
                    background-color: #1a1a1a !important;
                    padding: 4px !important;
                    max-height: 300px !important;
                }

                /* Individual Options */
                div[class$="-option"],
                div[class*="-option "] {
                    background-color: #1a1a1a !important;
                    color: #ffffff !important;
                    padding: 10px 12px !important;
                    cursor: pointer !important;
                    transition: background-color 0.15s ease !important;
                }

                /* Option Hover State */
                div[class$="-option"]:hover,
                div[class*="-option "]:hover,
                div[class*="option--is-focused"] {
                    background-color: #00d4ff !important;
                    color: #000000 !important;
                }

                /* Selected Option */
                div[class*="option--is-selected"] {
                    background-color: #006080 !important;
                    color: #ffffff !important;
                }
                
                div[class*="option--is-selected"]:hover {
                    background-color: #007a99 !important;
                }

                /* Single Selected Value Display */
                div[class$="-singleValue"],
                div[class*="-singleValue "] {
                    color: #ffffff !important;
                }

                /* Multi-Select Values (Tags) */
                div[class$="-multiValue"],
                div[class*="-multiValue "] {
                    background-color: #00d4ff !important;
                    border-radius: 4px !important;
                }

                div[class$="-multiValueLabel"],
                div[class*="-multiValueLabel "] {
                    color: #000000 !important;
                    padding: 3px 6px !important;
                    font-weight: 500 !important;
                }

                div[class$="-multiValueRemove"],
                div[class*="-multiValueRemove "] {
                    color: #000000 !important;
                }
                
                div[class$="-multiValueRemove"]:hover,
                div[class*="-multiValueRemove "]:hover {
                    background-color: #ff3366 !important;
                    color: #ffffff !important;
                }

                /* Placeholder Text */
                div[class$="-placeholder"],
                div[class*="-placeholder "] {
                    color: #888 !important;
                }

                /* Input Field */
                div[class$="-Input"] input,
                div[class*="-Input "] input {
                    color: #ffffff !important;
                    caret-color: #00d4ff !important;
                }

                /* Indicator Separator */
                div[class$="-indicatorSeparator"],
                div[class*="-indicatorSeparator "],
                span[class$="-indicatorSeparator"] {
                    background-color: #444 !important;
                }

                /* Dropdown/Clear Indicators */
                div[class$="-indicatorContainer"],
                div[class*="-indicatorContainer "] {
                    color: #888 !important;
                }
                
                div[class$="-indicatorContainer"]:hover,
                div[class*="-indicatorContainer "]:hover {
                    color: #00d4ff !important;
                }

                /* No Options Message */
                div[class$="-NoOptionsMessage"],
                div[class*="-NoOptionsMessage "],
                .Select-noresults {
                    color: #888 !important;
                    padding: 10px !important;
                    text-align: center !important;
                }

                /* Loading Indicator */
                div[class$="-loadingIndicator"],
                div[class*="-loadingIndicator "] {
                    color: #00d4ff !important;
                }
                
                /* === LEGACY SELECT SUPPORT === */
                .Select--single > .Select-control .Select-value {
                    color: #ffffff !important;
                }
                
                .Select.is-open > .Select-control {
                    border-color: #00d4ff !important;
                }
                
                .Select.is-focused:not(.is-open) > .Select-control {
                    border-color: #00d4ff !important;
                    box-shadow: 0 0 0 1px #00d4ff !important;
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

    app.layout = dbc.Container(
        [

            # Header
            dbc.Row([
                dbc.Col([
                    html.H1("📊 MaxFlash Live Trading Dashboard",
                           className="text-center mb-2",
                           style={"color": "#00d4ff", "fontWeight": "bold"}),
                    html.P("Real-time market data and AI trading signals",
                          className="text-center text-muted mb-4"),
                ])
            ]),

            # Status Bar with Live Indicator
            dbc.Row([
                dbc.Col([
                    dbc.Alert(
                        id="status-alert",
                        children=[
                            html.Span("🔴 ", id="live-indicator", style={
                                "animation": "pulse 1s infinite",
                                "display": "inline-block"
                            }),
                            html.Span("Dashboard загружается...", id="status-text")
                        ],
                        color="success",
                        className="mb-3"
                    )
                ], width=12)
            ]),

            # Controls Row 1
            dbc.Row([
                dbc.Col([
                    dbc.Label("Торговая пара:", className="fw-bold", style={"color": "#ffffff"}),
                    dcc.Dropdown(
                        id="symbol-dropdown",
                        options=[{"label": p, "value": p} for p in TOP_50_COINS],
                        value="BTC/USDT",
                        clearable=False,
                        searchable=True,
                        style={"backgroundColor": "#1e1e1e", "color": "#ffffff"},
                    ),
                ], md=4),
                dbc.Col([
                    dbc.Label("Биржа:", className="fw-bold", style={"color": "#ffffff"}),
                    dcc.Dropdown(
                        id="exchange-dropdown",
                        options=[
                            {"label": "Binance", "value": "binance"},
                            {"label": "Bybit", "value": "bybit"},
                            {"label": "OKX", "value": "okx"},
                            {"label": "Kraken", "value": "kraken"},
                        ],
                        value="binance",
                        clearable=False,
                        style={"backgroundColor": "#1e1e1e", "color": "#ffffff"},
                    ),
                ], md=3),
                dbc.Col([
                    dbc.Label("Таймфрейм:", className="fw-bold", style={"color": "#ffffff"}),
                    dcc.Dropdown(
                        id="timeframe-dropdown",
                        options=[{"label": tf, "value": tf} for tf in ["1m", "5m", "15m", "1h", "4h", "1d"]],
                        value="15m",
                        clearable=False,
                        style={"backgroundColor": "#1e1e1e", "color": "#ffffff"},
                    ),
                ], md=3),
                dbc.Col([
                    dbc.Label("\u00A0", className="fw-bold"),
                    dbc.ButtonGroup([
                        dbc.Button("🔄", id="refresh-button", color="primary", title="Обновить данные"),
                        dbc.Button("🎯 Сигнал", id="generate-signal-btn", color="success", title="Сгенерировать сигнал"),
                    ], className="w-100"),
                ], md=2),
            ], className="mb-3"),

            # Controls Row 2 - Chart Indicators
            dbc.Row([
                dbc.Col([
                    dbc.Label("Индикаторы:", className="fw-bold", style={"color": "#ffffff"}),
                    dcc.Dropdown(
                        id="indicators-dropdown",
                        options=[
                            {"label": "MA (20, 50, 200)", "value": "ma"},
                            {"label": "EMA (9, 21, 55)", "value": "ema"},
                            {"label": "Bollinger Bands", "value": "bb"},
                            {"label": "Volume Profile", "value": "vp"},
                            {"label": "Support/Resistance", "value": "sr"},
                        ],
                        value=["ma"],
                        multi=True,
                        style={"backgroundColor": "#1e1e1e", "color": "#ffffff"},
                    ),
                ], md=6),
                dbc.Col([
                    dbc.Label("Осцилляторы:", className="fw-bold", style={"color": "#ffffff"}),
                    dcc.Dropdown(
                        id="oscillators-dropdown",
                        options=[
                            {"label": "RSI (14)", "value": "rsi"},
                            {"label": "MACD", "value": "macd"},
                            {"label": "Stochastic", "value": "stoch"},
                        ],
                        value=[],
                        multi=True,
                        style={"backgroundColor": "#1e1e1e", "color": "#ffffff"},
                    ),
                ], md=6),
            ], className="mb-4"),

            # Main Chart - NO LOADING ANIMATION for seamless real-time updates
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("📈 Price Chart & Signals", className="mb-0"),
                                      style={"backgroundColor": "#2a2a2a"}),
                        dbc.CardBody([
                            # Graph without Loading wrapper for seamless updates
                            dcc.Graph(
                                id="main-chart", 
                                style={"height": "700px"},
                                config={
                                    'displayModeBar': True,
                                    'scrollZoom': True,
                                    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                                },
                                # Prevent flickering on update
                                animate=False,
                            ),
                        ]),
                    ], style={"backgroundColor": "#1e1e1e", "border": "1px solid #333"}),
                ], width=12)
            ], className="mb-4"),

            # Signals Table - NO LOADING ANIMATION
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("🎯 Active Signals", className="mb-0"),
                                      style={"backgroundColor": "#2a2a2a"}),
                        dbc.CardBody([
                            html.Div(id="signals-table"),
                        ]),
                    ], style={"backgroundColor": "#1e1e1e", "border": "1px solid #333"}),
                ], width=12)
            ]),

            # Auto-refresh interval - Real-time update every 3 seconds
            dcc.Interval(id="interval-update", interval=3 * 1000, n_intervals=0),
            
            # Store for caching previous data (for incremental updates)
            dcc.Store(id="cache-store", data={"last_symbol": None, "last_price": None}),
            
            # Signal notification toast
            dbc.Toast(
                id="signal-toast",
                header="🎯 Новый сигнал!",
                is_open=False,
                dismissable=True,
                duration=10000,  # 10 секунд
                icon="success",
                style={"position": "fixed", "top": 80, "right": 20, "width": 350, "zIndex": 9999},
            ),
        ],
        fluid=True,
        style={"backgroundColor": "#0a0a0a", "minHeight": "100vh", "padding": "20px"}
    )

    # Cache for optimized updates - use mutable default to persist between calls
    _dashboard_cache = {
        'last_symbol': None,
        'last_exchange': None,
        'last_timeframe': None,
        'last_df': None,
        'last_update': None,
        'signals_cache': [],
        'signal_update_counter': 0,
    }

    @app.callback(
        [
            Output("main-chart", "figure"),
            Output("signals-table", "children"),
            Output("status-alert", "children"),
        ],
        [
            Input("refresh-button", "n_clicks"),
            Input("interval-update", "n_intervals"),
            Input("symbol-dropdown", "value"),
            Input("exchange-dropdown", "value"),
            Input("timeframe-dropdown", "value"),
            Input("indicators-dropdown", "value"),
            Input("oscillators-dropdown", "value"),
        ],
        prevent_initial_call=False
    )
    def update_dashboard(n_clicks, n_intervals, symbol, exchange, timeframe, indicators, oscillators):
        """
        Обновление дашборда с реальными данными в реальном времени.
        
        Оптимизации:
        - Кэширование данных между обновлениями
        - Быстрое обновление цены каждые 3 секунды
        - Генерация сигналов каждые 5 обновлений (15 сек)
        """
        try:
            # Проверяем, изменились ли параметры (symbol, exchange, timeframe)
            params_changed = (
                _dashboard_cache['last_symbol'] != symbol or
                _dashboard_cache['last_exchange'] != exchange or
                _dashboard_cache['last_timeframe'] != timeframe
            )
            
            # Принудительное обновление при изменении параметров ИЛИ нажатии кнопки
            force_refresh = params_changed or (n_clicks is not None and n_clicks > 0)
            
            if params_changed:
                logger.info(f"Параметры изменены: {symbol} {timeframe} от {exchange}")
                _dashboard_cache['signal_update_counter'] = 0
                # Очищаем кэш сигналов при смене параметров
                _dashboard_cache['signals_cache'] = []
            
            # Получаем данные - ВСЕГДА обновляем для real-time
            df = data_manager.get_ohlcv(
                symbol=symbol, 
                timeframe=timeframe, 
                limit=200, 
                exchange_id=exchange,
                force_refresh=force_refresh  # True при смене параметров
            )

            if df is None or df.empty:
                status_content = [
                    html.Span("⚠️ ", style={"color": "#ffcc00"}),
                    html.Span(f"Нет данных для {symbol}")
                ]
                return create_empty_chart(), html.P("Нет данных"), status_content

            # Обновляем кэш
            _dashboard_cache['last_symbol'] = symbol
            _dashboard_cache['last_exchange'] = exchange
            _dashboard_cache['last_timeframe'] = timeframe
            _dashboard_cache['last_df'] = df
            _dashboard_cache['last_update'] = datetime.now()
            
            # Генерируем сигналы каждые 5 обновлений (15 сек) или при изменении параметров
            _dashboard_cache['signal_update_counter'] += 1
            if params_changed or _dashboard_cache['signal_update_counter'] >= 5:
                signals = signal_generator.generate_signals(
                    symbol=symbol, 
                    timeframe=timeframe, 
                    limit=200
                )
                _dashboard_cache['signals_cache'] = signals
                _dashboard_cache['signal_update_counter'] = 0
            else:
                signals = _dashboard_cache['signals_cache']

            # Создаем график с индикаторами
            fig = create_live_chart(df, signals, symbol, timeframe, indicators or [], oscillators or [])

            # Таблица сигналов
            signals_table = create_signals_table(signals)

            # Формируем статус с live-индикатором
            price = df['close'].iloc[-1]
            prev_price = df['close'].iloc[-2] if len(df) > 1 else price
            price_change = ((price - prev_price) / prev_price) * 100
            
            # Определяем цвет и символ изменения цены
            if price_change > 0:
                change_color = "#00ff88"
                change_symbol = "▲"
            elif price_change < 0:
                change_color = "#ff3366"
                change_symbol = "▼"
            else:
                change_color = "#ffffff"
                change_symbol = "■"
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            status_content = [
                html.Span(className="live-dot"),
                html.Span("LIVE ", style={"color": "#00ff00", "fontWeight": "bold", "marginRight": "10px"}),
                html.Span(f"{timestamp} | ", style={"color": "#888"}),
                html.Span(f"{exchange.upper()}: ", style={"color": "#00d4ff"}),
                html.Span(f"{symbol} ", style={"fontWeight": "bold"}),
                html.Span(f"${price:,.2f} ", style={"color": "#ffffff", "fontWeight": "bold"}),
                html.Span(f"{change_symbol} {abs(price_change):.2f}%", style={"color": change_color, "marginLeft": "5px"}),
                html.Span(f" | Сигналов: {len(signals)}", style={"color": "#888", "marginLeft": "10px"}),
            ]

            return fig, signals_table, status_content

        except Exception as e:
            logger.error(f"Ошибка дашборда: {e}", exc_info=True)
            status_content = [
                html.Span("❌ ", style={"color": "#ff3366"}),
                html.Span(f"Ошибка: {str(e)}")
            ]
            return create_empty_chart(), html.P("Ошибка загрузки данных"), status_content

    # Callback для генерации сигналов по кнопке
    @app.callback(
        [
            Output("signal-toast", "children"),
            Output("signal-toast", "is_open"),
            Output("signal-toast", "header"),
            Output("signal-toast", "icon"),
        ],
        [Input("generate-signal-btn", "n_clicks")],
        [
            dash.dependencies.State("symbol-dropdown", "value"),
            dash.dependencies.State("timeframe-dropdown", "value"),
        ],
        prevent_initial_call=True
    )
    def generate_signal_on_click(n_clicks, symbol, timeframe):
        """Генерация сигнала по клику на кнопку."""
        if not n_clicks:
            return "", False, "", "info"
        
        try:
            # Генерируем сигналы
            signals = signal_generator.generate_signals(
                symbol=symbol,
                timeframe=timeframe,
                limit=200
            )
            
            if signals:
                signal = signals[0]  # Берём первый (самый сильный) сигнал
                signal_type = signal.signal_type
                
                # Определяем цвет и иконку
                if signal_type == "LONG":
                    icon = "success"
                    header = "🟢 LONG Сигнал!"
                    bg_color = "#1a3d2e"
                else:
                    icon = "danger"
                    header = "🔴 SHORT Сигнал!"
                    bg_color = "#3d1a2e"
                
                content = html.Div([
                    html.P([
                        html.Strong(f"{symbol}"),
                        html.Span(f" ({timeframe})", style={"color": "#888"})
                    ]),
                    html.Hr(style={"margin": "8px 0", "borderColor": "#444"}),
                    html.Div([
                        html.Span("Entry: ", style={"color": "#888"}),
                        html.Strong(f"${signal.entry_price:,.2f}", style={"color": "#00d4ff"}),
                    ]),
                    html.Div([
                        html.Span("TP: ", style={"color": "#888"}),
                        html.Strong(f"${signal.take_profit:,.2f}", style={"color": "#00ff88"}),
                    ]),
                    html.Div([
                        html.Span("SL: ", style={"color": "#888"}),
                        html.Strong(f"${signal.stop_loss:,.2f}", style={"color": "#ff3366"}),
                    ]),
                    html.Div([
                        html.Span("Confidence: ", style={"color": "#888"}),
                        html.Strong(f"{signal.confidence:.1%}", style={"color": "#ffd700"}),
                    ], style={"marginTop": "5px"}),
                    html.Div([
                        html.Small(f"Индикаторы: {', '.join(signal.indicators[:3])}", 
                                  style={"color": "#666", "fontSize": "11px"})
                    ], style={"marginTop": "8px"}),
                ], style={"backgroundColor": bg_color, "padding": "10px", "borderRadius": "5px"})
                
                return content, True, header, icon
            else:
                return html.P("Нет сигналов на данный момент. Попробуйте другую пару или таймфрейм.", 
                             style={"color": "#888"}), True, "ℹ️ Нет сигналов", "info"
                
        except Exception as e:
            logger.error(f"Ошибка генерации сигнала: {e}")
            return html.P(f"Ошибка: {str(e)}", style={"color": "#ff3366"}), True, "❌ Ошибка", "danger"

    return app


def calculate_indicators(df: pd.DataFrame, indicators: list, oscillators: list):
    """Вычисляет технические индикаторы."""
    df = df.copy()

    # Moving Averages
    if 'ma' in indicators:
        df['ma_20'] = df['close'].rolling(window=20).mean()
        df['ma_50'] = df['close'].rolling(window=50).mean()
        df['ma_200'] = df['close'].rolling(window=200).mean()

    # EMA
    if 'ema' in indicators:
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema_55'] = df['close'].ewm(span=55, adjust=False).mean()

    # Bollinger Bands
    if 'bb' in indicators:
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)

    # Support/Resistance (простой расчет на основе локальных минимумов/максимумов)
    if 'sr' in indicators:
        df['support'] = df['low'].rolling(window=20, center=True).min()
        df['resistance'] = df['high'].rolling(window=20, center=True).max()

    # RSI
    if 'rsi' in oscillators:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

    # MACD
    if 'macd' in oscillators:
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

    # Stochastic
    if 'stoch' in oscillators:
        low_14 = df['low'].rolling(window=14).min()
        high_14 = df['high'].rolling(window=14).max()
        df['stoch_k'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
        df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()

    return df


def create_live_chart(df: pd.DataFrame, signals: list, symbol: str, timeframe: str, indicators: list, oscillators: list):
    """Создает реальный график с данными, сигналами и индикаторами."""
    # Вычисляем индикаторы
    df = calculate_indicators(df, indicators, oscillators)

    # Определяем количество рядов для графика
    num_oscillators = len(oscillators)
    total_rows = 2 + num_oscillators  # price + volume + oscillators
    row_heights = [0.5] + [0.15] * num_oscillators + [0.2]  # price, oscillators, volume

    fig = make_subplots(
        rows=total_rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=row_heights,
        subplot_titles=('Price & Indicators', *[osc.upper() for osc in oscillators], 'Volume')
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            name='Price', increasing_line_color='#00ff88', decreasing_line_color='#ff3366'
        ), row=1, col=1
    )

    # === Добавляем индикаторы на график цены ===
    # Moving Averages
    if 'ma' in indicators:
        fig.add_trace(go.Scatter(x=df.index, y=df['ma_20'], name='MA20', line=dict(color='#ffd700', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['ma_50'], name='MA50', line=dict(color='#ff6347', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['ma_200'], name='MA200', line=dict(color='#00bfff', width=1.5)), row=1, col=1)

    # EMA
    if 'ema' in indicators:
        fig.add_trace(go.Scatter(x=df.index, y=df['ema_9'], name='EMA9', line=dict(color='#adff2f', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['ema_21'], name='EMA21', line=dict(color='#ff69b4', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['ema_55'], name='EMA55', line=dict(color='#9370db', width=1)), row=1, col=1)

    # Bollinger Bands
    if 'bb' in indicators:
        fig.add_trace(go.Scatter(x=df.index, y=df['bb_upper'], name='BB Upper',
                                line=dict(color='rgba(250,128,114,0.5)', width=1, dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['bb_middle'], name='BB Middle',
                                line=dict(color='rgba(250,128,114,0.8)', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['bb_lower'], name='BB Lower',
                                line=dict(color='rgba(250,128,114,0.5)', width=1, dash='dash'),
                                fill='tonexty', fillcolor='rgba(250,128,114,0.1)'), row=1, col=1)

    # Support/Resistance
    if 'sr' in indicators:
        fig.add_trace(go.Scatter(x=df.index, y=df['support'], name='Support',
                                line=dict(color='#00ff00', width=2, dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['resistance'], name='Resistance',
                                line=dict(color='#ff0000', width=2, dash='dot')), row=1, col=1)

    # === Добавляем сигналы ===
    for signal in signals:
        color = "#00ff88" if signal.signal_type == "LONG" else "#ff3366"
        symbol_marker = "triangle-up" if signal.signal_type == "LONG" else "triangle-down"

        signal_time = signal.timestamp
        closest_idx = df.index[df.index.get_indexer([signal_time], method='nearest')[0]]

        fig.add_trace(
            go.Scatter(
                x=[closest_idx], y=[signal.entry_price],
                mode='markers',
                marker=dict(symbol=symbol_marker, size=15, color=color, line=dict(color='white', width=2)),
                name=f"{signal.signal_type}",
                showlegend=True,
                hovertemplate=f"<b>{signal.signal_type}</b><br>Entry: ${signal.entry_price:.2f}<br>" +
                             f"TP: ${signal.take_profit:.2f}<br>SL: ${signal.stop_loss:.2f}<extra></extra>"
            ), row=1, col=1
        )

        # TP/SL линии
        fig.add_hline(y=signal.take_profit, line_dash="dash", line_color="green", opacity=0.5, row=1, col=1)
        fig.add_hline(y=signal.stop_loss, line_dash="dash", line_color="red", opacity=0.5, row=1, col=1)

    # === Добавляем осцилляторы ===
    current_row = 2

    # RSI
    if 'rsi' in oscillators:
        fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], name='RSI', line=dict(color='#ffd700', width=2)),
                     row=current_row, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=current_row, col=1)
        fig.update_yaxes(title_text="RSI", range=[0, 100], row=current_row, col=1)
        current_row += 1

    # MACD
    if 'macd' in oscillators:
        fig.add_trace(go.Scatter(x=df.index, y=df['macd'], name='MACD', line=dict(color='#00bfff', width=2)),
                     row=current_row, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['macd_signal'], name='Signal', line=dict(color='#ff6347', width=2)),
                     row=current_row, col=1)
        colors_macd = ['#00ff88' if val >= 0 else '#ff3366' for val in df['macd_hist']]
        fig.add_trace(go.Bar(x=df.index, y=df['macd_hist'], name='Histogram', marker_color=colors_macd, opacity=0.5),
                     row=current_row, col=1)
        fig.update_yaxes(title_text="MACD", row=current_row, col=1)
        current_row += 1

    # Stochastic
    if 'stoch' in oscillators:
        fig.add_trace(go.Scatter(x=df.index, y=df['stoch_k'], name='%K', line=dict(color='#ffd700', width=2)),
                     row=current_row, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['stoch_d'], name='%D', line=dict(color='#ff6347', width=2)),
                     row=current_row, col=1)
        fig.add_hline(y=80, line_dash="dash", line_color="red", opacity=0.5, row=current_row, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color="green", opacity=0.5, row=current_row, col=1)
        fig.update_yaxes(title_text="Stochastic", range=[0, 100], row=current_row, col=1)
        current_row += 1

    # === Volume (всегда последний ряд) ===
    colors = ['#00ff88' if c > o else '#ff3366' for c, o in zip(df['close'], df['open'])]
    fig.add_trace(go.Bar(x=df.index, y=df['volume'], name='Volume', marker_color=colors, opacity=0.5),
                 row=total_rows, col=1)
    fig.update_yaxes(title_text="Volume", row=total_rows, col=1)

    # === Настройки макета ===
    chart_height = 600 + (num_oscillators * 150)
    fig.update_layout(
        title=dict(text=f"{symbol} - {timeframe}", font=dict(size=24, color="#00d4ff")),
        template="plotly_dark", xaxis_rangeslider_visible=False, height=chart_height,
        hovermode='x unified', plot_bgcolor='#0a0a0a', paper_bgcolor='#1e1e1e',
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        # Preserve zoom/pan state on updates
        uirevision='constant',
        # Smooth transitions
        transition={'duration': 0},
    )

    # Настройка осей
    for i in range(1, total_rows + 1):
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#2a2a2a', row=i, col=1)
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#2a2a2a', row=i, col=1)

    return fig


def create_signals_table(signals: list):
    """Создает таблицу сигналов."""
    if not signals:
        return html.P("Нет активных сигналов", className="text-muted text-center p-4")

    data = []
    for signal in signals:
        data.append({
            "Time": signal.timestamp.strftime("%H:%M:%S"),
            "Type": signal.signal_type,
            "Entry": f"${signal.entry_price:,.2f}",
            "TP": f"${signal.take_profit:.2f}",
            "SL": f"${signal.stop_loss:.2f}",
            "R:R": f"{signal.risk_reward_ratio:.2f}",
            "Confidence": f"{signal.confidence:.1%}",
        })

    return dash_table.DataTable(
        data=data,
        columns=[{"name": col, "id": col} for col in data[0].keys()],
        style_table={'overflowX': 'auto'},
        style_cell={
            'backgroundColor': '#1e1e1e', 'color': '#e0e0e0', 'border': '1px solid #333',
            'textAlign': 'left', 'padding': '10px'
        },
        style_header={'backgroundColor': '#2a2a2a', 'fontWeight': 'bold'},
        style_data_conditional=[
            {'if': {'filter_query': '{Type} = "LONG"'}, 'backgroundColor': '#1a3d2e'},
            {'if': {'filter_query': '{Type} = "SHORT"'}, 'backgroundColor': '#3d1a2e'},
        ],
        page_size=10,
    )


def create_empty_chart():
    """Пустой график."""
    fig = go.Figure()
    fig.add_annotation(text="Нет данных", xref="paper", yref="paper", x=0.5, y=0.5,
                      showarrow=False, font=dict(size=20, color="#888"))
    fig.update_layout(
        template="plotly_dark", 
        height=700, 
        plot_bgcolor='#0a0a0a', 
        paper_bgcolor='#1e1e1e',
        uirevision='constant',
        transition={'duration': 0},
    )
    return fig


if __name__ == "__main__":
    app = create_simple_app()
    app.run(debug=True, host="0.0.0.0", port=8050)
