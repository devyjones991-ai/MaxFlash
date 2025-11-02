"""
Компонент визуализации Footprint Chart.
"""
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Optional


def create_footprint_chart(dataframe: Optional[pd.DataFrame] = None) -> go.Figure:
    """
    Создает Footprint Chart с Delta и Order Flow.
    
    Args:
        dataframe: DataFrame с footprint данными
        
    Returns:
        Plotly figure
    """
    # Тестовые данные
    if dataframe is None:
        dates = pd.date_range('2024-01-01', periods=50, freq='15min')
        np.random.seed(42)
        
        prices = 50000 + np.cumsum(np.random.randn(50) * 50)
        volumes = np.random.uniform(1000000, 3000000, 50)
        
        dataframe = pd.DataFrame({
            'open': prices * 0.999,
            'high': prices * 1.002,
            'low': prices * 0.998,
            'close': prices,
            'volume': volumes,
            'fp_buy_volume': np.where(prices > prices[0], volumes * 0.6, volumes * 0.4),
            'fp_sell_volume': np.where(prices < prices[0], volumes * 0.6, volumes * 0.4),
            'delta': np.where(prices > prices[0], volumes * 0.2, -volumes * 0.2)
        }, index=dates)
    
    # Создаем subplots
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=('Price with Footprint', 'Buy/Sell Volume', 'Delta'),
        row_heights=[0.5, 0.25, 0.25]
    )
    
    # 1. Price candlesticks
    fig.add_trace(
        go.Candlestick(
            x=dataframe.index,
            open=dataframe['open'],
            high=dataframe['high'],
            low=dataframe['low'],
            close=dataframe['close'],
            name="Price",
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        ),
        row=1, col=1
    )
    
    # 2. Buy/Sell Volume bars
    fig.add_trace(
        go.Bar(
            x=dataframe.index,
            y=dataframe['fp_buy_volume'],
            name='Buy Volume',
            marker_color='green',
            opacity=0.7
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=dataframe.index,
            y=-dataframe['fp_sell_volume'],
            name='Sell Volume',
            marker_color='red',
            opacity=0.7
        ),
        row=2, col=1
    )
    
    # 3. Delta line
    colors = ['green' if d > 0 else 'red' for d in dataframe['delta']]
    
    fig.add_trace(
        go.Scatter(
            x=dataframe.index,
            y=dataframe['delta'],
            mode='lines+markers',
            name='Delta',
            line=dict(width=2),
            marker=dict(size=6, color=colors),
            fill='tozeroy',
            fillcolor='rgba(0, 255, 255, 0.1)'
        ),
        row=3, col=1
    )
    
    # Zero line для Delta
    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=3, col=1)
    
    # Обновление layout
    fig.update_layout(
        template="plotly_dark",
        height=600,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        hovermode='x unified'
    )
    
    # Обновление осей
    fig.update_xaxes(title_text="Time", row=3, col=1)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_yaxes(title_text="Delta", row=3, col=1)
    
    return fig


