"""
Callbacks для экспорта данных.
"""
from dash import Input, Output, State, callback_context
from dash import dcc
import pandas as pd
from typing import Dict, Any

from utils.market_data_manager import MarketDataManager
from config.market_config import POPULAR_PAIRS, get_sector_for_pair


def register_export_callbacks(app, data_manager=None):
    """
    Зарегистрировать callbacks для экспорта данных.

    Args:
        app: Dash приложение
        data_manager: Менеджер данных рынка
    """
    if data_manager is None:
        data_manager = MarketDataManager()

    @app.callback(
        Output('download-csv', 'data'),
        [Input('export-csv-btn', 'n_clicks')],
        [State('pairs-data-store', 'data'),
         State('pair-search-input', 'value')],
        prevent_initial_call=True
    )
    def export_to_csv(_n_clicks, stored_data, search_query):
        """Экспортировать данные в CSV."""
        try:
            # Получаем данные
            if stored_data and 'tickers' in stored_data:
                tickers = stored_data['tickers']
            else:
                tickers = data_manager.get_tickers('binance', POPULAR_PAIRS[:100])
            
            # Подготавливаем данные для экспорта
            export_data = []
            for symbol, ticker in tickers.items():
                if search_query and search_query.lower() not in symbol.lower():
                    continue
                
                export_data.append({
                    'Pair': symbol,
                    'Price': ticker.get('last', 0),
                    'Change 24h (%)': ticker.get('percentage', 0),
                    'Volume 24h': ticker.get('quoteVolume', 0),
                    'High 24h': ticker.get('high', 0),
                    'Low 24h': ticker.get('low', 0),
                    'Sector': get_sector_for_pair(symbol) or "Other"
                })
            
            # Создаем DataFrame
            df = pd.DataFrame(export_data)
            
            # Экспортируем в CSV
            return dcc.send_data_frame(
                df.to_csv,
                filename=f"market_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                index=False
            )
        except Exception as e:
            # Возвращаем пустой файл при ошибке
            return None

