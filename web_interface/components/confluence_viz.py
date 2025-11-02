"""
Компонент визуализации Confluence зон.
"""
import numpy as np
import plotly.graph_objects as go
from typing import List, Dict, Optional


def create_confluence_map(confluence_zones: List[Dict] = None) -> go.Figure:
    """
    Создает карту Confluence зон.
    
    Args:
        confluence_zones: List of confluence zones
        
    Returns:
        Plotly figure
    """
    # Тестовые данные
    if confluence_zones is None:
        confluence_zones = [
            {
                'level': 50000,
                'high': 50200,
                'low': 49800,
                'strength': 8.5,
                'signals': ['order_block', 'vp_poc', 'mp_val', 'fvg'],
                'signal_count': 4
            },
            {
                'level': 51000,
                'high': 51100,
                'low': 50900,
                'strength': 6.0,
                'signals': ['order_block', 'vp_hvn', 'fvg'],
                'signal_count': 3
            },
            {
                'level': 49500,
                'high': 49600,
                'low': 49400,
                'strength': 5.5,
                'signals': ['vp_hvn', 'mp_vah'],
                'signal_count': 2
            }
        ]
    
    fig = go.Figure()
    
    # Сортировка по силе
    sorted_zones = sorted(confluence_zones, key=lambda x: x['strength'], reverse=True)
    
    # Цветовая схема по силе
    max_strength = max(zone['strength'] for zone in confluence_zones) if confluence_zones else 10
    
    for i, zone in enumerate(sorted_zones):
        strength_pct = zone['strength'] / max_strength
        color = f'rgba(255, {int(255 * (1 - strength_pct))}, 0, {0.3 + strength_pct * 0.4})'
        
        # Зона как прямоугольник
        fig.add_trace(go.Scatter(
            x=[i - 0.3, i + 0.3, i + 0.3, i - 0.3, i - 0.3],
            y=[zone['low'], zone['low'], zone['high'], zone['high'], zone['low']],
            mode='lines',
            fill='toself',
            fillcolor=color,
            line=dict(width=2, color='white'),
            name=f"Zone {i+1}",
            hovertemplate=(
                f"<b>Confluence Zone {i+1}</b><br>"
                f"Price: ${zone['level']:,.2f}<br>"
                f"Range: ${zone['low']:,.2f} - ${zone['high']:,.2f}<br>"
                f"Strength: {zone['strength']:.1f}<br>"
                f"Signals: {zone['signal_count']}<br>"
                f"Types: {', '.join(zone['signals'])}<extra></extra>"
            )
        ))
        
        # Центральная линия уровня
        fig.add_trace(go.Scatter(
            x=[i - 0.3, i + 0.3],
            y=[zone['level'], zone['level']],
            mode='lines',
            line=dict(width=3, color='white'),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Текст со strength
        fig.add_annotation(
            x=i,
            y=zone['level'],
            text=f"{zone['strength']:.1f}",
            showarrow=False,
            font=dict(size=12, color='white', family="Arial Black"),
            bgcolor='rgba(0,0,0,0.5)',
            bordercolor='white',
            borderwidth=1
        )
    
    # Layout
    fig.update_layout(
        template="plotly_dark",
        height=400,
        title="Confluence Zones Map",
        xaxis=dict(
            title="Zone",
            tickmode='array',
            tickvals=list(range(len(sorted_zones))),
            ticktext=[f"Zone {i+1}" for i in range(len(sorted_zones))]
        ),
        yaxis_title="Price (USDT)",
        showlegend=True,
        margin=dict(l=80, r=20, t=60, b=40)
    )
    
    return fig


