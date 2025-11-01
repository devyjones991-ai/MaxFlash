"""
Plotly Dash Web Interface для MaxFlash Trading System.
Оптимальное отображение всех индикаторов и сигналов.
"""
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Добавляем пути к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger_config import setup_logging
try:
    from api.freqtrade_client import FreqtradeClient
except ImportError:
    # Fallback для тестирования без API
    FreqtradeClient = None

# Настройка логирования
logger = setup_logging()

# Инициализация Dash app с темной темой
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        dbc.icons.BOOTSTRAP
    ],
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ]
)

app.title = "MaxFlash Trading System Dashboard"

# Инициализация Freqtrade клиента (если доступен)
ft_client = FreqtradeClient() if FreqtradeClient else None

# Главный layout
app.layout = dbc.Container([
    # Header с навигацией
    dbc.Navbar([
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H3("📊 MaxFlash Trading System", className="mb-0"),
                    html.Small("Smart Money + Footprint + Volume Profile + Market Profile + TPO",
                             className="text-muted")
                ], width="auto"),
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("🔄 Refresh", id="refresh-btn", outline=True, color="primary"),
                        dbc.Button("⚙️ Settings", id="settings-btn", outline=True, color="secondary"),
                    ])
                ], width="auto", className="ms-auto")
            ], align="center")
        ], fluid=True)
    ], color="dark", dark=True, className="mb-4"),
    
    # Status bar
    dbc.Row([
        dbc.Col([
            dbc.Alert(id="status-alert", color="info", className="mb-3", dismissable=True)
        ])
    ]),
    
    # Основной контент
    dbc.Row([
        # Главный график (левая колонка - 9 из 12)
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H5("Price Chart with Order Blocks & FVG", className="mb-0"),
                    dbc.ButtonGroup([
                        dbc.Button("15m", id="tf-15m", size="sm", outline=True),
                        dbc.Button("1h", id="tf-1h", size="sm", outline=True),
                        dbc.Button("4h", id="tf-4h", size="sm", outline=True),
                        dbc.Button("1d", id="tf-1d", size="sm", outline=True),
                    ], className="float-end")
                ]),
                dbc.CardBody([
                    dcc.Graph(
                        id="price-chart",
                        style={"height": "600px"},
                        config={
                            "displayModeBar": True,
                            "displaylogo": False,
                            "modeBarButtonsToAdd": ["drawline", "drawrect", "eraseshape"],
                        }
                    ),
                    dcc.Interval(
                        id='interval-component',
                        interval=15*1000,  # 15 секунд
                        n_intervals=0
                    )
                ])
            ], className="mb-4")
        ], width=9),
        
        # Боковая панель (правая колонка - 3 из 12)
        dbc.Col([
            # Volume Profile
            dbc.Card([
                dbc.CardHeader("Volume Profile"),
                dbc.CardBody([
                    dcc.Graph(id="volume-profile", style={"height": "250px"})
                ])
            ], className="mb-3"),
            
            # Active Signals
            dbc.Card([
                dbc.CardHeader("🎯 Active Signals"),
                dbc.CardBody([
                    html.Div(id="signals-panel")
                ])
            ], className="mb-3"),
            
            # Quick Metrics
            dbc.Card([
                dbc.CardHeader("📈 Quick Metrics"),
                dbc.CardBody([
                    html.Div(id="metrics-panel")
                ])
            ])
        ], width=3)
    ]),
    
    # Tabs для дополнительных виджетов
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Tabs([
                        dbc.Tab(label="📊 Footprint Chart", tab_id="footprint", activeTabClassName="fw-bold"),
                        dbc.Tab(label="📈 Market Profile", tab_id="market-profile", activeTabClassName="fw-bold"),
                        dbc.Tab(label="🔗 Confluence Zones", tab_id="confluence", activeTabClassName="fw-bold"),
                        dbc.Tab(label="📉 Backtest Results", tab_id="backtest", activeTabClassName="fw-bold"),
                        dbc.Tab(label="⚡ Real-time Signals", tab_id="signals", activeTabClassName="fw-bold"),
                    ], id="tabs", active_tab="footprint"),
                    html.Div(id="tab-content", className="mt-3")
                ])
            ], className="mt-4")
        ])
    ])
], fluid=True, className="p-4")


# Callback для обновления всех компонентов
@app.callback(
    [Output('price-chart', 'figure'),
     Output('volume-profile', 'figure'),
     Output('signals-panel', 'children'),
     Output('metrics-panel', 'children'),
     Output('status-alert', 'children'),
     Output('status-alert', 'color')],
    [Input('interval-component', 'n_intervals'),
     Input('refresh-btn', 'n_clicks')],
    [State('price-chart', 'figure')]
)
def update_dashboard(n_intervals, refresh_clicks, existing_figure):
    """
    Обновление всех компонентов dashboard.
    """
    try:
        # Импортируем компоненты для создания графиков
        from components.price_chart import create_price_chart_with_indicators
        from components.volume_profile_viz import create_volume_profile_chart
        from components.signals_panel import create_signals_panel
        from components.metrics_panel import create_metrics_panel
        
        # Получаем актуальные данные
        # В реальности здесь будет запрос к Freqtrade API или БД
        
        # Price Chart
        price_fig = create_price_chart_with_indicators()
        
        # Volume Profile
        volume_fig = create_volume_profile_chart()
        
        # Signals Panel
        signals = create_signals_panel()
        
        # Metrics Panel
        metrics = create_metrics_panel()
        
        # Status
        status_msg = f"✅ System Online | Last update: {datetime.now().strftime('%H:%M:%S')}"
        status_color = "success"
        
        return price_fig, volume_fig, signals, metrics, status_msg, status_color
    
    except Exception as e:
        logger.error(f"Error updating dashboard: {e}", exc_info=True)
        error_msg = f"❌ Error: {str(e)}"
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, error_msg, "danger"


# Callback для табов
@app.callback(
    Output('tab-content', 'children'),
    [Input('tabs', 'active_tab')]
)
def update_tab_content(active_tab):
    """
    Обновление контента выбранного таба.
    """
    try:
        if active_tab == "footprint":
            from components.footprint_viz import create_footprint_chart
            return html.Div([
                dcc.Graph(
                    figure=create_footprint_chart(),
                    style={"height": "400px"}
                )
            ])
        
        elif active_tab == "market-profile":
            from components.market_profile_viz import create_market_profile_chart
            return html.Div([
                dcc.Graph(
                    figure=create_market_profile_chart(),
                    style={"height": "400px"}
                )
            ])
        
        elif active_tab == "confluence":
            from components.confluence_viz import create_confluence_map
            return html.Div([
                dcc.Graph(
                    figure=create_confluence_map(),
                    style={"height": "400px"}
                )
            ])
        
        elif active_tab == "backtest":
            from components.backtest_viz import create_backtest_results
            return create_backtest_results()
        
        elif active_tab == "signals":
            from components.realtime_signals import create_realtime_signals_panel
            return create_realtime_signals_panel()
        
    except Exception as e:
        logger.error(f"Error in tab content: {e}", exc_info=True)
        return html.Div([
            dbc.Alert(f"Error loading {active_tab}: {str(e)}", color="danger")
        ])
    
    return html.Div()


if __name__ == '__main__':
    logger.info("Starting MaxFlash Trading System Dashboard")
    logger.info("Dashboard available at: http://localhost:8050")
    app.run_server(debug=True, host='0.0.0.0', port=8050)

