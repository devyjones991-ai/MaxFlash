"""
Callbacks для Multi-View компонента.
Обновление графиков при изменении пар и таймфреймов.
"""

import sys
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dash import Input, Output, State, callback_context

try:
    from components.multi_chart_view import create_multi_chart_figure
except ImportError:
    from web_interface.components.multi_chart_view import create_multi_chart_figure

from utils.market_data_manager import MarketDataManager


def register_multi_view_callbacks(app, data_manager=None):
    """
    Зарегистрировать callbacks для Multi-View компонента.

    Args:
        app: Dash приложение
        data_manager: Менеджер данных рынка
    """
    if data_manager is None:
        data_manager = MarketDataManager()

    # Callback для обновления полей ввода при выборе из dropdown
    @app.callback(
        [
            Output("multi-symbol-1", "value"),
            Output("multi-symbol-2", "value"),
            Output("multi-symbol-3", "value"),
            Output("multi-symbol-4", "value"),
        ],
        [
            Input("pair-1-btc", "n_clicks"),
            Input("pair-1-eth", "n_clicks"),
            Input("pair-1-sol", "n_clicks"),
            Input("pair-1-bnb", "n_clicks"),
            Input("pair-2-btc", "n_clicks"),
            Input("pair-2-eth", "n_clicks"),
            Input("pair-2-sol", "n_clicks"),
            Input("pair-2-bnb", "n_clicks"),
            Input("pair-3-btc", "n_clicks"),
            Input("pair-3-eth", "n_clicks"),
            Input("pair-3-sol", "n_clicks"),
            Input("pair-3-bnb", "n_clicks"),
            Input("pair-4-btc", "n_clicks"),
            Input("pair-4-eth", "n_clicks"),
            Input("pair-4-sol", "n_clicks"),
            Input("pair-4-bnb", "n_clicks"),
        ],
        [
            State("multi-symbol-1", "value"),
            State("multi-symbol-2", "value"),
            State("multi-symbol-3", "value"),
            State("multi-symbol-4", "value"),
        ],
    )
    def update_symbol_inputs(
        _p1_btc,
        _p1_eth,
        _p1_sol,
        _p1_bnb,
        _p2_btc,
        _p2_eth,
        _p2_sol,
        _p2_bnb,
        _p3_btc,
        _p3_eth,
        _p3_sol,
        _p3_bnb,
        _p4_btc,
        _p4_eth,
        _p4_sol,
        _p4_bnb,
        symbol1,
        symbol2,
        symbol3,
        symbol4,
    ):
        """Обновить значения полей ввода при выборе из dropdown."""
        ctx = callback_context
        if ctx.triggered:
            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

            if trigger_id == "pair-1-btc":
                symbol1 = "BTC/USDT"
            elif trigger_id == "pair-1-eth":
                symbol1 = "ETH/USDT"
            elif trigger_id == "pair-1-sol":
                symbol1 = "SOL/USDT"
            elif trigger_id == "pair-1-bnb":
                symbol1 = "BNB/USDT"
            elif trigger_id == "pair-2-btc":
                symbol2 = "BTC/USDT"
            elif trigger_id == "pair-2-eth":
                symbol2 = "ETH/USDT"
            elif trigger_id == "pair-2-sol":
                symbol2 = "SOL/USDT"
            elif trigger_id == "pair-2-bnb":
                symbol2 = "BNB/USDT"
            elif trigger_id == "pair-3-btc":
                symbol3 = "BTC/USDT"
            elif trigger_id == "pair-3-eth":
                symbol3 = "ETH/USDT"
            elif trigger_id == "pair-3-sol":
                symbol3 = "SOL/USDT"
            elif trigger_id == "pair-3-bnb":
                symbol3 = "BNB/USDT"
            elif trigger_id == "pair-4-btc":
                symbol4 = "BTC/USDT"
            elif trigger_id == "pair-4-eth":
                symbol4 = "ETH/USDT"
            elif trigger_id == "pair-4-sol":
                symbol4 = "SOL/USDT"
            elif trigger_id == "pair-4-bnb":
                symbol4 = "BNB/USDT"

        return symbol1, symbol2, symbol3, symbol4

    @app.callback(
        [
            Output("multi-chart-1", "figure"),
            Output("multi-chart-2", "figure"),
            Output("multi-chart-3", "figure"),
            Output("multi-chart-4", "figure"),
            Output("multi-chart-1-header", "children"),
            Output("multi-chart-2-header", "children"),
            Output("multi-chart-3-header", "children"),
            Output("multi-chart-4-header", "children"),
        ],
        [
            Input("multi-update-btn", "n_clicks"),
            Input("multi-tf-15m", "n_clicks"),
            Input("multi-tf-1h", "n_clicks"),
            Input("multi-tf-4h", "n_clicks"),
            Input("multi-tf-1d", "n_clicks"),
            Input("multi-symbol-1", "value"),
            Input("multi-symbol-2", "value"),
            Input("multi-symbol-3", "value"),
            Input("multi-symbol-4", "value"),
        ],
        [
            State("multi-symbol-1", "value"),
            State("multi-symbol-2", "value"),
            State("multi-symbol-3", "value"),
            State("multi-symbol-4", "value"),
        ],
    )
    def update_multi_charts(_update_clicks, _tf15m, _tf1h, _tf4h, _tf1d, symbol1, symbol2, symbol3, symbol4):
        """
        Обновить все графики в Multi-View.

        Returns:
            Кортеж из 8 элементов: 4 фигуры и 4 заголовка
        """
        # Определяем таймфрейм из контекста (синхронизация между графиками)
        ctx = callback_context
        timeframe = "15m"  # По умолчанию

        if ctx.triggered:
            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

            # Обработка выбора таймфрейма
            if trigger_id == "multi-tf-15m":
                timeframe = "15m"
            elif trigger_id == "multi-tf-1h":
                timeframe = "1h"
            elif trigger_id == "multi-tf-4h":
                timeframe = "4h"
            elif trigger_id == "multi-tf-1d":
                timeframe = "1d"

        # Все графики используют один таймфрейм (синхронизация)

        # Создаем графики для каждой пары
        symbols = [symbol1, symbol2, symbol3, symbol4]
        figures = []
        headers = []

        for i, symbol in enumerate(symbols, 1):
            if symbol and symbol.strip():
                fig = create_multi_chart_figure(symbol.strip().upper(), timeframe, data_manager)
                header = f"{symbol.strip().upper()} - {timeframe}"
            else:
                # Пустой график
                import plotly.graph_objects as go

                fig = go.Figure()
                fig.add_annotation(
                    text="Выберите торговую пару", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
                )
                fig.update_layout(template="plotly_dark", title="No Data")
                header = f"Chart {i} - Empty"

            figures.append(fig)
            # Возвращаем строку, так как заголовок уже обернут в html.H5
            headers.append(header)

        return tuple(figures + headers)
