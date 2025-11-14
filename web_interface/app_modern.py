"""
Современный веб-интерфейс в стиле топовых криптосайтов.
Вдохновлен Binance, CoinGecko, TradingView.
"""
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

try:
    from components.price_chart import create_price_chart_with_indicators
    from components.volume_profile_viz import create_volume_profile_chart
    from components.signals_panel import create_signals_panel
    from components.metrics_panel import create_metrics_panel
    HAS_COMPONENTS = True
except ImportError:
    HAS_COMPONENTS = False


# Инициализация приложения
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap"
    ]
)
app.title = "MaxFlash | Crypto Trading Dashboard"

# Загружаем кастомные стили
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link rel="stylesheet" href="/assets/modern_style.css">
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


def create_price_cards():
    """Создает карточки с ценами популярных пар."""
    pairs = [
        {"symbol": "BTC/USDT", "price": 43567.89, "change": 2.34, "volume": "2.4B"},
        {"symbol": "ETH/USDT", "price": 2645.12, "change": -1.23, "volume": "1.2B"},
        {"symbol": "BNB/USDT", "price": 312.45, "change": 0.87, "volume": "450M"},
    ]
    
    cards = []
    for pair in pairs:
        is_positive = pair["change"] >= 0
        cards.append(
            html.Div(
                className="price-card glass-card fade-in",
                style={"animationDelay": f"{pairs.index(pair) * 0.1}s"},
                children=[
                    html.Div(pair["symbol"], className="price-symbol"),
                    html.Div(
                        f"${pair['price']:,.2f}",
                        className="price-value"
                    ),
                    html.Div(
                        [
                            "↑" if is_positive else "↓",
                            f"{abs(pair['change']):.2f}%"
                        ],
                        className=f"price-change {'positive' if is_positive else 'negative'}"
                    ),
                    html.Div(
                        f"Vol: {pair['volume']}",
                        style={
                            "fontSize": "0.75rem",
                            "color": "var(--text-tertiary)",
                            "marginTop": "0.5rem"
                        }
                    )
                ]
            )
        )
    
    return cards


def create_stats_grid():
    """Создает сетку со статистикой."""
    stats = [
        {"label": "Total Signals", "value": "24", "icon": "📊"},
        {"label": "Win Rate", "value": "68%", "icon": "🎯"},
        {"label": "Avg Return", "value": "12.5%", "icon": "📈"},
        {"label": "Active Trades", "value": "8", "icon": "⚡"},
    ]
    
    return [
        html.Div(
            className="stat-item fade-in",
            style={"animationDelay": f"{i * 0.1}s"},
            children=[
                html.Div(
                    [
                        html.Span(stat["icon"], style={"fontSize": "1.5rem", "marginRight": "0.5rem"}),
                        html.Span(stat["label"], className="stat-label")
                    ]
                ),
                html.Div(stat["value"], className="stat-value")
            ]
        )
        for i, stat in enumerate(stats)
    ]


def create_modern_chart():
    """Создает современный график цены."""
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=500, freq='1H')
    np.random.seed(42)
    base_price = 43000
    prices = base_price + np.cumsum(np.random.randn(500) * 200)
    
    fig = go.Figure()
    
    # Градиентная линия цены
    fig.add_trace(go.Scatter(
        x=dates,
        y=prices,
        mode='lines',
        name='BTC/USDT',
        line=dict(
            width=3,
            color='#0ECB81'
        ),
        fill='tonexty',
        fillcolor='rgba(14, 203, 129, 0.1)',
        hovertemplate='<b>%{fullData.name}</b><br>' +
                      'Time: %{x}<br>' +
                      'Price: $%{y:,.2f}<br>' +
                      '<extra></extra>'
    ))
    
    # Обновление layout в современном стиле
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            gridcolor='rgba(255, 255, 255, 0.1)',
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            gridcolor='rgba(255, 255, 255, 0.1)',
            showgrid=True,
            zeroline=False
        ),
        hovermode='x unified',
        margin=dict(l=0, r=0, t=0, b=0),
        height=500,
        showlegend=False,
        font=dict(family="Inter, sans-serif", size=12)
    )
    
    fig.update_xaxes(
        showspikes=True,
        spikecolor="#0ECB81",
        spikesnap="cursor",
        spikemode="across",
        spikethickness=1
    )
    
    fig.update_yaxes(
        showspikes=True,
        spikecolor="#0ECB81",
        spikesnap="cursor",
        spikemode="across",
        spikethickness=1
    )
    
    return fig


