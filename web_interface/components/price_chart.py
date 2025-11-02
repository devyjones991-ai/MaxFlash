"""
Компонент графика цены с Order Blocks, FVG и другими индикаторами.
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from typing import Optional


def create_price_chart_with_indicators(
    dataframe: Optional[pd.DataFrame] = None,
    show_order_blocks: bool = True,
    show_fvg: bool = True,
    show_confluence: bool = True
) -> go.Figure:
    """
    Создает график цены с Order Blocks, FVG и другими индикаторами.
    
    Args:
        dataframe: DataFrame с OHLCV данными
        show_order_blocks: Показывать Order Blocks
        show_fvg: Показывать Fair Value Gaps
        show_confluence: Показывать Confluence zones
        
    Returns:
        Plotly figure
    """
    # Генерируем тестовые данные если не предоставлены
    if dataframe is None:
        dates = pd.date_range(start='2024-01-01', periods=200, freq='15min')
        np.random.seed(42)
        base_price = 50000
        prices = base_price + np.cumsum(np.random.randn(200) * 100)
        
        dataframe = pd.DataFrame({
            'open': prices * 0.999,
            'high': prices * 1.002,
            'low': prices * 0.998,
            'close': prices,
            'volume': np.random.uniform(1000000, 5000000, 200)
        }, index=dates)
    
    # Создаем subplots
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=('Price with Order Blocks & FVG', 'Volume', 'Delta'),
        row_heights=[0.6, 0.2, 0.2],
        specs=[[{"secondary_y": False}],
               [{"secondary_y": False}],
               [{"secondary_y": False}]]
    )
    
    # 1. Candlesticks
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
    
    # Order Blocks (пример - в реальности из детектора)
    if show_order_blocks:
        # Bullish Order Block
        ob_start_idx = 50
        ob_end_idx = 55
        ob_price = dataframe['close'].iloc[ob_start_idx]
        ob_high = dataframe['high'].iloc[ob_start_idx:ob_end_idx].max()
        ob_low = dataframe['low'].iloc[ob_start_idx:ob_end_idx].min()
        
        fig.add_trace(
            go.Scatter(
                x=[dataframe.index[ob_start_idx], dataframe.index[ob_end_idx]],
                y=[ob_low, ob_low],
                mode='lines',
                line=dict(width=0),
                fill='tonexty',
                fillcolor='rgba(0, 255, 0, 0.15)',
                name='Bullish OB',
                showlegend=True
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=[dataframe.index[ob_start_idx], dataframe.index[ob_end_idx]],
                y=[ob_high, ob_high],
                mode='lines',
                line=dict(width=2, color='green', dash='dash'),
                name='OB High',
                showlegend=False
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=[dataframe.index[ob_start_idx], dataframe.index[ob_end_idx]],
                y=[ob_low, ob_low],
                mode='lines',
                line=dict(width=2, color='green', dash='dash'),
                name='OB Low',
                showlegend=False
            ),
            row=1, col=1
        )
    
    # Fair Value Gaps (пример)
    if show_fvg:
        fvg_idx = 100
        fvg_high = dataframe['close'].iloc[fvg_idx - 2]
        fvg_low = dataframe['open'].iloc[fvg_idx]
        
        fig.add_trace(
            go.Scatter(
                x=[dataframe.index[fvg_idx - 2], dataframe.index[fvg_idx]],
                y=[fvg_low, fvg_low],
                mode='lines',
                line=dict(width=0),
                fill='tonexty',
                fillcolor='rgba(255, 255, 0, 0.1)',
                name='FVG',
                showlegend=True
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=[dataframe.index[fvg_idx - 2], dataframe.index[fvg_idx]],
                y=[fvg_high, fvg_high],
                mode='lines',
                line=dict(width=1, color='yellow', dash='dot'),
                name='FVG High',
                showlegend=False
            ),
            row=1, col=1
        )
    
    # Confluence zones (пример)
    if show_confluence:
        confluence_price = dataframe['close'].iloc[-1]
        confluence_range = confluence_price * 0.01  # 1% range
        
        fig.add_trace(
            go.Scatter(
                x=[dataframe.index[-50], dataframe.index[-1]],
                y=[confluence_price + confluence_range, confluence_price + confluence_range],
                mode='lines',
                line=dict(width=0),
                fill='tonexty',
                fillcolor='rgba(255, 0, 255, 0.1)',
                name='Confluence Zone',
                showlegend=True
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=[dataframe.index[-50], dataframe.index[-1]],
                y=[confluence_price - confluence_range, confluence_price - confluence_range],
                mode='lines',
                line=dict(width=1, color='magenta', dash='dot'),
                showlegend=False
            ),
            row=1, col=1
        )
    
    # 2. Volume bars
    colors = ['green' if close > open else 'red' 
              for close, open in zip(dataframe['close'], dataframe['open'])]
    
    fig.add_trace(
        go.Bar(
            x=dataframe.index,
            y=dataframe['volume'],
            name="Volume",
            marker_color=colors,
            marker_opacity=0.6
        ),
        row=2, col=1
    )
    
    # 3. Delta (пример)
    delta_values = np.where(
        dataframe['close'] > dataframe['open'],
        dataframe['volume'] * 0.6,  # Buying volume
        -dataframe['volume'] * 0.4   # Selling volume
    )
    
    fig.add_trace(
        go.Scatter(
            x=dataframe.index,
            y=delta_values,
            mode='lines',
            name='Delta',
            line=dict(color='cyan', width=2),
            fill='tozeroy',
            fillcolor='rgba(0, 255, 255, 0.2)'
        ),
        row=3, col=1
    )
    
    # Обновление layout
    fig.update_layout(
        template="plotly_dark",
        height=800,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    # Обновление осей
    fig.update_xaxes(title_text="Time", row=3, col=1)
    fig.update_yaxes(title_text="Price (USDT)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_yaxes(title_text="Delta", row=3, col=1)
    
    return fig


