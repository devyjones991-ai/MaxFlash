"""
Callbacks для компонента Watchlist (отслеживание монет).
"""

import json
import logging

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback_context, html, ClientsideFunction

logger = logging.getLogger(__name__)

import sys
from pathlib import Path

# Добавляем путь к корню проекта
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.market_data_manager import MarketDataManager

try:
    from config.market_config import POPULAR_PAIRS
except ImportError:
    POPULAR_PAIRS = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "AVAX/USDT"]

try:
    from components.watchlist import create_watchlist_item, create_watchlist_items
except ImportError:
    from web_interface.components.watchlist import create_watchlist_items


def register_watchlist_callbacks(app, data_manager=None):
    """
    Зарегистрировать callbacks для Watchlist компонента.

    Args:
        app: Dash приложение
        data_manager: Менеджер данных рынка
    """
    if data_manager is None:
        data_manager = MarketDataManager()

    # Клиентский callback для сохранения в localStorage
    app.clientside_callback(
        """
        function(data) {
            if (data && data.symbols) {
                localStorage.setItem('maxflash_watchlist', JSON.stringify(data.symbols));
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("watchlist-store", "data", allow_duplicate=True),
        Input("watchlist-store", "data"),
        prevent_initial_call=True,
    )

    @app.callback(
        Output("watchlist-store", "data", allow_duplicate=True),
        [Input("watchlist-add-btn", "n_clicks"), Input({"type": "watchlist-remove", "symbol": "*"}, "n_clicks")],
        [State("watchlist-symbol-input", "value"), State("watchlist-store", "data")],
        prevent_initial_call=True,
    )
    def update_watchlist(_add_clicks, _remove_clicks, symbol_input, stored_data):
        """Обновить список отслеживаемых монет."""
        ctx = callback_context
        if not ctx.triggered:
            return stored_data or {"symbols": ["BTC/USDT", "ETH/USDT"]}

        trigger_id = ctx.triggered[0]["prop_id"]
        symbols = stored_data.get("symbols", ["BTC/USDT", "ETH/USDT"]) if stored_data else ["BTC/USDT", "ETH/USDT"]

        # Добавление монеты
        if "watchlist-add-btn" in trigger_id and symbol_input:
            symbol = symbol_input.strip().upper()
            if symbol and symbol not in symbols:
                symbols.append(symbol)
                return {"symbols": symbols}

        # Удаление монеты
        if "watchlist-remove" in trigger_id:
            try:
                # Извлекаем symbol из trigger_id
                trigger_data = json.loads(trigger_id.split(".")[0])
                symbol_to_remove = trigger_data.get("symbol")
                if symbol_to_remove in symbols:
                    symbols.remove(symbol_to_remove)
                    return {"symbols": symbols}
            except (json.JSONDecodeError, KeyError, AttributeError):
                pass

        return stored_data or {"symbols": symbols}

    @app.callback(
        Output("watchlist-items", "children"),
        [Input("watchlist-store", "data"), Input("watchlist-interval", "n_intervals")],
    )
    def update_watchlist_display(stored_data, _n_intervals):
        """Обновить отображение списка отслеживания."""
        if not stored_data or "symbols" not in stored_data:
            return html.Div([dbc.Alert("Нет отслеживаемых монет. Добавьте монету выше.", color="info")])

        symbols = stored_data["symbols"]
        if not symbols:
            return html.Div([dbc.Alert("Нет отслеживаемых монет. Добавьте монету выше.", color="info")])

        # Ограничиваем количество одновременно загружаемых тикеров
        if len(symbols) > 20:
            symbols = symbols[:20]  # Максимум 20 монет для производительности
        return create_watchlist_items(symbols, data_manager)

    app.clientside_callback(
        ClientsideFunction(namespace="clientside", function_name="toggleWatchlistModal"),
        Output("add-watchlist-modal", "is_open"),
        [Input("add-watchlist-btn", "n_clicks"), Input("close-watchlist-modal", "n_clicks")],
        [State("add-watchlist-modal", "is_open")],
        allow_duplicate=True,
        prevent_initial_call=True,
    )

    @app.callback(
        Output("watchlist-symbol-input", "value"),
        [
            Input("watchlist-add-btn", "n_clicks"),
            Input("watchlist-quick-BTC", "n_clicks"),
            Input("watchlist-quick-ETH", "n_clicks"),
            Input("watchlist-quick-SOL", "n_clicks"),
            Input("watchlist-quick-BNB", "n_clicks"),
        ],
        [State("watchlist-symbol-input", "value")],
    )
    def clear_watchlist_input(_add, _btc, _eth, _sol, _bnb, current_value):
        """Очистить поле ввода после добавления или быстрого выбора."""
        ctx = callback_context
        if ctx.triggered:
            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
            if trigger_id == "watchlist-add-btn":
                return ""  # Очищаем поле после добавления
            elif trigger_id == "watchlist-quick-BTC":
                return "BTC/USDT"
            elif trigger_id == "watchlist-quick-ETH":
                return "ETH/USDT"
            elif trigger_id == "watchlist-quick-SOL":
                return "SOL/USDT"
            elif trigger_id == "watchlist-quick-BNB":
                return "BNB/USDT"
        return current_value

    @app.callback(
        Output("symbol-input", "value"),
        [Input({"type": "watchlist-load", "symbol": "*"}, "n_clicks")],
        [State({"type": "watchlist-load", "symbol": "*"}, "id")],
    )
    def load_symbol_from_watchlist(_n_clicks, button_id):
        """Загрузить символ из watchlist на график."""
        ctx = callback_context
        if ctx.triggered and button_id:
            symbol = button_id.get("symbol")
            if symbol:
                return symbol
        return None

    # Callback для загрузки всех доступных пар
    @app.callback(Output("all-pairs-store", "data"), [Input("watchlist-search-btn", "n_clicks")])
    def load_all_pairs(_n_clicks):
        """Загрузить все доступные пары с биржи."""
        try:
            # Используем get_all_pairs из MarketDataManager
            all_pairs = data_manager.get_all_pairs("binance")
            # Добавляем популярные пары в начало
            popular_set = set(POPULAR_PAIRS)
            other_pairs = [p for p in all_pairs if p not in popular_set]
            sorted_pairs = POPULAR_PAIRS[:100] + other_pairs[:500]  # Ограничиваем для производительности
            return {"pairs": sorted_pairs}
        except Exception as e:
            logger.warning("Ошибка загрузки всех пар: %s", str(e))
            # Fallback на популярные пары
            return {"pairs": POPULAR_PAIRS[:200]}

    # Callback для автодополнения в watchlist
    @app.callback(
        [Output("watchlist-suggestions", "children"), Output("watchlist-suggestions", "style")],
        [Input("watchlist-symbol-input", "value"), Input("all-pairs-store", "data")],
    )
    def update_watchlist_suggestions(query, pairs_data):
        """Обновить список предложений при вводе."""
        if not query or len(query) < 2:
            return html.Div(), {"display": "none"}

        query_upper = query.upper()
        # Используем только популярные пары для быстрого поиска
        pairs = pairs_data.get("pairs", []) if pairs_data else POPULAR_PAIRS[:100]

        # Ищем совпадения (оптимизированный поиск)
        suggestions = [pair for pair in pairs if query_upper in pair.upper()][:10]  # Показываем максимум 10 (уменьшено)

        if not suggestions:
            return html.Div([dbc.Alert("Ничего не найдено", color="info", className="m-2")]), {"display": "block"}

        items = []
        for pair in suggestions:
            items.append(
                html.Div(
                    [
                        dbc.Button(
                            pair,
                            id={"type": "watchlist-suggestion", "symbol": pair},
                            className="w-100 text-start btn-sm",
                            color="secondary",
                            outline=True,
                        )
                    ],
                    className="p-1",
                )
            )

        return html.Div(items, className="p-2"), {"display": "block"}

    # Callback для выбора из предложений
    @app.callback(
        Output("watchlist-symbol-input", "value", allow_duplicate=True),
        [Input({"type": "watchlist-suggestion", "symbol": "*"}, "n_clicks")],
        [State({"type": "watchlist-suggestion", "symbol": "*"}, "id")],
        prevent_initial_call=True,
    )
    def select_suggestion(_n_clicks, button_id):
        """Выбрать символ из предложений."""
        if button_id:
            symbol = button_id.get("symbol")
            if symbol:
                return symbol
        return None

    # Callback для модального окна со всеми парами
    @app.callback(
        [Output("all-pairs-modal", "is_open"), Output("all-pairs-list", "children")],
        [
            Input("watchlist-search-btn", "n_clicks"),
            Input("close-all-pairs-modal", "n_clicks"),
            Input("all-pairs-search", "value"),
        ],
        [State("all-pairs-modal", "is_open"), State("all-pairs-store", "data")],
    )
    def toggle_all_pairs_modal(search_clicks, close_clicks, search_query, is_open, pairs_data):
        """Открыть/закрыть модальное окно со всеми парами."""
        ctx = callback_context
        if not ctx.triggered:
            return False, html.Div()

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if trigger_id == "watchlist-search-btn":
            # Открываем модальное окно
            pairs = pairs_data.get("pairs", []) if pairs_data else []
            return True, create_all_pairs_list(pairs, search_query)
        elif trigger_id == "close-all-pairs-modal":
            return False, html.Div()
        elif trigger_id == "all-pairs-search":
            # Обновляем список при поиске
            pairs = pairs_data.get("pairs", []) if pairs_data else []
            return is_open, create_all_pairs_list(pairs, search_query)

        return is_open, html.Div()

    def create_all_pairs_list(pairs, search_query=None):
        """Создать список всех пар для модального окна."""
        if not pairs:
            return html.Div([dbc.Alert("Загрузка пар...", color="info")])

        # Фильтрация по поисковому запросу
        if search_query:
            query_upper = search_query.upper()
            filtered_pairs = [p for p in pairs if query_upper in p.upper()]
        else:
            filtered_pairs = pairs[:200]  # Показываем первые 200

        if not filtered_pairs:
            return html.Div([dbc.Alert("Ничего не найдено", color="warning")])

        items = []
        for pair in filtered_pairs:
            items.append(
                dbc.ListGroupItem(
                    [
                        dbc.Row(
                            [
                                dbc.Col([html.Strong(pair)], width=8),
                                dbc.Col(
                                    [
                                        dbc.Button(
                                            "➕",
                                            id={"type": "add-from-modal", "symbol": pair},
                                            color="success",
                                            size="sm",
                                            outline=True,
                                        )
                                    ],
                                    width=4,
                                    className="text-end",
                                ),
                            ]
                        )
                    ],
                    action=True,
                    className="mb-1",
                )
            )

        return dbc.ListGroup(items)

    # Callback для добавления из модального окна
    @app.callback(
        Output("watchlist-store", "data", allow_duplicate=True),
        [Input({"type": "add-from-modal", "symbol": "*"}, "n_clicks")],
        [State("watchlist-store", "data"), State({"type": "add-from-modal", "symbol": "*"}, "id")],
        prevent_initial_call=True,
    )
    def add_from_modal(_n_clicks, stored_data, button_id):
        """Добавить монету из модального окна."""
        if button_id:
            symbol = button_id.get("symbol")
            if symbol:
                symbols = stored_data.get("symbols", []) if stored_data else []
                if symbol not in symbols:
                    symbols.append(symbol)
                    return {"symbols": symbols}
        return stored_data or {"symbols": []}