# Главный layout
app.layout = html.Div(
    className="dashboard-container",
    style={"minHeight": "100vh", "background": "var(--bg-primary)"},
    children=[
        # Современный header
        html.Header(
            className="modern-header",
            children=[
                html.Div(
                    className="header-content",
                    children=[
                        html.Div(
                            className="logo-section",
                            children=[
                                html.Span("⚡", style={"fontSize": "2rem"}),
                                html.Span("MaxFlash", className="logo-text"),
                                html.Span("PRO", className="logo-badge")
                            ]
                        ),
                        html.Div(
                            className="d-flex gap-2",
                            children=[
                                html.Button(
                                    "🔄 Refresh",
                                    id="refresh-btn",
                                    className="btn-modern",
                                    style={"fontSize": "0.875rem"}
                                ),
                                html.Button(
                                    "⚙️ Settings",
                                    id="settings-btn",
                                    className="btn-modern btn-outline",
                                    style={"fontSize": "0.875rem"}
                                )
                            ]
                        )
                    ]
                )
            ]
        ),
        
        # Основной контент
        html.Main(
            style={"padding": "2rem"},
            children=[
                # Секция с ценами
                html.Section(
                    className="mb-4",
                    children=[
                        html.H2("Market Overview", className="section-title"),
                        html.Div(
                            className="stats-grid",
                            children=create_price_cards()
                        )
                    ]
                ),
                
                # Статистика
                html.Section(
                    className="mb-4",
                    children=[
                        html.Div(
                            className="stats-grid",
                            children=create_stats_grid()
                        )
                    ]
                ),
                
                # График
                html.Section(
                    className="mb-4",
                    children=[
                        html.H2("Price Chart", className="section-title"),
                        html.Div(
                            className="chart-container glass-card",
                            children=[
                                dcc.Graph(
                                    id="main-chart",
                                    figure=create_modern_chart(),
                                    config={
                                        'displayModeBar': True,
                                        'displaylogo': False,
                                        'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                                        'toImageButtonOptions': {
                                            'format': 'png',
                                            'filename': 'maxflash_chart',
                                            'height': 500,
                                            'width': 1200,
                                            'scale': 2
                                        }
                                    },
                                    style={"height": "500px", "background": "transparent"}
                                ),
                                dcc.Interval(
                                    id='interval-component',
                                    interval=30*1000,  # 30 секунд
                                    n_intervals=0
                                )
                            ]
                        )
                    ]
                ),
                
                # Сигналы и метрики
                html.Section(
                    className="mb-4",
                    children=[
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.H3("Active Signals", className="section-title"),
                                        html.Div(
                                            id="signals-container",
                                            children=[
                                                html.Div(
                                                    className="signal-item",
                                                    children=[
                                                        html.Div(
                                                            "LONG",
                                                            className="signal-type long"
                                                        ),
                                                        html.Div(
                                                            "BTC/USDT @ $43,567.89",
                                                            style={
                                                                "fontWeight": "600",
                                                                "marginBottom": "0.25rem"
                                                            }
                                                        ),
                                                        html.Div(
                                                            "Confluence: 5 signals • Entry: $43,200",
                                                            style={
                                                                "fontSize": "0.875rem",
                                                                "color": "var(--text-secondary)"
                                                            }
                                                        )
                                                    ]
                                                ),
                                                html.Div(
                                                    className="signal-item",
                                                    children=[
                                                        html.Div(
                                                            "SHORT",
                                                            className="signal-type short"
                                                        ),
                                                        html.Div(
                                                            "ETH/USDT @ $2,645.12",
                                                            style={
                                                                "fontWeight": "600",
                                                                "marginBottom": "0.25rem"
                                                            }
                                                        ),
                                                        html.Div(
                                                            "Confluence: 4 signals • Entry: $2,680",
                                                            style={
                                                                "fontSize": "0.875rem",
                                                                "color": "var(--text-secondary)"
                                                            }
                                                        )
                                                    ]
                                                )
                                            ]
                                        )
                                    ],
                                    width=6
                                ),
                                dbc.Col(
                                    [
                                        html.H3("Performance Metrics", className="section-title"),
                                        html.Div(
                                            className="glass-card",
                                            style={"padding": "1.5rem"},
                                            children=[
                                                html.Div(
                                                    [
                                                        html.Span("Total P&L:", style={"color": "var(--text-secondary)"}),
                                                        html.Span(
                                                            " +$12,450.32",
                                                            style={
                                                                "color": "var(--accent-primary)",
                                                                "fontWeight": "700",
                                                                "fontSize": "1.5rem",
                                                                "marginLeft": "1rem"
                                                            }
                                                        )
                                                    ],
                                                    style={"marginBottom": "1.5rem"}
                                                ),
                                                html.Div(
                                                    [
                                                        html.Div("Sharpe Ratio: 8.20", className="mb-2"),
                                                        html.Div("Win Rate: 68%", className="mb-2"),
                                                        html.Div("Profit Factor: 3.00", className="mb-2"),
                                                        html.Div("Max Drawdown: -2.4%", className="mb-2"),
                                                    ],
                                                    style={"fontSize": "0.875rem"}
                                                )
                                            ]
                                        )
                                    ],
                                    width=6
                                )
                            ]
                        )
                    ]
                ),
                
                # Store для данных
                dcc.Store(id='data-store', data={})
            ]
        )
    ]
)


# Callbacks
@app.callback(
    Output('main-chart', 'figure'),
    [Input('interval-component', 'n_intervals'),
     Input('refresh-btn', 'n_clicks')]
)
def update_chart(n_intervals, refresh_clicks):
    """Обновление графика."""
    return create_modern_chart()


@app.callback(
    Output('data-store', 'data'),
    [Input('interval-component', 'n_intervals')]
)
def update_data(n_intervals):
    """Обновление данных."""
    return {"timestamp": datetime.now().isoformat()}


if __name__ == '__main__':
    print("\n" + "="*60)
    print("⚡ MaxFlash Trading Dashboard - Modern Interface")
    print("="*60)
    print("🎨 Design inspired by Binance, CoinGecko, TradingView")
    print("🌐 Dashboard доступен: http://localhost:8050")
    print("⏹️  Нажмите Ctrl+C для остановки")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=8050)

