"""
Callbacks для системы уведомлений о ценах.
"""
import json
from typing import Dict, List, Any, Optional
from dash import Input, Output, State, callback_context
from dash import html
import dash_bootstrap_components as dbc

from utils.market_data_manager import MarketDataManager


def register_price_alerts_callbacks(app, data_manager=None):
    """
    Зарегистрировать callbacks для системы уведомлений о ценах.

    Args:
        app: Dash приложение
        data_manager: Менеджер данных рынка
    """
    if data_manager is None:
        data_manager = MarketDataManager()

    @app.callback(
        Output('alerts-store', 'data'),
        [Input('alert-add-btn', 'n_clicks'),
         Input({'type': 'alert-remove', 'symbol': '*'}, 'n_clicks')],
        [State('alert-symbol-input', 'value'),
         State('alert-price-input', 'value'),
         State('alert-type-select', 'value'),
         State('alerts-store', 'data')]
    )
    def update_alerts(_add_clicks, _remove_clicks, symbol, price, alert_type, stored_data):
        """Обновить список алертов."""
        ctx = callback_context
        if not ctx.triggered:
            return stored_data or {'alerts': []}

        trigger_id = ctx.triggered[0]['prop_id']
        alerts = stored_data.get('alerts', []) if stored_data else []

        # Добавление алерта
        if 'alert-add-btn' in trigger_id and symbol and price:
            alert_id = f"{symbol}_{price}_{alert_type}"
            # Проверяем, нет ли уже такого алерта
            if not any(a.get('id') == alert_id for a in alerts):
                alerts.append({
                    'id': alert_id,
                    'symbol': symbol.strip().upper(),
                    'price': float(price),
                    'type': alert_type,
                    'triggered': False
                })
                return {'alerts': alerts}

        # Удаление алерта
        if 'alert-remove' in trigger_id:
            try:
                trigger_data = json.loads(trigger_id.split('.')[0])
                symbol_to_remove = trigger_data.get('symbol')
                alerts = [a for a in alerts if a.get('symbol') != symbol_to_remove]
                return {'alerts': alerts}
            except (json.JSONDecodeError, KeyError, AttributeError):
                pass

        return stored_data or {'alerts': alerts}

    @app.callback(
        Output('active-alerts-list', 'children'),
        [Input('alerts-store', 'data'),
         Input('alerts-check-interval', 'n_intervals')]
    )
    def update_alerts_display(stored_data, _n_intervals):
        """Обновить отображение активных алертов и проверить их."""
        if not stored_data or 'alerts' not in stored_data:
            return html.Div([
                dbc.Alert("Нет активных уведомлений", color="info", className="mb-0")
            ])

        alerts = stored_data['alerts']
        if not alerts:
            return html.Div([
                dbc.Alert("Нет активных уведомлений", color="info", className="mb-0")
            ])

        items = []
        for alert in alerts:
            symbol = alert.get('symbol', '')
            price = alert.get('price', 0)
            alert_type = alert.get('type', 'above')
            triggered = alert.get('triggered', False)

            # Получаем текущую цену
            try:
                ticker = data_manager.get_ticker(symbol, 'binance')
                current_price = ticker.get('last', 0) if ticker else 0

                # Проверяем условие
                if alert_type == 'above' and current_price >= price:
                    triggered = True
                elif alert_type == 'below' and current_price <= price:
                    triggered = True

                type_text = "выше" if alert_type == 'above' else "ниже"
                color = "success" if triggered else "secondary"

                items.append(
                    dbc.Alert([
                        dbc.Row([
                            dbc.Col([
                                html.Strong(symbol),
                                html.Br(),
                                html.Small(
                                    f"Уведомить когда {type_text} ${price:,.2f}",
                                    className="text-muted"
                                ),
                                html.Br(),
                                html.Small(
                                    f"Текущая: ${current_price:,.2f}",
                                    className="text-info"
                                )
                            ], width=10),
                            dbc.Col([
                                dbc.Button(
                                    "❌", id={"type": "alert-remove", "symbol": symbol},
                                    color="danger", size="sm", outline=True
                                )
                            ], width=2)
                        ])
                    ], color=color, className="mb-2")
                )
            except Exception:
                items.append(
                    dbc.Alert([
                        html.Strong(symbol),
                        html.Br(),
                        html.Small(f"Ошибка получения данных", className="text-muted")
                    ], color="warning", className="mb-2")
                )

        return html.Div(items)

    @app.callback(
        [Output('alert-symbol-input', 'value'),
         Output('alert-price-input', 'value')],
        [Input('alert-add-btn', 'n_clicks')],
        [State('alert-symbol-input', 'value'),
         State('alert-price-input', 'value')]
    )
    def clear_alert_inputs(_n_clicks, symbol, price):
        """Очистить поля ввода после добавления алерта."""
        ctx = callback_context
        if ctx.triggered and 'alert-add-btn' in ctx.triggered[0]['prop_id']:
            return "", None  # Очищаем поля
        return symbol, price

