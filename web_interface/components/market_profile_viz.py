"""
Компонент визуализации Market Profile и TPO.
"""
import numpy as np
import plotly.graph_objects as go
from typing import Optional, Dict


def create_market_profile_chart(profile_data: Optional[Dict] = None) -> go.Figure:
    """
    Создает Market Profile chart с TPO distribution.
    
    Args:
        profile_data: Dictionary с Market Profile данными
        
    Returns:
        Plotly figure
    """
    # Тестовые данные
    if profile_data is None:
        price_levels = np.linspace(48000, 52000, 30)
        tpo_counts = np.random.poisson(5, 30)
        tpo_counts[15] = tpo_counts.max() * 2  # POC
        
        profile_data = {
            'price_levels': price_levels,
            'tpo_counts': tpo_counts,
            'poc': price_levels[15],
            'vah': price_levels[20],
            'val': price_levels[10],
            'initial_balance_high': price_levels[22],
            'initial_balance_low': price_levels[18]
        }
    
    fig = go.Figure()
    
    # TPO bars (горизонтальная гистограмма)
    fig.add_trace(go.Bar(
        x=profile_data['tpo_counts'],
        y=profile_data['price_levels'],
        orientation='h',
        marker=dict(
            color=profile_data['tpo_counts'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="TPO Count")
        ),
        name='TPO Distribution',
        hovertemplate='Price: %{y:$.2f}<br>TPO: %{x}<extra></extra>'
    ))
    
    # POC line
    if 'poc' in profile_data:
        max_tpo = profile_data['tpo_counts'].max()
        fig.add_trace(go.Scatter(
            x=[0, max_tpo * 1.2],
            y=[profile_data['poc'], profile_data['poc']],
            mode='lines',
            line=dict(color='red', width=3, dash='dash'),
            name='POC'
        ))
    
    # Value Area
    if 'vah' in profile_data and 'val' in profile_data:
        # VAH
        fig.add_trace(go.Scatter(
            x=[0, profile_data['tpo_counts'].max() * 1.2],
            y=[profile_data['vah'], profile_data['vah']],
            mode='lines',
            line=dict(color='yellow', width=2),
            name='VAH'
        ))
        
        # VAL
        fig.add_trace(go.Scatter(
            x=[0, profile_data['tpo_counts'].max() * 1.2],
            y=[profile_data['val'], profile_data['val']],
            mode='lines',
            line=dict(color='yellow', width=2),
            name='VAL'
        ))
        
        # Value Area fill
        max_tpo = profile_data['tpo_counts'].max()
        fig.add_trace(go.Scatter(
            x=[0, max_tpo * 1.2, max_tpo * 1.2, 0, 0],
            y=[profile_data['val'], profile_data['val'], 
               profile_data['vah'], profile_data['vah'], profile_data['val']],
            mode='lines',
            fill='toself',
            fillcolor='rgba(255, 255, 0, 0.1)',
            line=dict(width=0),
            name='Value Area',
            showlegend=False
        ))
    
    # Initial Balance
    if 'initial_balance_high' in profile_data:
        max_tpo = profile_data['tpo_counts'].max()
        fig.add_trace(go.Scatter(
            x=[0, max_tpo * 1.2],
            y=[profile_data['initial_balance_high'], profile_data['initial_balance_high']],
            mode='lines',
            line=dict(color='cyan', width=2, dash='dot'),
            name='IB High'
        ))
        
        fig.add_trace(go.Scatter(
            x=[0, max_tpo * 1.2],
            y=[profile_data['initial_balance_low'], profile_data['initial_balance_low']],
            mode='lines',
            line=dict(color='cyan', width=2, dash='dot'),
            name='IB Low'
        ))
    
    # Layout
    fig.update_layout(
        template="plotly_dark",
        height=400,
        title="Market Profile (TPO Distribution)",
        xaxis_title="TPO Count",
        yaxis_title="Price (USDT)",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=80, r=20, t=60, b=40)
    )
    
    return fig

