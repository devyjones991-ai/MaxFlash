"""
Упрощенная версия dashboard для быстрого запуска.
Минимальные зависимости, максимальная простота.
"""
try:
    import dash
    from dash import dcc, html
    import dash_bootstrap_components as dbc
    import plotly.graph_objects as go
    import pandas as pd
    import numpy as np
    from datetime import datetime
    HAS_DEPS = True
except ImportError as e:
    HAS_DEPS = False
    MISSING = str(e).split("'")[1] if "'" in str(e) else "dash"


def create_simple_app():
    """Создает простое приложение."""
    if not HAS_DEPS:
        app = dash.Dash(__name__)
        app.layout = html.Div([
            html.H1("❌ Зависимости не установлены"),
            html.P(f"Установите: pip install {MISSING} dash-bootstrap-components"),
            html.P("Или запустите: start_dashboard.bat (установит автоматически)")
        ])
        return app
    
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
    app.title = "MaxFlash Dashboard"
    
    app.layout = dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H1("📊 MaxFlash Trading Dashboard", className="text-center mb-4"),
                dbc.Alert(
                    "✅ Dashboard запущен! Графики загружаются...",
                    color="success",
                    className="mb-3"
                )
            ])
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Price Chart"),
                    dbc.CardBody([
                        dcc.Graph(
                            figure=create_sample_chart(),
                            style={"height": "600px"}
                        ),
                        dcc.Interval(id='interval', interval=15*1000, n_intervals=0)
                    ])
                ])
            ], width=12)
        ])
    ], fluid=True)
    
    @app.callback(
        dcc.Output('interval', 'disabled'),
        [dcc.Input('interval', 'n_intervals')]
    )
    def update_chart(n):
        return False
    
    return app


def create_sample_chart():
    """Создает примерный график."""
    dates = pd.date_range('2024-01-01', periods=100, freq='15min')
    prices = 50000 + np.cumsum(np.random.randn(100) * 100)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=prices,
        mode='lines',
        name='Price',
        line=dict(color='cyan', width=2)
    ))
    fig.update_layout(
        template="plotly_dark",
        title="Price Chart (Пример)",
        height=600
    )
    return fig


if __name__ == '__main__':
    app = create_simple_app()
    print("\n" + "="*60)
    print("MaxFlash Trading Dashboard")
    print("="*60)
    print("Dashboard доступен: http://localhost:8050")
    print("Нажмите Ctrl+C для остановки")
    print("="*60 + "\n")
    app.run_server(debug=True, host='0.0.0.0', port=8050)


