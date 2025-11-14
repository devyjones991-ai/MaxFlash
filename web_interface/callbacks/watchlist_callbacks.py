"""
Callbacks для компонента Watchlist (отслеживание монет).
"""
import json
from typing import List, Dict, Any, Optional
from dash import Input, Output, State, callback_context
from dash import html
import dash_bootstrap_components as dbc

from utils.market_data_manager import MarketDataManager

try:
    from components.watchlist import create_watchlist_items, create_watchlist_item
except ImportError:
    from web_interface.components.watchlist import create_watchlist_items, create_watchlist_item


def register_watchlist_callbacks(app, data_manager=None):
    """
    Зарегистрировать callbacks для Watchlist компонента.

    Args:
        app: Dash приложение
        data_manager: Менеджер данных рынка
    """
    if data_manager is None:
        data_manager = MarketDataManager()

    @app.callback(
        Output('watchlist-store', 'data'),
        [Input('watchlist-add-btn', 'n_clicks'),
         Input({'type': 'watchlist-remove', 'symbol': '*'}, 'n_clicks')],
        [State('watchlist-symbol-input', 'value'),
         State('watchlist-store', 'data')]
    )
    def update_watchlist(_add_clicks, _remove_clicks, symbol_input, stored_data):
        """Обновить список отслеживаемых монет."""
        ctx = callback_context
        if not ctx.triggered:
            return stored_data or {'symbols': ['BTC/USDT', 'ETH/USDT']}

        trigger_id = ctx.triggered[0]['prop_id']
        symbols = stored_data.get('symbols', ['BTC/USDT', 'ETH/USDT']) if stored_data else ['BTC/USDT', 'ETH/USDT']

        # Добавление монеты
        if 'watchlist-add-btn' in trigger_id and symbol_input:
            symbol = symbol_input.strip().upper()
            if symbol and symbol not in symbols:
                symbols.append(symbol)
                return {'symbols': symbols}

        # Удаление монеты
        if 'watchlist-remove' in trigger_id:
            try:
                # Извлекаем symbol из trigger_id
                trigger_data = json.loads(trigger_id.split('.')[0])
                symbol_to_remove = trigger_data.get('symbol')
                if symbol_to_remove in symbols:
                    symbols.remove(symbol_to_remove)
                    return {'symbols': symbols}
            except (json.JSONDecodeError, KeyError, AttributeError):
                pass

        return stored_data or {'symbols': symbols}

    @app.callback(
        Output('watchlist-items', 'children'),
        [Input('watchlist-store', 'data'),
         Input('watchlist-interval', 'n_intervals')]
    )
    def update_watchlist_display(stored_data, _n_intervals):
        """Обновить отображение списка отслеживания."""
        if not stored_data or 'symbols' not in stored_data:
            return html.Div([
                dbc.Alert("Нет отслеживаемых монет. Добавьте монету выше.", color="info")
            ])

        symbols = stored_data['symbols']
        if not symbols:
            return html.Div([
                dbc.Alert("Нет отслеживаемых монет. Добавьте монету выше.", color="info")
            ])

        return create_watchlist_items(symbols, data_manager)

    @app.callback(
        Output('watchlist-symbol-input', 'value'),
        [Input('watchlist-add-btn', 'n_clicks')],
        [State('watchlist-symbol-input', 'value')]
    )
    def clear_watchlist_input(_n_clicks, current_value):
        """Очистить поле ввода после добавления."""
        ctx = callback_context
        if ctx.triggered and 'watchlist-add-btn' in ctx.triggered[0]['prop_id']:
            return ""  # Очищаем поле после добавления
        return current_value

    @app.callback(
        Output('symbol-input', 'value'),
        [Input({'type': 'watchlist-load', 'symbol': '*'}, 'n_clicks')],
        [State({'type': 'watchlist-load', 'symbol': '*'}, 'id')]
    )
    def load_symbol_from_watchlist(_n_clicks, button_id):
        """Загрузить символ из watchlist на график."""
        ctx = callback_context
        if ctx.triggered and button_id:
            symbol = button_id.get('symbol')
            if symbol:
                return symbol
        return None

