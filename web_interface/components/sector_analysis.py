"""
Sector Analysis компонент: анализ секторов криптовалютного рынка.
Классификация, визуализация, производительность секторов.
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Optional, Any
from dash import html, dcc
import dash_bootstrap_components as dbc

from utils.market_data_manager import MarketDataManager
from utils.market_analytics import MarketAnalytics
from config.market_config import (
    get_all_sectors, get_pairs_by_sector, SECTOR_CLASSIFICATION
)


def create_sector_analysis(
    data_manager: Optional[MarketDataManager] = None,
    analytics: Optional[MarketAnalytics] = None
) -> html.Div:
    """
    Создать компонент Sector Analysis.

    Args:
        data_manager: Менеджер данных рынка
        analytics: Аналитика рынка

    Returns:
        HTML компонент с анализом секторов
    """
    if data_manager is None:
        data_manager = MarketDataManager()
    if analytics is None:
        analytics = MarketAnalytics(data_manager)

    # Получаем производительность всех секторов
    sectors = get_all_sectors()
    sector_performance = {}

    for sector in sectors:
        perf = analytics.get_sector_performance(sector)
        if perf:
            sector_performance[sector] = perf

    return html.Div([
        # Обзор секторов
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📊 Распределение по секторам"),
                    dbc.CardBody([
                        dcc.Graph(
                            id="sector-distribution",
                            figure=create_sector_distribution_chart(
                                sector_performance
                            ),
                            style={"height": "400px"}
                        )
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📈 Производительность секторов"),
                    dbc.CardBody([
                        dcc.Graph(
                            id="sector-performance",
                            figure=create_sector_performance_chart(
                                sector_performance
                            ),
                            style={"height": "400px"}
                        )
                    ])
                ])
            ], width=6)
        ], className="mb-4"),

        # Детальная информация по секторам
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🔍 Детали по секторам"),
                    dbc.CardBody([
                        create_sector_details(sector_performance)
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📊 Корреляционная матрица секторов"),
                    dbc.CardBody([
                        dcc.Graph(
                            id="sector-correlation-matrix",
                            figure=create_sector_correlation_matrix(
                                sector_performance, analytics
                            ),
                            style={"height": "400px"}
                        )
                    ])
                ])
            ], width=6)
        ])
    ])


def create_sector_distribution_chart(
    sector_performance: Dict[str, Dict[str, Any]]
) -> go.Figure:
    """
    Создать pie chart распределения по секторам.

    Args:
        sector_performance: Словарь с производительностью секторов

    Returns:
        Plotly figure с pie chart
    """
    if not sector_performance:
        fig = go.Figure()
        fig.add_annotation(
            text="Нет данных для отображения",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(template="plotly_dark")
        return fig

    sectors = list(sector_performance.keys())
    pair_counts = [
        sector_performance[s]['total_pairs']
        for s in sectors
    ]

    fig = go.Figure(data=[go.Pie(
        labels=sectors,
        values=pair_counts,
        hole=0.3,
        textinfo='label+percent',
        textposition='outside'
    )])

    fig.update_layout(
        title="Распределение торговых пар по секторам",
        template="plotly_dark",
        height=400
    )

    return fig


def create_sector_performance_chart(
    sector_performance: Dict[str, Dict[str, Any]]
) -> go.Figure:
    """
    Создать bar chart производительности секторов.

    Args:
        sector_performance: Словарь с производительностью секторов

    Returns:
        Plotly figure с bar chart
    """
    if not sector_performance:
        fig = go.Figure()
        fig.add_annotation(
            text="Нет данных для отображения",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(template="plotly_dark")
        return fig

    sectors = list(sector_performance.keys())
    bullish_percentages = [
        sector_performance[s].get('bullish_percentage', 0)
        for s in sectors
    ]
    avg_changes = [
        sector_performance[s].get('avg_price_change', 0)
        for s in sectors
    ]

    fig = go.Figure()

    # Добавляем bars для процента бычьих пар
    fig.add_trace(go.Bar(
        name='Bullish %',
        x=sectors,
        y=bullish_percentages,
        marker_color='green',
        yaxis='y',
        offsetgroup=1
    ))

    # Добавляем line для среднего изменения цены
    fig.add_trace(go.Scatter(
        name='Avg Change %',
        x=sectors,
        y=avg_changes,
        mode='lines+markers',
        yaxis='y2',
        line=dict(color='orange', width=2),
        marker=dict(size=8)
    ))

    fig.update_layout(
        title="Производительность секторов",
        template="plotly_dark",
        height=400,
        xaxis=dict(title="Sector"),
        yaxis=dict(
            title="Bullish Percentage (%)",
            side='left'
        ),
        yaxis2=dict(
            title="Average Price Change (%)",
            overlaying='y',
            side='right'
        ),
        legend=dict(x=0.7, y=1)
    )

    return fig


def create_sector_correlation_matrix(
    sector_performance: Dict[str, Dict[str, Any]],
    analytics: Optional[MarketAnalytics] = None
) -> go.Figure:
    """
    Создать корреляционную матрицу между секторами.

    Args:
        sector_performance: Словарь с производительностью секторов
        analytics: Аналитика рынка

    Returns:
        Plotly figure с корреляционной матрицей
    """
    if not sector_performance or analytics is None:
        fig = go.Figure()
        fig.add_annotation(
            text="Нет данных для отображения",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(template="plotly_dark")
        return fig

    try:
        from config.market_config import get_pairs_by_sector

        # Получаем по 3-5 пар из каждого сектора для анализа
        sectors = list(sector_performance.keys())
        sector_pairs = {}
        
        for sector in sectors:
            pairs = get_pairs_by_sector(sector)
            sector_pairs[sector] = pairs[:5] if len(pairs) >= 5 else pairs

        # Рассчитываем средние изменения цен для каждого сектора
        sector_returns = {}
        for sector, pairs in sector_pairs.items():
            if not pairs:
                continue
            returns = []
            for pair in pairs:
                trend = analytics.detect_trends(pair, timeframe='1d', period_days=7)
                if trend.get('price_change_24h'):
                    returns.append(trend['price_change_24h'])
            if returns:
                sector_returns[sector] = np.mean(returns)

        if len(sector_returns) < 2:
            fig = go.Figure()
            fig.add_annotation(
                text="Недостаточно данных для корреляции",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(template="plotly_dark")
            return fig

        # Создаем корреляционную матрицу (упрощенную)
        sectors_list = list(sector_returns.keys())
        correlation_data = []
        
        for s1 in sectors_list:
            row = []
            for s2 in sectors_list:
                if s1 == s2:
                    row.append(1.0)
                else:
                    # Упрощенная корреляция на основе схожести изменений
                    diff = abs(sector_returns[s1] - sector_returns[s2])
                    corr = max(0, 1 - diff / 100)  # Нормализуем
                    row.append(corr)
            correlation_data.append(row)

        fig = go.Figure(data=go.Heatmap(
            z=correlation_data,
            x=sectors_list,
            y=sectors_list,
            colorscale='RdYlBu',
            zmid=0.5,
            text=[[f"{v:.2f}" for v in row] for row in correlation_data],
            texttemplate='%{text}',
            textfont={"size": 10},
            colorbar=dict(title="Correlation")
        ))

        fig.update_layout(
            title="Корреляционная матрица секторов",
            template="plotly_dark",
            height=400
        )

        return fig
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(
            text=f"Ошибка: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(template="plotly_dark")
        return fig


def create_sector_details(
    sector_performance: Dict[str, Dict[str, Any]]
) -> html.Div:
    """
    Создать детальную информацию по секторам.

    Args:
        sector_performance: Словарь с производительностью секторов

    Returns:
        HTML компонент с деталями
    """
    if not sector_performance:
        return html.Div("Нет данных")

    cards = []
    for sector, perf in sector_performance.items():
        cards.append(
            dbc.Card([
                dbc.CardHeader(html.H5(sector, className="mb-0")),
                dbc.CardBody([
                    html.P([
                        html.Strong("Всего пар: "),
                        str(perf.get('total_pairs', 0))
                    ]),
                    html.P([
                        html.Strong("Бычьих: "),
                        html.Span(
                            str(perf.get('bullish_pairs', 0)),
                            className="text-success"
                        )
                    ]),
                    html.P([
                        html.Strong("Медвежьих: "),
                        html.Span(
                            str(perf.get('bearish_pairs', 0)),
                            className="text-danger"
                        )
                    ]),
                    html.P([
                        html.Strong("Среднее изменение: "),
                        f"{perf.get('avg_price_change', 0):.2f}%"
                    ]),
                    html.P([
                        html.Strong("Сила тренда: "),
                        f"{perf.get('avg_strength', 0):.2f}"
                    ])
                ])
            ], className="mb-3")
        )

    return html.Div(cards)

