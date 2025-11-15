"""
Callbacks для Market Overview компонента.
Поиск пар, фильтрация, обновление данных, lazy loading.
"""
import sys
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dash import Input, Output, State, dcc
from dash import html
import dash_bootstrap_components as dbc
from dash import callback_context

try:
    from components.market_overview import create_pairs_table, create_crypto_heatmap
except ImportError:
    from web_interface.components.market_overview import (
        create_pairs_table, create_crypto_heatmap
    )

from utils.market_data_manager import MarketDataManager
from utils.async_data_loader import AsyncDataLoader
from utils.market_alerts import MarketAlerts
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


def register_market_overview_callbacks(app, data_manager=None):
    """
    Зарегистрировать callbacks для Market Overview компонента.

    Args:
        app: Dash приложение
        data_manager: Менеджер данных рынка
    """
    if data_manager is None:
        data_manager = MarketDataManager(cache_ttl_minutes=2)  # Более короткий TTL для market overview

    async_loader = AsyncDataLoader(data_manager)

    # Callback для сортировки таблицы
    @app.callback(
        Output('pairs-table-container', 'children', allow_duplicate=True),
        [Input('sort-pair-btn', 'n_clicks'),
         Input('sort-price-btn', 'n_clicks'),
         Input('sort-change-btn', 'n_clicks'),
         Input('sort-volume-btn', 'n_clicks')],
        [State('pairs-data-store', 'data'),
         State('pair-search-input', 'value')],
        prevent_initial_call=True
    )
    def sort_pairs_table(_pair, _price, _change, _volume, stored_data, search_query):
        """Сортировка таблицы пар."""
        ctx = callback_context
        sort_by = 'volume'  # По умолчанию
        
        if ctx.triggered:
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            if trigger_id == 'sort-pair-btn':
                sort_by = 'pair'
            elif trigger_id == 'sort-price-btn':
                sort_by = 'price'
            elif trigger_id == 'sort-change-btn':
                sort_by = 'change'
            elif trigger_id == 'sort-volume-btn':
                sort_by = 'volume'
        
        # Получаем данные
        if stored_data and 'tickers' in stored_data:
            tickers = stored_data['tickers']
        else:
            tickers = async_loader.load_tickers_async(
                POPULAR_PAIRS[:100], 'binance', max_workers=10
            )
            tickers = {k: v for k, v in tickers.items() if v is not None}
        
        # Подготавливаем данные
        table_data = []
        for symbol, ticker in tickers.items():
            if search_query and search_query.lower() not in symbol.lower():
                continue
            
            table_data.append({
                'Pair': symbol,
                'Price': ticker.get('last', 0),
                'Change 24h': ticker.get('percentage', 0),
                'Volume 24h': ticker.get('quoteVolume', 0),
                'High 24h': ticker.get('high', 0),
                'Low 24h': ticker.get('low', 0),
                'Sector': get_sector_for_pair(symbol) or "Other"
            })
        
        # Сортировка
        if sort_by == 'pair':
            table_data.sort(key=lambda x: x['Pair'], reverse=False)
        elif sort_by == 'price':
            table_data.sort(key=lambda x: x['Price'], reverse=True)
        elif sort_by == 'change':
            table_data.sort(key=lambda x: x['Change 24h'], reverse=True)
        else:  # volume
            table_data.sort(key=lambda x: x['Volume 24h'], reverse=True)
        
        # Создаем таблицу
        from components.market_overview import create_pairs_table
        return create_pairs_table(
            {item['Pair']: {
                'last': item['Price'],
                'percentage': item['Change 24h'],
                'quoteVolume': item['Volume 24h'],
                'high': item['High 24h'],
                'low': item['Low 24h']
            } for item in table_data},
            search_query,
            50
        )
    
    # Store для хранения состояния загруженных данных
    @app.callback(
        Output('pairs-data-store', 'data'),
        [Input('pair-search-btn', 'n_clicks'),
         Input('pair-search-input', 'n_submit')],
        [State('pair-search-input', 'value'),
         State('pairs-data-store', 'data')]
    )
    def update_pairs_data(_search_clicks, _submit, search_query, stored_data):
        """Обновить данные пар при поиске."""
        try:
            tickers = data_manager.get_tickers('binance', POPULAR_PAIRS[:100])
            return {'tickers': tickers, 'search_query': search_query}
        except Exception as e:
            return {'error': str(e)}

    @app.callback(
        Output('pairs-table-container', 'children'),
        [Input('pair-search-btn', 'n_clicks'),
         Input('pair-search-input', 'n_submit'),
         Input('load-more-pairs-btn', 'n_clicks')],
        [State('pair-search-input', 'value'),
         State('pairs-data-store', 'data')]
    )
    def update_pairs_table(_search_clicks, _submit, _load_more, search_query, stored_data):
        """
        Обновить таблицу пар с учетом поискового запроса и lazy loading.

        Args:
            _search_clicks: Количество кликов по кнопке поиска
            _submit: Количество submit событий в поле ввода
            _load_more: Количество кликов по кнопке "Загрузить еще"
            search_query: Поисковый запрос
            stored_data: Сохраненные данные из Store

        Returns:
            Обновленная таблица пар
        """
        try:
            # Определяем, сколько данных показывать
            ctx = callback_context
            display_limit = 50
            
            # Если нажата кнопка "Загрузить еще", увеличиваем лимит
            if ctx.triggered:
                trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
                if trigger_id == 'load-more-pairs-btn' and stored_data:
                    # Увеличиваем лимит на 50
                    current_limit = stored_data.get('display_limit', 50)
                    stored_data['display_limit'] = current_limit + 50
                    display_limit = stored_data['display_limit']
                elif trigger_id in ['pair-search-btn', 'pair-search-input']:
                    # Сброс лимита при новом поиске
                    if stored_data:
                        stored_data['display_limit'] = 50
                    display_limit = 50
            
            # Получаем тикеры
            if stored_data and 'tickers' in stored_data:
                tickers = stored_data['tickers']
            else:
                # Используем асинхронную загрузку для производительности
                tickers = async_loader.load_tickers_async(
                    POPULAR_PAIRS[:50], 'binance', max_workers=5  # Уменьшено для скорости
                )
                # Фильтруем None значения
                tickers = {k: v for k, v in tickers.items() if v is not None}

            # Создаем таблицу с учетом поискового запроса и лимита
            table = create_pairs_table(tickers, search_query, display_limit)

            return table
        except Exception as e:
            return html.Div([
                dbc.Alert(
                    f"Ошибка загрузки данных: {str(e)}",
                    color="danger"
                )
            ])

    @app.callback(
        Output('crypto-heatmap', 'figure'),
        [Input('heatmap-interval', 'n_intervals')]
    )
    def update_heatmap(_n_intervals):
        """
        Автоматическое обновление heatmap.

        Args:
            _n_intervals: Количество интервалов

        Returns:
            Обновленная фигура heatmap
        """
        try:
            tickers = data_manager.get_tickers('binance', POPULAR_PAIRS[:100])
            return create_crypto_heatmap(tickers)
        except Exception as e:
            # Возвращаем пустой график при ошибке
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_annotation(
                text=f"Ошибка обновления: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(template="plotly_dark")
            return fig

    @app.callback(
        Output('market-alerts-list', 'children'),
        [Input('alerts-interval', 'n_intervals')]
    )
    def update_alerts(_n_intervals):
        """
        Обновить список алертов.

        Args:
            _n_intervals: Количество интервалов

        Returns:
            HTML компонент со списком алертов
        """
        try:
            alerts_system = MarketAlerts(data_manager)
            recent_alerts = alerts_system.get_recent_alerts(limit=10)
            
            if not recent_alerts:
                return html.Div([
                    dbc.Alert("Нет активных алертов", color="info")
                ])
            
            alert_items = []
            for alert in recent_alerts:
                severity_color = {
                    'info': 'info',
                    'warning': 'warning',
                    'critical': 'danger'
                }.get(alert['severity'], 'info')
                
                alert_items.append(
                    dbc.Alert([
                        html.Strong(f"{alert['symbol']}: "),
                        alert['message'],
                        html.Br(),
                        html.Small(
                            alert['timestamp'],
                            className="text-muted"
                        )
                    ], color=severity_color, className="mb-2")
                )
            
            return html.Div(alert_items)
        except Exception as e:
            return html.Div([
                dbc.Alert(f"Ошибка загрузки алертов: {str(e)}", color="danger")
            ])

