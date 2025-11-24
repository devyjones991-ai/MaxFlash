"""
Компонент автодополнения для поиска торговых пар.
Предоставляет выпадающий список при вводе символа.
"""

import sys
from pathlib import Path
from typing import Optional

import dash_bootstrap_components as dbc
from dash import html

# Добавляем путь к корню проекта для импорта config
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from config.market_config import POPULAR_PAIRS
except ImportError:
    # Fallback значения если config не найден
    POPULAR_PAIRS = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "AVAX/USDT"]


def create_symbol_autocomplete(
    input_id: str = "symbol-input", placeholder: str = "BTC/USDT", popular_pairs: Optional[list[str]] = None
) -> html.Div:
    """
    Создать компонент автодополнения для поиска монет.

    Args:
        input_id: ID поля ввода
        placeholder: Placeholder текст
        popular_pairs: Список популярных пар для быстрого доступа

    Returns:
        HTML компонент с автодополнением
    """
    if popular_pairs is None:
        popular_pairs = POPULAR_PAIRS[:50]

    return html.Div(
        [
            dbc.InputGroup(
                [
                    dbc.InputGroupText("💰"),
                    dbc.Input(
                        id=input_id,
                        placeholder=placeholder,
                        type="text",
                        style={"maxWidth": "200px"},
                        autoComplete="off",
                    ),
                    dbc.DropdownMenu(
                        label="📋 Популярные",
                        children=[
                            dbc.DropdownMenuItem(pair, id=f"quick-{pair.replace('/', '-')}")
                            for pair in popular_pairs[:20]
                        ],
                        toggle_style={"padding": "0.25rem 0.5rem"},
                        direction="down",
                    ),
                ],
                size="sm",
            ),
            html.Div(
                id=f"{input_id}-suggestions",
                className="position-absolute",
                style={
                    "zIndex": 1000,
                    "maxHeight": "200px",
                    "overflowY": "auto",
                    "backgroundColor": "#1e1e1e",
                    "border": "1px solid #444",
                    "borderRadius": "4px",
                    "display": "none",
                },
            ),
        ],
        className="position-relative",
    )


def create_suggestions_list(query: str, all_pairs: list[str], max_suggestions: int = 10) -> html.Div:
    """
    Создать список предложений для автодополнения.

    Args:
        query: Поисковый запрос
        all_pairs: Список всех доступных пар
        max_suggestions: Максимальное количество предложений

    Returns:
        HTML компонент со списком предложений
    """
    if not query or len(query) < 2:
        return html.Div()

    query_upper = query.upper()
    suggestions = [pair for pair in all_pairs if query_upper in pair.upper()][:max_suggestions]

    if not suggestions:
        return html.Div([dbc.Alert("Ничего не найдено", color="info", className="m-2")])

    items = []
    for pair in suggestions:
        items.append(
            html.Div(
                [
                    dbc.Button(
                        pair,
                        id={"type": "suggestion-select", "symbol": pair},
                        className="w-100 text-start",
                        color="secondary",
                        outline=True,
                        size="sm",
                    )
                ],
                className="p-1",
            )
        )

    return html.Div(items, className="p-2")
