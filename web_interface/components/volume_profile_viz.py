"""
Компонент визуализации Volume Profile.
"""
import numpy as np
import plotly.graph_objects as go
from typing import Optional, Dict, List
import pandas as pd


def create_volume_profile_chart(
    price_levels: Optional[np.ndarray] = None,
    volumes: Optional[np.ndarray] = None,
    poc: Optional[float] = None,
    vah: Optional[float] = None,
    val: Optional[float] = None,
    hvn: Optional[List[float]] = None,
    lvn: Optional[List[float]] = None
) -> go.Figure:
    """
    Создает горизонтальную гистограмму Volume Profile.
    
    Args:
        price_levels: Уровни цен
        volumes: Объемы на каждом уровне
        poc: Point of Control
        vah: Value Area High
        val: Value Area Low
        hvn: High Volume Nodes
        lvn: Low Volume Nodes
        
    Returns:
        Plotly figure
    """
    # Генерация тестовых данных если не предоставлены
    if price_levels is None or volumes is None:
        price_levels = np.linspace(48000, 52000, 70)
        volumes = np.random.exponential(500000, 70)
        # POC - максимальный объем
        poc_bin = 35
        volumes[poc_bin] = volumes.max() * 1.5
        poc = price_levels[poc_bin]
        
        # Value Area (примерно 70%)
        sorted_indices = np.argsort(volumes)[::-1]
        target_volume = volumes.sum() * 0.70
        cumulative = 0
        val_bin = poc_bin
        vah_bin = poc_bin
        
        for idx in sorted_indices:
            cumulative += volumes[idx]
            if cumulative >= target_volume:
                break
            if idx < val_bin:
                val_bin = idx
            if idx > vah_bin:
                vah_bin = idx
        
        val = price_levels[val_bin]
        vah = price_levels[vah_bin]
        
        # HVN/LVN
        avg_volume = volumes.mean()
        hvn_mask = volumes >= avg_volume * 1.5
        lvn_mask = (volumes <= avg_volume * 0.5) & (volumes > 0)
        hvn = price_levels[hvn_mask].tolist()
        lvn = price_levels[lvn_mask].tolist()
    
    # Создание фигуры
    fig = go.Figure()
    
    # Основная гистограмма объема
    fig.add_trace(go.Bar(
        x=volumes,
        y=price_levels,
        orientation='h',
        marker=dict(
            color=volumes,
            colorscale='Blues',
            showscale=True,
            colorbar=dict(title="Volume")
        ),
        name='Volume',
        hovertemplate='Price: %{y:$.2f}<br>Volume: %{x:,.0f}<extra></extra>'
    ))
    
    # POC линия
    if poc:
        max_volume = volumes.max()
        fig.add_trace(go.Scatter(
            x=[0, max_volume * 1.1],
            y=[poc, poc],
            mode='lines',
            line=dict(color='red', width=3, dash='dash'),
            name='POC',
            hovertemplate='POC: $%{y:,.2f}<extra></extra>'
        ))
    
    # Value Area
    if val and vah:
        # Value Area High
        fig.add_trace(go.Scatter(
            x=[0, volumes.max() * 1.1],
            y=[vah, vah],
            mode='lines',
            line=dict(color='yellow', width=2, dash='dot'),
            name='VAH',
            hovertemplate='VAH: $%{y:,.2f}<extra></extra>'
        ))
        
        # Value Area Low
        fig.add_trace(go.Scatter(
            x=[0, volumes.max() * 1.1],
            y=[val, val],
            mode='lines',
            line=dict(color='yellow', width=2, dash='dot'),
            name='VAL',
            hovertemplate='VAL: $%{y:,.2f}<extra></extra>'
        ))
        
        # Заливка Value Area
        fig.add_trace(go.Scatter(
            x=[0, volumes.max() * 1.1, volumes.max() * 1.1, 0, 0],
            y=[val, val, vah, vah, val],
            mode='lines',
            fill='toself',
            fillcolor='rgba(255, 255, 0, 0.1)',
            line=dict(width=0),
            name='Value Area',
            showlegend=False,
            hoverinfo='skip'
        ))
    
    # HVN маркеры
    if hvn:
        hvn_volumes = [volumes[np.argmin(np.abs(price_levels - h))] for h in hvn]
        fig.add_trace(go.Scatter(
            x=hvn_volumes,
            y=hvn,
            mode='markers',
            marker=dict(
                symbol='triangle-up',
                size=10,
                color='green',
                line=dict(width=2, color='white')
            ),
            name='HVN',
            hovertemplate='HVN: $%{y:,.2f}<br>Volume: %{x:,.0f}<extra></extra>'
        ))
    
    # LVN маркеры
    if lvn:
        lvn_volumes = [volumes[np.argmin(np.abs(price_levels - l))] for l in lvn]
        fig.add_trace(go.Scatter(
            x=lvn_volumes,
            y=lvn,
            mode='markers',
            marker=dict(
                symbol='triangle-down',
                size=10,
                color='red',
                line=dict(width=2, color='white')
            ),
            name='LVN',
            hovertemplate='LVN: $%{y:,.2f}<br>Volume: %{x:,.0f}<extra></extra>'
        ))
    
    # Обновление layout
    fig.update_layout(
        template="plotly_dark",
        height=250,
        title="",
        xaxis_title="Volume",
        yaxis_title="Price (USDT)",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=80, r=20, t=10, b=40),
        xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
    )
    
    return fig

