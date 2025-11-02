"""
Современные компоненты для dashboard в стиле топовых криптосайтов.
"""
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional


def create_modern_price_card(symbol: str, price: float, change: float, volume: str = "") -> html.Div:
    """
    Создает современную карточку цены.
    
    Args:
        symbol: Торговая пара (например, 'BTC/USDT')
        price: Текущая цена
        change: Изменение в процентах
        volume: Объем торгов
        
    Returns:
        Dash компонент карточки
    """
    is_positive = change >= 0
    change_emoji = "↑" if is_positive else "↓"
    
    return html.Div(
        className="price-card glass-card fade-in",
        children=[
            html.Div(symbol, className="price-symbol"),
            html.Div(
                f"${price:,.2f}",
                className="price-value"
            ),
            html.Div(
                [
                    change_emoji,
                    f"{abs(change):.2f}%"
                ],
                className=f"price-change {'positive' if is_positive else 'negative'}"
            ),
            html.Div(
                f"Vol: {volume}" if volume else "",
                style={
                    "fontSize": "0.75rem",
                    "color": "var(--text-tertiary)",
                    "marginTop": "0.5rem"
                }
            )
        ]
    )


def create_modern_stat_item(label: str, value: str, icon: str = "") -> html.Div:
    """
    Создает элемент статистики.
    
    Args:
        label: Подпись
        value: Значение
        icon: Эмодзи или иконка
        
    Returns:
        Dash компонент
    """
    return html.Div(
        className="stat-item fade-in",
        children=[
            html.Div(
                [
                    html.Span(icon, style={"fontSize": "1.5rem", "marginRight": "0.5rem"}) if icon else None,
                    html.Span(label, className="stat-label")
                ]
            ),
            html.Div(value, className="stat-value")
        ]
    )


def create_modern_signal_item(signal: Dict) -> html.Div:
    """
    Создает элемент сигнала в современном стиле.
    
    Args:
        signal: Словарь с данными сигнала
        
    Returns:
        Dash компонент
    """
    signal_type = signal.get('type', 'LONG').upper()
    is_long = signal_type == 'LONG'
    
    return html.Div(
        className="signal-item",
        children=[
            html.Div(
                signal_type,
                className=f"signal-type {'long' if is_long else 'short'}"
            ),
            html.Div(
                f"{signal.get('symbol', 'N/A')} @ ${signal.get('price', 0):,.2f}",
                style={
                    "fontWeight": "600",
                    "marginBottom": "0.25rem",
                    "color": "var(--text-primary)"
                }
            ),
            html.Div(
                [
                    f"Confluence: {signal.get('confluence', 0)} signals",
                    " • ",
                    f"Entry: ${signal.get('entry_price', 0):,.2f}"
                ],
                style={
                    "fontSize": "0.875rem",
                    "color": "var(--text-secondary)"
                }
            )
        ]
    )


def create_modern_candlestick_chart(
    dataframe: pd.DataFrame,
    show_order_blocks: bool = True,
    show_fvg: bool = True
) -> go.Figure:
    """
    Создает современный график японских свечей.
    
    Args:
        dataframe: DataFrame с OHLCV данными
        show_order_blocks: Показывать Order Blocks
        show_fvg: Показывать Fair Value Gaps
        
    Returns:
        Plotly figure
    """
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=('Price Chart', 'Volume'),
        specs=[[{"secondary_y": False}],
               [{"secondary_y": False}]]
    )
    
    # Японские свечи
    fig.add_trace(
        go.Candlestick(
            x=dataframe.index,
            open=dataframe['open'],
            high=dataframe['high'],
            low=dataframe['low'],
            close=dataframe['close'],
            name='Price',
            increasing_line_color='#0ECB81',
            decreasing_line_color='#F6465D',
            increasing_fillcolor='rgba(14, 203, 129, 0.8)',
            decreasing_fillcolor='rgba(246, 70, 93, 0.8)'
        ),
        row=1, col=1
    )
    
    # Volume bars
    colors = ['#0ECB81' if close >= open else '#F6465D'
              for close, open in zip(dataframe['close'], dataframe['open'])]
    
    fig.add_trace(
        go.Bar(
            x=dataframe.index,
            y=dataframe['volume'],
            name='Volume',
            marker_color=colors,
            marker_opacity=0.6,
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Современный layout
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, sans-serif", size=12),
        height=600,
        showlegend=False,
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis_rangeslider_visible=False,
        hovermode='x unified'
    )
    
    # Стилизация осей
    fig.update_xaxes(
        gridcolor='rgba(255, 255, 255, 0.1)',
        showgrid=True,
        zeroline=False,
        row=2, col=1
    )
    
    fig.update_yaxes(
        gridcolor='rgba(255, 255, 255, 0.1)',
        showgrid=True,
        zeroline=False,
        row=1, col=1
    )
    
    fig.update_yaxes(
        gridcolor='rgba(255, 255, 255, 0.1)',
        showgrid=True,
        zeroline=False,
        row=2, col=1
    )
    
    return fig


def create_performance_metric_card(metrics: Dict) -> html.Div:
    """
    Создает карточку с метриками производительности.
    
    Args:
        metrics: Словарь с метриками
        
    Returns:
        Dash компонент
    """
    total_pnl = metrics.get('total_pnl', 0)
    pnl_color = '#0ECB81' if total_pnl >= 0 else '#F6465D'
    pnl_sign = '+' if total_pnl >= 0 else ''
    
    return html.Div(
        className="glass-card",
        style={"padding": "1.5rem"},
        children=[
            html.Div(
                [
                    html.Span("Total P&L:", style={"color": "var(--text-secondary)"}),
                    html.Span(
                        f" {pnl_sign}${abs(total_pnl):,.2f}",
                        style={
                            "color": pnl_color,
                            "fontWeight": "700",
                            "fontSize": "1.5rem",
                            "marginLeft": "1rem"
                        }
                    )
                ],
                style={"marginBottom": "1.5rem"}
            ),
            html.Div(
                [
                    html.Div(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}", className="mb-2"),
                    html.Div(f"Win Rate: {metrics.get('win_rate', 0):.1f}%", className="mb-2"),
                    html.Div(f"Profit Factor: {metrics.get('profit_factor', 0):.2f}", className="mb-2"),
                    html.Div(f"Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%", className="mb-2"),
                ],
                style={
                    "fontSize": "0.875rem",
                    "color": "var(--text-secondary)"
                }
            )
        ]
    )

