"""
TradingView-style chart component with technical indicators.
"""

from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate technical indicators for chart."""
    # Moving Averages
    df["ma20"] = df["close"].rolling(window=20).mean()
    df["ma50"] = df["close"].rolling(window=50).mean()

    # Bollinger Bands
    df["bb_middle"] = df["close"].rolling(window=20).mean()
    bb_std = df["close"].rolling(window=20).std()
    df["bb_upper"] = df["bb_middle"] + (bb_std * 2)
    df["bb_lower"] = df["bb_middle"] - (bb_std * 2)

    # RSI
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # MACD
    exp1 = df["close"].ewm(span=12, adjust=False).mean()
    exp2 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = exp1 - exp2
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    return df


def create_price_chart_with_indicators(
    dataframe: Optional[pd.DataFrame] = None,
    symbol: str = "BTC/USDT",
) -> go.Figure:
    """Create TradingView-style price chart with indicators."""

    # Generate test data if none provided
    if dataframe is None or dataframe.empty:
        # Return empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="Waiting for Data...",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20, color="#00f3ff"),
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis={"visible": False},
            yaxis={"visible": False},
        )
        return fig

    # Calculate indicators
    df = calculate_indicators(dataframe.copy())

    # Create subplots: Price + Volume + RSI + MACD
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.15, 0.15, 0.2],
        specs=[
            [{"secondary_y": False}],
            [{"secondary_y": False}],
            [{"secondary_y": False}],
            [{"secondary_y": False}],
        ],
    )

    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
            increasing_line_color="#00ff41",  # Neon Green
            decreasing_line_color="#ff00ff",  # Neon Pink
            increasing_fillcolor="rgba(0, 255, 65, 0.1)",
            decreasing_fillcolor="rgba(255, 0, 255, 0.1)",
        ),
        row=1,
        col=1,
    )

    # Moving Averages
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["ma20"],
            mode="lines",
            name="MA20",
            line=dict(color="#00f3ff", width=1.5),  # Neon Blue
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["ma50"],
            mode="lines",
            name="MA50",
            line=dict(color="#ffff00", width=1.5),  # Yellow
        ),
        row=1,
        col=1,
    )

    # Bollinger Bands
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["bb_upper"],
            mode="lines",
            name="BB Upper",
            line=dict(color="rgba(0, 243, 255, 0.3)", width=1, dash="dash"),
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["bb_lower"],
            mode="lines",
            name="BB Lower",
            line=dict(color="rgba(0, 243, 255, 0.3)", width=1, dash="dash"),
            fill="tonexty",
            fillcolor="rgba(0, 243, 255, 0.05)",
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    # Volume bars
    colors = ["#00ff41" if close > open else "#ff00ff" for close, open in zip(df["close"], df["open"])]

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["volume"],
            name="Volume",
            marker_color=colors,
            marker_opacity=0.5,
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    # RSI
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["rsi"],
            mode="lines",
            name="RSI",
            line=dict(color="#bd00ff", width=2),  # Purple
            showlegend=False,
        ),
        row=3,
        col=1,
    )

    # RSI overbought/oversold levels
    fig.add_hline(y=70, line_dash="dash", line_color="#ff00ff", opacity=0.5, row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#00ff41", opacity=0.5, row=3, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="gray", opacity=0.3, row=3, col=1)

    # MACD
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["macd"],
            mode="lines",
            name="MACD",
            line=dict(color="#00f3ff", width=1.5),
            showlegend=False,
        ),
        row=4,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["macd_signal"],
            mode="lines",
            name="Signal",
            line=dict(color="#ff9900", width=1.5),
            showlegend=False,
        ),
        row=4,
        col=1,
    )

    # MACD histogram
    macd_colors = ["#00ff41" if val > 0 else "#ff00ff" for val in df["macd_hist"]]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["macd_hist"],
            name="MACD Hist",
            marker_color=macd_colors,
            marker_opacity=0.6,
            showlegend=False,
        ),
        row=4,
        col=1,
    )

    # Update layout
    fig.update_layout(
        template="plotly_dark",
        height=800,
        margin=dict(l=50, r=50, t=30, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI", color="#b3b3b3"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )

    # Update axes
    grid_color = "rgba(128, 128, 128, 0.1)"

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor=grid_color)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=grid_color)

    return fig
