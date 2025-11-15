"""
Callbacks для автодополнения символов.
"""
from typing import List, Optional
from dash import Input, Output, State, callback_context
from dash import html
import dash_bootstrap_components as dbc

import sys
from pathlib import Path

# Добавляем путь к корню проекта
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from config.market_config import POPULAR_PAIRS
except ImportError:
    POPULAR_PAIRS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT']
from utils.market_data_manager import MarketDataManager


def register_symbol_autocomplete_callbacks(app, data_manager=None):
    """
    Зарегистрировать callbacks для автодополнения символов.

    Args:
        app: Dash приложение
        data_manager: Менеджер данных рынка
    """
    if data_manager is None:
        data_manager = MarketDataManager()

    # Callback для быстрого выбора из dropdown
    @app.callback(
        Output('symbol-input', 'value'),
        [Input(f'quick-{pair.replace("/", "-")}', 'n_clicks') for pair in [
            'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT',
            'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT'
        ]]
    )
    def quick_select_symbol(*clicks):
        """Быстрый выбор символа из dropdown."""
        ctx = callback_context
        if ctx.triggered:
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            if trigger_id.startswith('quick-'):
                symbol = trigger_id.replace('quick-', '').replace('-', '/')
                return symbol
        return None

    # Callback для автодополнения
    @app.callback(
        [Output('symbol-input-suggestions', 'children'),
         Output('symbol-input-suggestions', 'style')],
        [Input('symbol-input', 'value')],
        [State('symbol-input', 'value')]
    )
    def update_suggestions(symbol_value):
        """Обновить список предложений при вводе."""
        if not symbol_value or len(symbol_value) < 2:
            return html.Div(), {"display": "none"}

        # Используем популярные пары для быстрого поиска
        query_upper = symbol_value.upper()
        suggestions = [
            pair for pair in POPULAR_PAIRS[:100]
            if query_upper in pair.upper()
        ][:10]

        if not suggestions:
            return html.Div(), {"display": "none"}

        items = []
        for pair in suggestions:
            items.append(
                html.Div([
                    dbc.Button(
                        pair,
                        id={"type": "suggestion-select", "symbol": pair},
                        className="w-100 text-start btn-sm",
                        color="secondary",
                        outline=True
                    )
                ], className="p-1")
            )

        return html.Div(items, className="p-2"), {"display": "block"}

    # Callback для выбора из предложений
    @app.callback(
        Output('symbol-input', 'value', allow_duplicate=True),
        [Input({'type': 'suggestion-select', 'symbol': '*'}, 'n_clicks')],
        [State({'type': 'suggestion-select', 'symbol': '*'}, 'id')],
        prevent_initial_call=True
    )
    def select_suggestion(_n_clicks, button_id):
        """Выбрать символ из предложений."""
        if button_id:
            symbol = button_id.get('symbol')
            if symbol:
                return symbol
        return None

