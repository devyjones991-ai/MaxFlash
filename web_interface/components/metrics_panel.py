"""
Компонент панели метрик производительности.
"""

from typing import Optional

import dash_bootstrap_components as dbc
from dash import html


def create_metrics_panel(metrics: Optional[dict] = None) -> list:
    """
    Создает панель с метриками производительности.

    Args:
        metrics: Dictionary с метриками

    Returns:
        List of Dash components
    """
    # Тестовые данные
    if metrics is None:
        metrics = {
            "win_rate": 60.0,
            "profit_factor": 3.00,
            "sharpe_ratio": 8.20,
            "total_return": 8.00,
            "max_drawdown": -1.83,
            "total_trades": 150,
            "avg_win": 200.0,
            "avg_loss": -100.0,
        }

    children = []

    # Метрики с цветовой индикацией
    metric_items = [
        ("Win Rate", f"{metrics.get('win_rate', 0):.1f}%", "success" if metrics.get("win_rate", 0) > 50 else "warning"),
        (
            "Profit Factor",
            f"{metrics.get('profit_factor', 0):.2f}",
            "success" if metrics.get("profit_factor", 0) > 1.5 else "warning",
        ),
        (
            "Sharpe Ratio",
            f"{metrics.get('sharpe_ratio', 0):.2f}",
            "success" if metrics.get("sharpe_ratio", 0) > 1.0 else "secondary",
        ),
        (
            "Total Return",
            f"{metrics.get('total_return', 0):.2f}%",
            "success" if metrics.get("total_return", 0) > 0 else "danger",
        ),
        (
            "Max DD",
            f"{metrics.get('max_drawdown', 0):.2f}%",
            "danger" if metrics.get("max_drawdown", 0) < -10 else "warning",
        ),
    ]

    for label, value, color in metric_items:
        children.append(
            dbc.Row(
                [
                    dbc.Col([html.Strong(label + ":")], width=8),
                    dbc.Col([dbc.Badge(value, color=color, className="float-end")], width=4),
                ],
                className="mb-2",
            )
        )

    # Дополнительные метрики
    children.append(html.Hr(className="my-3"))

    children.append(
        html.Div(
            [html.Strong("Total Trades: "), html.Span(f"{metrics.get('total_trades', 0)}", className="float-end")],
            className="mb-2",
        )
    )

    children.append(
        html.Div(
            [
                html.Strong("Avg Win: "),
                html.Span(f"${metrics.get('avg_win', 0):.2f}", className="float-end text-success"),
            ],
            className="mb-2",
        )
    )

    children.append(
        html.Div(
            [
                html.Strong("Avg Loss: "),
                html.Span(f"${metrics.get('avg_loss', 0):.2f}", className="float-end text-danger"),
            ]
        )
    )

    return children
