"""
Компонент панели торговых сигналов с интеграцией SignalService.
"""

import asyncio
from datetime import datetime
from typing import Optional

import dash_bootstrap_components as dbc
from dash import html


async def get_signal_for_symbol(symbol: str):
    """Get signal analysis for symbol using SignalService."""
    try:
        from trading.signals_service import signal_service

        result = await signal_service.analyze_symbol(symbol)
        return result
    except Exception as e:
        print(f"Error getting signal: {e}")
        return None


def create_signals_panel(symbol: str = "BTC/USDT") -> list:
    """
    Создает панель с активными торговыми сигналами.

    Args:
        symbol: Trading pair to analyze

    Returns:
        List of Dash components
    """
    # Try to get real signal (sync wrapper)
    try:
        signal_result = asyncio.run(get_signal_for_symbol(symbol))
    except Exception as e:
        print(f"Error running signal analysis: {e}")
        signal_result = None

    children = []

    if signal_result:
        # Real signal from SignalService
        signal_type = (
            str(signal_result.signal_type.value)
            if hasattr(signal_result.signal_type, "value")
            else str(signal_result.signal_type)
        )
        confidence = signal_result.confidence * 100

        # Determine color and icon based on signal type
        if signal_type.upper() == "BUY":
            signal_class = "signal-buy"
            text_color = "neon-text-green"  # Custom class or use style
            icon = "🟢"
            title = "LONG ENTRY"
            btn_color = "success"
        elif signal_type.upper() == "SELL":
            signal_class = "signal-sell"
            text_color = "neon-text-pink"
            icon = "🔴"
            title = "SHORT ENTRY"
            btn_color = "danger"
        else:
            signal_class = ""
            text_color = "text-muted"
            icon = "⚪"
            title = "NEUTRAL"
            btn_color = "secondary"

        # Main signal card with Neon styling
        card = dbc.Card(
            [
                dbc.CardBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.H4(
                                            [html.Span(icon, className="me-2"), title],
                                            className=f"mb-0 {text_color}",
                                            style={"textShadow": "0 0 10px rgba(0,0,0,0.5)"},
                                        )
                                    ],
                                    width=8,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Badge(
                                            f"{confidence:.1f}% CONFIDENCE",
                                            color=btn_color,
                                            className="float-end",
                                            style={"fontSize": "0.9rem"},
                                        )
                                    ],
                                    width=4,
                                ),
                            ],
                            className="mb-3 align-items-center",
                        ),
                        # Price Levels Grid
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.Small("ENTRY PRICE", className="text-muted d-block"),
                                        html.Span(f"${signal_result.price:,.2f}", className="h5 text-white"),
                                    ],
                                    width=4,
                                ),
                                dbc.Col(
                                    [
                                        html.Small("STOP LOSS", className="text-muted d-block"),
                                        html.Span(
                                            f"${signal_result.stop_loss:,.2f}" if signal_result.stop_loss else "N/A",
                                            className="h5 text-danger",
                                        ),
                                    ],
                                    width=4,
                                ),
                                dbc.Col(
                                    [
                                        html.Small("TAKE PROFIT", className="text-muted d-block"),
                                        html.Span(
                                            f"${signal_result.take_profit:,.2f}"
                                            if signal_result.take_profit
                                            else "N/A",
                                            className="h5 text-success",
                                        ),
                                    ],
                                    width=4,
                                ),
                            ],
                            className="mb-3 text-center",
                        ),
                        html.Hr(className="border-secondary"),
                        # Analysis Text
                        html.Div(
                            [
                                html.Small("AI ANALYSIS", className="text-muted fw-bold mb-2 d-block"),
                                html.P(
                                    signal_result.reasoning[0]
                                    if signal_result.reasoning
                                    else "No detailed analysis available.",
                                    className="text-light small mb-0",
                                    style={"lineHeight": "1.4"},
                                ),
                            ]
                        ),
                        html.Div(
                            html.Small(
                                f"Generated: {signal_result.timestamp.strftime('%H:%M:%S')}",
                                className="text-muted float-end mt-2",
                            )
                        ),
                    ]
                )
            ],
            className=f"signal-card {signal_class} mb-3",
        )

        children.append(card)
    else:
        # Fallback: No signal available
        children.append(
            dbc.Alert(
                [
                    html.H5("NO ACTIVE SIGNAL", className="alert-heading"),
                    html.P("Market conditions are neutral or data is insufficient for a high-confidence signal."),
                    html.Hr(),
                    html.P("Waiting for new setup...", className="mb-0"),
                ],
                color="dark",
                className="border border-secondary text-muted",
            )
        )

    return children
