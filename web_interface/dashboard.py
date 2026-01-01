import logging
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output, State
from datetime import datetime
import plotly.graph_objects as go
import pandas as pd
import asyncio

from utils.logger_config import setup_logging
from utils.market_data_manager import MarketDataManager
# from trading.signals_service import signal_service

# Setup logging
logger = setup_logging()

# Initialize Dash app with dark theme
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG, "/assets/neon.css"],
    title="MaxFlash | Neon Terminal",
    update_title=None,
    suppress_callback_exceptions=True,
)
server = app.server

# Initialize Data Manager
if not hasattr(app, "_data_manager"):
    app._data_manager = MarketDataManager(cache_ttl_minutes=2)

# --- Layout Components ---


def create_header():
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(html.Img(src="/assets/logo.png", height="40px"), width="auto"),
                        dbc.Col(
                            html.H2("MAXFLASH TERMINAL", className="neon-text-blue mb-0", style={"fontWeight": "bold"}),
                            width="auto",
                            className="d-flex align-items-center",
                        ),
                        dbc.Col(
                            html.Div(
                                [
                                    html.Span("● LIVE", className="live-indicator", style={"marginRight": "8px"}),
                                    html.Span(id="server-time", className="text-muted small"),
                                ],
                                style={"display": "flex", "alignItems": "center"}
                            ),
                            width="auto",
                            className="d-flex align-items-center ms-3",
                        ),
                    ],
                    align="center",
                    className="g-0",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Button(
                                "⚡ TELEGRAM BOT",
                                href="https://t.me/MaxFlashBot",
                                target="_blank",
                                className="btn-primary me-2",
                                size="sm",
                            ),
                            width="auto",
                        ),
                        dbc.Col(dbc.Badge("v2.0.0", color="dark", className="border border-secondary"), width="auto"),
                    ],
                    align="center",
                    className="g-0",
                ),
            ],
            fluid=True,
        ),
        color="dark",
        dark=True,
        className="border-bottom border-secondary mb-4",
    )


def create_controls():
    return dbc.Card(
        dbc.CardBody(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Label("EXCHANGE", className="text-muted small mb-1"),
                                dbc.Select(
                                    id="exchange-select",
                                    options=[
                                        {"label": "BINANCE", "value": "binance"},
                                        {"label": "BYBIT", "value": "bybit"},
                                        {"label": "OKX", "value": "okx"},
                                        {"label": "KRAKEN", "value": "kraken"},
                                    ],
                                    value="binance",
                                    className="form-select-sm",
                                ),
                            ],
                            width=3,
                            lg=2,
                        ),
                        dbc.Col(
                            [
                                html.Label("SYMBOL", className="text-muted small mb-1"),
                                dbc.Input(
                                    id="symbol-input",
                                    value="BTC/USDT",
                                    type="text",
                                    placeholder="BTC/USDT",
                                    className="form-control-sm",
                                ),
                            ],
                            width=3,
                            lg=2,
                        ),
                        dbc.Col(
                            [
                                html.Label("TIMEFRAME", className="text-muted small mb-1"),
                                dbc.Select(
                                    id="timeframe-select",
                                    options=[
                                        {"label": "5m", "value": "5m"},
                                        {"label": "15m", "value": "15m"},
                                        {"label": "1h", "value": "1h"},
                                        {"label": "4h", "value": "4h"},
                                        {"label": "1d", "value": "1d"},
                                    ],
                                    value="15m",
                                    className="form-select-sm",
                                ),
                            ],
                            width=2,
                            lg=1,
                        ),
                        dbc.Col(
                            [
                                html.Label("ACTION", className="text-muted small mb-1 d-block"),
                                dbc.Button(
                                    "LOAD DATA", id="load-btn", n_clicks=0, className="btn-primary w-100", size="sm"
                                ),
                            ],
                            width=4,
                            lg=2,
                        ),
                        dbc.Col([html.Div(id="status-msg", className="mt-4 small text-end")], width=True),
                    ],
                    align="center",
                )
            ]
        ),
        className="mb-4",
    )


app.layout = html.Div(
    [
        create_header(),
        dbc.Container(
            [
                create_controls(),
                dcc.Loading(
                    id="loading-main",
                    type="dot",
                    color="#00f3ff",
                    children=[
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Card(
                                            dbc.CardBody(dcc.Graph(id="price-chart", style={"height": "600px"})),
                                            className="mb-4",
                                        )
                                    ],
                                    width=12,
                                    lg=8,
                                ),
                                dbc.Col(
                                    [
                                        html.H4("ACTIVE SIGNALS", className="neon-text-pink mb-3"),
                                        html.Div(id="signals-panel"),
                                    ],
                                    width=12,
                                    lg=4,
                                ),
                            ]
                        )
                    ],
                ),
            ],
            fluid=True,
        ),
        dcc.Interval(id="interval-component", interval=30 * 1000, n_intervals=0),  # 30s update
        html.Div(id="dummy-output", style={"display": "none"}),
    ],
    className="pb-5",
)

# --- Callbacks ---


@app.callback(
    [
        Output("price-chart", "figure"),
        Output("signals-panel", "children"),
        Output("status-msg", "children"),
        Output("server-time", "children"),
    ],
    [Input("load-btn", "n_clicks"), Input("interval-component", "n_intervals")],
    [State("exchange-select", "value"), State("symbol-input", "value"), State("timeframe-select", "value")],
)
def update_dashboard(n_clicks, n_intervals, exchange, symbol, timeframe):
    """Main dashboard update callback."""
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    current_time = " " + datetime.now().strftime("%H:%M:%S")

    # Default initial state
    if not n_clicks and trigger_id != "interval-component":
        return go.Figure(), html.Div("Click LOAD to start"), "", current_time

    symbol = symbol.upper().strip()
    logger.info(f"Updating dashboard for {exchange}:{symbol} ({timeframe})")

    try:
        # 1. Fetch Data
        data_manager = app._data_manager
        df = data_manager.get_ohlcv(symbol, timeframe=timeframe, exchange_id=exchange)

        if df is None or df.empty:
            return (
                go.Figure(),
                dbc.Alert(f"No data found for {symbol} on {exchange}", color="danger"),
                f"❌ Error fetching data",
                current_time,
            )

        # 2. Create Chart
        from components.price_chart import create_price_chart_with_indicators

        fig = create_price_chart_with_indicators(df, symbol)
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#b3b3b3"},
            title=dict(text=f"{exchange.upper()} : {symbol} ({timeframe})", font=dict(color="#00f3ff", size=20)),
        )

        # 3. Generate Signal
        # Run async signal generation in sync wrapper
        try:
            # Import here to avoid circular dependency
            from trading.signals_service import signal_service

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            signal_result = loop.run_until_complete(signal_service.analyze_symbol(symbol))
            loop.close()

            # Create Signal Card
            from components.signals_panel import create_signals_panel

            signal_card = create_signals_panel(symbol)

        except Exception as e:
            logger.error(f"Signal generation error: {e}")
            signal_card = dbc.Alert(f"Signal Error: {e}", color="warning")

        status = f"✅ Updated: {current_time} | Price: {df['close'].iloc[-1]:.2f}"

        return fig, signal_card, status, current_time

    except Exception as e:
        logger.error(f"Dashboard error: {e}", exc_info=True)
        return go.Figure(), dbc.Alert(f"System Error: {e}", color="danger"), "❌ System Error", current_time


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
