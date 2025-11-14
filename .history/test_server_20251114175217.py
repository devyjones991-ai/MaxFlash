#!/usr/bin/env python3
"""Простой тестовый сервер для проверки."""
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.title = "MaxFlash Test Dashboard"

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("🚀 MaxFlash Trading Dashboard", className="text-center mb-4"),
            dbc.Alert("✅ Сервер успешно запущен!", color="success", className="mb-3"),
            html.P("Это тестовая версия dashboard. Все работает!", className="text-center"),
            dcc.Graph(
                figure={
                    'data': [{'x': [1, 2, 3, 4, 5], 'y': [1, 4, 2, 3, 5], 'type': 'scatter', 'mode': 'lines+markers', 'name': 'Price'}],
                    'layout': {'title': 'Price Chart', 'template': 'plotly_dark'}
                },
                style={'height': '400px'}
            )
        ])
    ])
], fluid=True)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("MaxFlash Test Dashboard")
    print("="*60)
    print("Dashboard доступен: http://localhost:8050")
    print("Нажмите Ctrl+C для остановки")
    print("="*60 + "\n")
    app.run_server(debug=True, host='127.0.0.1', port=8050)

