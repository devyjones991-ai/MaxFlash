"""
Компонент для отслеживания монет (Watchlist).
Позволяет добавлять монеты в список отслеживания и видеть их цены в реальном времени.
"""

from typing import Any, Optional

import dash_bootstrap_components as dbc
from dash import dcc, html

from utils.market_alerts import MarketAlerts
from utils.market_data_manager import MarketDataManager


def create_watchlist_panel(
    data_manager: Optional[MarketDataManager] = None, alerts: Optional[MarketAlerts] = None
) -> html.Div:
    """
    Создать панель отслеживания монет.

    Args:
        data_manager: Менеджер данных рынка
        alerts: Система алертов

    Returns:
        HTML компонент с панелью отслеживания
    """
    if data_manager is None:
        data_manager = MarketDataManager()
    if alerts is None:
        alerts = MarketAlerts(data_manager)

    return html.Div(
        [
            dbc.Card(
                [
                    dbc.CardHeader(
                        [
                            html.H5("⭐ Отслеживаемые монеты", className="mb-0"),
                            html.Div(
                                [
                                    dbc.InputGroup(
                                        [
                                            dbc.Input(
                                                id="watchlist-symbol-input",
                                                placeholder="Поиск монеты... (BTC, ETH, SOL...)",
                                                type="text",
                                                style={"maxWidth": "180px"},
                                                autoComplete="off",
                                            ),
                                            dbc.Button(
                                                "🔍",
                                                id="watchlist-search-btn",
                                                color="info",
                                                size="sm",
                                                title="Поиск всех монет",
                                            ),
                                            dbc.Button(
                                                "➕",
                                                id="watchlist-add-btn",
                                                color="success",
                                                size="sm",
                                                title="Добавить монету",
                                            ),
                                        ],
                                        size="sm",
                                        className="mt-2",
                                    ),
                                    html.Div(
                                        id="watchlist-suggestions",
                                        className="position-absolute bg-dark border rounded mt-1",
                                        style={
                                            "zIndex": 1000,
                                            "maxHeight": "200px",
                                            "overflowY": "auto",
                                            "display": "none",
                                            "width": "250px",
                                            "maxWidth": "100%",
                                        },
                                    ),
                                ],
                                className="position-relative",
                            ),
                        ]
                    ),
                    dbc.CardBody(
                        [
                            dcc.Store(id="watchlist-store", data={"symbols": ["BTC/USDT", "ETH/USDT"]}),
                            dcc.Store(id="all-pairs-store", data={"pairs": []}),
                            html.Div(id="watchlist-items"),
                            dcc.Interval(
                                id="watchlist-interval",
                                interval=5 * 1000,  # Обновление каждые 5 секунд
                                n_intervals=0,
                            ),
                            # Модальное окно для выбора всех пар
                            dbc.Modal(
                                [
                                    dbc.ModalHeader("🔍 Все доступные монеты"),
                                    dbc.ModalBody(
                                        [
                                            dbc.Input(
                                                id="all-pairs-search",
                                                placeholder="Поиск...",
                                                type="text",
                                                className="mb-3",
                                            ),
                                            html.Div(
                                                id="all-pairs-list", style={"maxHeight": "400px", "overflowY": "auto"}
                                            ),
                                        ]
                                    ),
                                    dbc.ModalFooter(
                                        [dbc.Button("Закрыть", id="close-all-pairs-modal", className="ms-auto")]
                                    ),
                                ],
                                id="all-pairs-modal",
                                is_open=False,
                                size="lg",
                            ),
                        ]
                    ),
                ]
            )
        ]
    )


def create_watchlist_item(symbol: str, ticker: Optional[dict[str, Any]] = None) -> html.Div:
    """
    Создать элемент списка отслеживания.

    Args:
        symbol: Торговая пара
        ticker: Данные тикера

    Returns:
        HTML компонент элемента
    """
    if ticker is None:
        price = 0
        change_24h = 0
        volume_24h = 0
    else:
        price = ticker.get("last", 0)
        change_24h = ticker.get("percentage", 0)
        volume_24h = ticker.get("quoteVolume", 0)

    change_color = "success" if change_24h >= 0 else "danger"
    change_icon = "📈" if change_24h >= 0 else "📉"

    # Форматирование цены в зависимости от размера
    if price >= 1000:
        price_str = f"${price:,.0f}"
    elif price >= 1:
        price_str = f"${price:,.2f}"
    else:
        price_str = f"${price:.4f}"

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Button(
                                        symbol,
                                        id={"type": "watchlist-load", "symbol": symbol},
                                        className="btn btn-link p-0 text-start text-decoration-none fw-bold",
                                        style={
                                            "color": "inherit",
                                            "border": "none",
                                            "background": "none",
                                            "cursor": "pointer",
                                            "font-size": "0.95rem",
                                        },
                                    ),
                                    html.Br(),
                                    html.Small(
                                        f"{change_icon} {change_24h:+.2f}%", className=f"text-{change_color} fw-bold"
                                    ),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    html.Strong(price_str, className="text-primary"),
                                    html.Br(),
                                    html.Small(
                                        f"Vol: ${volume_24h:,.0f}"
                                        if volume_24h >= 1000
                                        else f"Vol: ${volume_24h:,.2f}",
                                        className="text-muted",
                                    ),
                                ],
                                width=5,
                                className="text-end",
                            ),
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "❌",
                                        id={"type": "watchlist-remove", "symbol": symbol},
                                        color="danger",
                                        size="sm",
                                        outline=True,
                                        title="Удалить из отслеживания",
                                    )
                                ],
                                width=1,
                            ),
                        ],
                        align="center",
                    )
                ]
            )
        ],
        className="mb-2 watchlist-item",
        style={"cursor": "pointer", "transition": "all 0.2s"},
    )


def create_watchlist_items(symbols: list[str], data_manager: MarketDataManager) -> html.Div:
    """
    Создать список элементов отслеживания.

    Args:
        symbols: Список символов для отслеживания
        data_manager: Менеджер данных рынка

    Returns:
        HTML компонент со списком
    """
    if not symbols:
        return html.Div([dbc.Alert("Нет отслеживаемых монет. Добавьте монету выше.", color="info")])

    items = []
    # Ограничиваем количество воркеров для производительности
    tickers = data_manager.get_tickers("binance", symbols, max_workers=5)

    for symbol in symbols:
        ticker = tickers.get(symbol)
        items.append(create_watchlist_item(symbol, ticker))

    return html.Div(items)
