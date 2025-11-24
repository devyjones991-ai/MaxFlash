"""
Упрощенная версия dashboard для быстрого запуска.
Минимальные зависимости, максимальная простота.
"""

try:
    from datetime import datetime

    import dash
    import dash_bootstrap_components as dbc
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    from dash import Input, Output, dcc, html

    HAS_DEPS = True
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

    app.layout = dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H1("📊 MaxFlash Trading Dashboard", className="text-center mb-4"),
                            dbc.Alert(
                                "✅ Dashboard запущен! Графики загружаются...", color="success", className="mb-3"
                            ),
                        ]
                    )
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("Price Chart"),
                                    dbc.CardBody(
                                        [
                                            dcc.Graph(figure=create_sample_chart(), style={"height": "600px"}),
                                            dcc.Interval(id="interval", interval=15 * 1000, n_intervals=0),
                                        ]
                                    ),
                                ]
                            )
                        ],
                        width=12,
                    )
                ]
            ),
        ],
        fluid=True,
    )

    @app.callback(Output("interval", "disabled"), [Input("interval", "n_intervals")])
    def update_chart(n):
        return False

    return app


def create_sample_chart():
    """Создает примерный график."""
    dates = pd.date_range("2024-01-01", periods=100, freq="15min")
    prices = 50000 + np.cumsum(np.random.randn(100) * 100)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=prices, mode="lines", name="Price", line={"color": "cyan", "width": 2}))
    fig.update_layout(template="plotly_dark", title="Price Chart (Пример)", height=600)
    return fig


if __name__ == "__main__":
    app = create_simple_app()
    app.run(debug=True, host="0.0.0.0", port=8050)
