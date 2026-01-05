"""
MaxFlash Ecosystem Components v2.0
Dashboard components for the full trading ecosystem.
Fixed: responsive design, proper styling, real data.
"""

import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
import plotly.graph_objects as go
import numpy as np


# ==================== TRADING COMPONENTS ====================

def create_trading_overview_cards():
    """Create overview cards for trading section - CLICKABLE navigation using html.Div with n_clicks."""
    
    card_style = {
        "cursor": "pointer",
        "backgroundColor": "#1e1e1e",
        "border": "1px solid",
        "borderRadius": "8px",
        "padding": "15px",
        "height": "100%",
        "transition": "transform 0.2s, box-shadow 0.2s",
    }
    
    def make_card(card_id, emoji, title, value_id, value, subtitle, border_color, subtitle_id=None):
        """Create a clickable card using html.Div with n_clicks."""
        style = {**card_style, "borderColor": border_color}
        subtitle_elem = html.Small(id=subtitle_id, children=subtitle, className="text-muted") if subtitle_id else html.Small(subtitle, className="text-muted")
        return html.Div([
            html.Div([
                html.Span(emoji, className="fs-1"),
                html.Div([
                    html.H6(title, className="mb-0", style={"color": border_color}),
                    html.H4(id=value_id, children=value, className="mb-0"),
                    subtitle_elem,
                ], className="ms-3"),
            ], className="d-flex align-items-center"),
        ], id=card_id, n_clicks=0, style=style, className="hover-glow")
    
    return dbc.Row([
        # Crypto Card
        dbc.Col([
            make_card("nav-card-crypto", "💰", "КРИПТО", "crypto-signals-count", "0", "сигналов", "#ffc107"),
        ], xs=6, md=4, lg=2, className="mb-3"),
        
        # Forex Card
        dbc.Col([
            make_card("nav-card-forex", "💱", "FOREX", "forex-signals-count", "0", "пар", "#17a2b8"),
        ], xs=6, md=4, lg=2, className="mb-3"),
        
        # Gold Card
        dbc.Col([
            make_card("nav-card-gold", "🥇", "ЗОЛОТО", "gold-price", "$0", "+0%", "#ffc107", "gold-change"),
        ], xs=6, md=4, lg=2, className="mb-3"),
        
        # Oil Card
        dbc.Col([
            make_card("nav-card-oil", "🛢️", "НЕФТЬ", "oil-price", "$0", "+0%", "#28a745", "oil-change"),
        ], xs=6, md=4, lg=2, className="mb-3"),
        
        # Fear & Greed Card
        dbc.Col([
            make_card("nav-card-fear-greed", "😱", "FEAR/GREED", "fear-greed-mini", "50", "Neutral", "#dc3545", "fear-greed-label-mini"),
        ], xs=6, md=4, lg=2, className="mb-3"),
        
        # BTC Dominance Card
        dbc.Col([
            make_card("nav-card-btc-dom", "₿", "BTC DOM", "btc-dominance", "0%", "доминация", "#ffc107"),
        ], xs=6, md=4, lg=2, className="mb-3"),
    ], className="g-2")


# ==================== INVESTMENTS TAB (Completely Redesigned) ====================

def create_investments_tab():
    """Create fully redesigned investments tab with multi-asset support."""
    return html.Div([
        # Header
        dbc.Row([
            dbc.Col([
                html.H4("💎 Инвестиционные портфели", className="text-info mb-3"),
                html.P("Создавайте и отслеживайте диверсифицированные портфели", className="text-muted"),
            ]),
        ], className="mb-4"),

        # Portfolio Builder - Full Width
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("📁 Конструктор портфеля", className="mb-0 text-warning"),
                    ], className="bg-dark"),
                    dbc.CardBody([
                        # Row 1: Type and Capital
                        dbc.Row([
                            dbc.Col([
                                html.Label("Тип портфеля:", className="text-light mb-1"),
                                dbc.Select(
                                    id="portfolio-type",
                                    options=[
                                        {"label": "🔥 Агрессивный (высокий риск/доход)", "value": "aggressive"},
                                        {"label": "⚖️ Сбалансированный (средний риск)", "value": "balanced"},
                                        {"label": "🛡️ Консервативный (низкий риск)", "value": "conservative"},
                                        {"label": "🌍 Глобальный (все классы активов)", "value": "global"},
                                    ],
                                    value="balanced",
                                    className="bg-dark text-light border-secondary",
                                ),
                            ], xs=12, md=6, className="mb-3"),
                            dbc.Col([
                                html.Label("Начальный капитал ($):", className="text-light mb-1"),
                                dbc.Input(
                                    id="portfolio-capital",
                                    type="number",
                                    value=10000,
                                    min=100,
                                    step=100,
                                    className="bg-dark text-light border-secondary",
                                ),
                            ], xs=12, md=6, className="mb-3"),
                        ]),

                        # Row 2: Asset Class Selection
                        html.Label("Классы активов:", className="text-light mb-2"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Checklist(
                                    id="asset-classes",
                                    options=[
                                        {"label": " 💰 Криптовалюты (BTC, ETH, SOL)", "value": "crypto"},
                                        {"label": " 💱 Forex (EUR/USD, GBP/USD)", "value": "forex"},
                                        {"label": " 🥇 Драгметаллы (Золото, Серебро)", "value": "metals"},
                                        {"label": " 🛢️ Сырьё (Нефть, Газ)", "value": "commodities"},
                                        {"label": " 📊 Индексы (S&P500, NASDAQ)", "value": "indices"},
                                    ],
                                    value=["crypto"],
                                    className="text-light",
                                    inline=False,
                                ),
                            ]),
                        ], className="mb-3"),

                        html.Hr(className="border-secondary"),

                        # Allocation Preview
                        html.H6("📊 Предпросмотр распределения:", className="text-light mb-3"),
                        html.Div(id="allocation-preview", children=[
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        html.Span("BTC", className="badge bg-warning me-2"),
                                        html.Span("40%", className="text-light"),
                                    ], className="d-flex justify-content-between mb-2"),
                                    dbc.Progress(value=40, color="warning", className="mb-2", style={"height": "8px"}),
                                ], xs=12, md=6),
                                dbc.Col([
                                    html.Div([
                                        html.Span("ETH", className="badge bg-info me-2"),
                                        html.Span("30%", className="text-light"),
                                    ], className="d-flex justify-content-between mb-2"),
                                    dbc.Progress(value=30, color="info", className="mb-2", style={"height": "8px"}),
                                ], xs=12, md=6),
                            ]),
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        html.Span("SOL", className="badge bg-success me-2"),
                                        html.Span("15%", className="text-light"),
                                    ], className="d-flex justify-content-between mb-2"),
                                    dbc.Progress(value=15, color="success", className="mb-2", style={"height": "8px"}),
                                ], xs=12, md=6),
                                dbc.Col([
                                    html.Div([
                                        html.Span("USDT", className="badge bg-secondary me-2"),
                                        html.Span("15%", className="text-light"),
                                    ], className="d-flex justify-content-between mb-2"),
                                    dbc.Progress(value=15, color="secondary", className="mb-2", style={"height": "8px"}),
                                ], xs=12, md=6),
                            ]),
                        ]),

                        dbc.Button(
                            "🚀 Создать портфель",
                            id="create-portfolio-btn",
                            color="success",
                            className="mt-3 w-100",
                        ),
                    ], className="bg-dark"),
                ], className="bg-dark border-warning mb-4"),
            ]),
        ]),

        # DCA Strategy Card
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("📈 DCA Стратегия (усреднение)", className="mb-0 text-success"),
                    ], className="bg-dark"),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Label("Актив:", className="text-light mb-1"),
                                dbc.Select(
                                    id="dca-asset",
                                    options=[
                                        {"label": "BTC/USDT", "value": "BTC/USDT"},
                                        {"label": "ETH/USDT", "value": "ETH/USDT"},
                                        {"label": "SOL/USDT", "value": "SOL/USDT"},
                                        {"label": "XAU/USD (Золото)", "value": "XAU/USD"},
                                        {"label": "EUR/USD", "value": "EUR/USD"},
                                    ],
                                    value="BTC/USDT",
                                    className="bg-dark text-light border-secondary",
                                ),
                            ], xs=12, md=6, lg=3, className="mb-3"),
                            dbc.Col([
                                html.Label("Сумма ($):", className="text-light mb-1"),
                                dbc.Input(
                                    id="dca-amount",
                                    type="number",
                                    value=100,
                                    min=10,
                                    className="bg-dark text-light border-secondary",
                                ),
                            ], xs=6, md=3, lg=2, className="mb-3"),
                            dbc.Col([
                                html.Label("Частота:", className="text-light mb-1"),
                                dbc.Select(
                                    id="dca-frequency",
                                    options=[
                                        {"label": "Ежедневно", "value": "daily"},
                                        {"label": "Еженедельно", "value": "weekly"},
                                        {"label": "Ежемесячно", "value": "monthly"},
                                    ],
                                    value="weekly",
                                    className="bg-dark text-light border-secondary",
                                ),
                            ], xs=6, md=3, lg=2, className="mb-3"),
                            dbc.Col([
                                html.Label("Buy the dip (%):", className="text-light mb-1"),
                                dbc.Input(
                                    id="dca-dip-pct",
                                    type="number",
                                    value=10,
                                    min=5,
                                    max=50,
                                    className="bg-dark text-light border-secondary",
                                ),
                            ], xs=6, md=3, lg=2, className="mb-3"),
                            dbc.Col([
                                html.Label(" ", className="text-light mb-1 d-block"),
                                dbc.Button(
                                    "▶️ Запустить DCA",
                                    id="start-dca-btn",
                                    color="success",
                                    className="w-100",
                                ),
                            ], xs=6, md=3, lg=3, className="mb-3"),
                        ]),

                        dbc.Alert([
                            html.Strong("💡 DCA-стратегия: "),
                            "Регулярные покупки снижают среднюю цену входа. ",
                            "При падении на указанный % - автоматически удвоит покупку!"
                        ], color="info", className="mb-0 mt-2"),
                    ], className="bg-dark"),
                ], className="bg-dark border-success mb-4"),
            ]),
        ]),

        # Active Portfolios
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("📋 Активные портфели", className="mb-0"),
                    ], className="bg-dark"),
                    dbc.CardBody([
                        html.Div(id="active-portfolios-list", children=[
                            html.P("Нет активных портфелей. Создайте свой первый портфель выше!",
                                   className="text-muted text-center py-4"),
                        ]),
                    ], className="bg-dark"),
                ], className="bg-dark border-secondary"),
            ]),
        ]),
    ], className="p-3")


# ==================== ANALYTICS TAB (Fixed Layout) ====================

def create_analytics_tab():
    """Create analytics tab with proper responsive layout."""
    return html.Div([
        # Header
        dbc.Row([
            dbc.Col([
                html.H4("📊 Аналитика рынка", className="text-success mb-3"),
            ]),
        ]),

        # Fear & Greed - Full Width on Mobile
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("😱 Fear & Greed Index", className="mb-0"),
                    ], className="bg-dark"),
                    dbc.CardBody([
                        dcc.Graph(
                            id="fear-greed-gauge",
                            config={'displayModeBar': False},
                            style={'height': '280px'},
                        ),
                        html.Div(id="fear-greed-info", className="text-center"),
                        dcc.Store(id="fear-greed-data"),
                    ], className="bg-dark"),
                ], className="bg-dark border-danger mb-3"),
            ], xs=12, lg=4),

            # Volume Analysis
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("📊 Анализ объёмов", className="mb-0"),
                    ], className="bg-dark"),
                    dbc.CardBody([
                        html.H6("🔝 Топ по объёму (24ч):", className="text-warning mb-2"),
                        html.Div(id="top-volume-list", style={"maxHeight": "120px", "overflowY": "auto"}),

                        html.Hr(className="border-secondary my-2"),

                        html.H6("⚡ Аномальный объём:", className="text-danger mb-2"),
                        html.Div(id="volume-spikes-list", style={"maxHeight": "100px", "overflowY": "auto"}),
                    ], className="bg-dark", style={"minHeight": "250px"}),
                ], className="bg-dark border-warning mb-3"),
            ], xs=12, lg=4),

            # Market Structure
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("🏛️ Структура рынка", className="mb-0"),
                    ], className="bg-dark"),
                    dbc.CardBody([
                        html.Div([
                            html.Div([
                                html.Span("BTC Dominance:", className="text-muted"),
                                html.Span(id="market-btc-dom", children=" 54.2%", className="text-warning float-end"),
                            ], className="mb-2"),
                            html.Div([
                                html.Span("ETH Dominance:", className="text-muted"),
                                html.Span(id="market-eth-dom", children=" 18.1%", className="text-info float-end"),
                            ], className="mb-2"),
                            html.Div([
                                html.Span("Altseason Index:", className="text-muted"),
                                html.Span(id="market-altseason", children=" 35/100", className="text-danger float-end"),
                            ], className="mb-2"),
                            html.Hr(className="border-secondary"),
                            html.Div([
                                html.Span("Общий тренд:", className="text-muted"),
                                html.Span(id="market-trend", children=" BULLISH", className="text-success float-end"),
                            ], className="mb-2"),
                        ]),
                    ], className="bg-dark", style={"minHeight": "250px"}),
                ], className="bg-dark border-info mb-3"),
            ], xs=12, lg=4),
        ]),

        # Correlation Matrix - Full Width
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.H5("🔗 Корреляция активов", className="mb-0 d-inline"),
                            html.Small(" (30 дней)", className="text-muted ms-2"),
                        ]),
                    ], className="bg-dark"),
                    dbc.CardBody([
                        dcc.Graph(
                            id="correlation-heatmap",
                            config={'displayModeBar': False},
                            style={'height': '350px'},
                        ),
                        html.Small(
                            "Корреляция показывает связь между активами. "
                            "1.0 = движутся одинаково, -1.0 = противоположно, 0 = независимо.",
                            className="text-muted d-block mt-2"
                        ),
                    ], className="bg-dark"),
                ], className="bg-dark border-info"),
            ]),
        ]),
    ], className="p-3")


# ==================== RISK MANAGEMENT TAB ====================

def create_position_calculator():
    """Create position size calculator."""
    return dbc.Card([
        dbc.CardHeader([
            html.H5("🧮 Калькулятор позиции", className="mb-0"),
        ], className="bg-dark"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Депозит ($):", className="text-light mb-1"),
                    dbc.Input(
                        id="calc-deposit",
                        type="number",
                        value=10000,
                        className="bg-dark text-light border-secondary",
                    ),
                ], xs=6, md=4, className="mb-3"),
                dbc.Col([
                    html.Label("Риск (%):", className="text-light mb-1"),
                    dbc.Input(
                        id="calc-risk",
                        type="number",
                        value=1,
                        min=0.1,
                        max=10,
                        step=0.1,
                        className="bg-dark text-light border-secondary",
                    ),
                ], xs=6, md=4, className="mb-3"),
                dbc.Col([
                    html.Label("Плечо:", className="text-light mb-1"),
                    dbc.Select(
                        id="calc-leverage",
                        options=[
                            {"label": "1x (спот)", "value": "1"},
                            {"label": "2x", "value": "2"},
                            {"label": "3x", "value": "3"},
                            {"label": "5x", "value": "5"},
                            {"label": "10x", "value": "10"},
                        ],
                        value="1",
                        className="bg-dark text-light border-secondary",
                    ),
                ], xs=6, md=4, className="mb-3"),
            ]),
            dbc.Row([
                dbc.Col([
                    html.Label("Цена входа ($):", className="text-light mb-1"),
                    dbc.Input(
                        id="calc-entry",
                        type="number",
                        value=100000,
                        className="bg-dark text-light border-secondary",
                    ),
                ], xs=6, className="mb-3"),
                dbc.Col([
                    html.Label("Stop-Loss ($):", className="text-light mb-1"),
                    dbc.Input(
                        id="calc-stoploss",
                        type="number",
                        value=95000,
                        className="bg-dark text-light border-secondary",
                    ),
                ], xs=6, className="mb-3"),
            ]),

            html.Hr(className="border-secondary"),

            # Results
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Small("Размер позиции", className="text-muted"),
                            html.H4(id="calc-position-size", children="$2,000", className="text-warning mb-0"),
                        ], className="text-center py-2"),
                    ], className="bg-dark border-secondary"),
                ], xs=6, md=4, className="mb-2"),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Small("Количество", className="text-muted"),
                            html.H4(id="calc-quantity", children="0.02 BTC", className="text-info mb-0"),
                        ], className="text-center py-2"),
                    ], className="bg-dark border-secondary"),
                ], xs=6, md=4, className="mb-2"),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Small("Макс. убыток", className="text-muted"),
                            html.H4(id="calc-max-loss", children="$100", className="text-danger mb-0"),
                        ], className="text-center py-2"),
                    ], className="bg-dark border-secondary"),
                ], xs=12, md=4, className="mb-2"),
            ]),

            html.Hr(className="border-secondary"),

            # Take Profits
            html.H6("🎯 Уровни Take-Profit:", className="text-light mt-3"),
            dbc.Row([
                dbc.Col([
                    html.Small("TP1 (R:R 1:1)", className="text-muted"),
                    html.Div(id="calc-tp1", children="$105,000", className="text-success"),
                ], xs=4),
                dbc.Col([
                    html.Small("TP2 (R:R 1:2)", className="text-muted"),
                    html.Div(id="calc-tp2", children="$110,000", className="text-success"),
                ], xs=4),
                dbc.Col([
                    html.Small("TP3 (R:R 1:3)", className="text-muted"),
                    html.Div(id="calc-tp3", children="$115,000", className="text-success"),
                ], xs=4),
            ]),
        ], className="bg-dark"),
    ], className="bg-dark border-warning")


def create_risk_dashboard():
    """Create portfolio risk dashboard."""
    return dbc.Card([
        dbc.CardHeader([
            html.H5("⚠️ Риск-метрики", className="mb-0"),
        ], className="bg-dark"),
        dbc.CardBody([
            html.Div([
                html.Div([
                    html.Span("Общий риск:", className="text-muted"),
                    html.Span(" 35%", className="text-warning float-end"),
                ], className="mb-1"),
                dbc.Progress(value=35, color="warning", className="mb-3", style={"height": "6px"}),
            ]),

            html.Div([
                html.Div([
                    html.Span("Корреляционный риск:", className="text-muted"),
                    html.Span(" 60%", className="text-danger float-end"),
                ], className="mb-1"),
                dbc.Progress(value=60, color="danger", className="mb-3", style={"height": "6px"}),
            ]),

            html.Div([
                html.Div([
                    html.Span("Диверсификация:", className="text-muted"),
                    html.Span(" 75%", className="text-success float-end"),
                ], className="mb-1"),
                dbc.Progress(value=75, color="success", className="mb-3", style={"height": "6px"}),
            ]),

            dbc.Alert([
                html.Strong("💡 Совет: "),
                "Добавьте некоррелированные активы (золото, forex) для снижения риска."
            ], color="info", className="mb-0 mt-3 py-2", style={"fontSize": "0.85rem"}),
        ], className="bg-dark"),
    ], className="bg-dark border-danger")


# ==================== EDUCATION TAB (Comprehensive for all asset classes) ====================

def create_education_tab():
    """Create comprehensive education tab with tabs for each asset class."""
    return html.Div([
        # Header
        dbc.Row([
            dbc.Col([
                html.H4("📚 Комплексное обучение", className="text-purple mb-3"),
                html.P("Криптовалюты, Форекс, Инвестиции, Сырьё - всё в одном месте", className="text-muted"),
            ]),
        ], className="mb-3"),

        # Quick Start Steps
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("🚀 Быстрый старт", className="mb-0"),
                    ], className="bg-dark"),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Div([
                                    html.Div("1️⃣", className="fs-5"),
                                    html.Strong("Депозит", style={"fontSize": "0.8rem"}),
                                    html.P("Мин. $500", className="text-muted small mb-0"),
                                ], className="text-center p-1"),
                            ], xs=6, sm=3),
                            dbc.Col([
                                html.Div([
                                    html.Div("2️⃣", className="fs-5"),
                                    html.Strong("Telegram", style={"fontSize": "0.8rem"}),
                                    html.P("Подписка", className="text-muted small mb-0"),
                                ], className="text-center p-1"),
                            ], xs=6, sm=3),
                            dbc.Col([
                                html.Div([
                                    html.Div("3️⃣", className="fs-5"),
                                    html.Strong("Риски", style={"fontSize": "0.8rem"}),
                                    html.P("Изучи гайды", className="text-muted small mb-0"),
                                ], className="text-center p-1"),
                            ], xs=6, sm=3),
                            dbc.Col([
                                html.Div([
                                    html.Div("4️⃣", className="fs-5"),
                                    html.Strong("Торгуй", style={"fontSize": "0.8rem"}),
                                    html.P("1-2% риска", className="text-muted small mb-0"),
                                ], className="text-center p-1"),
                            ], xs=6, sm=3),
                        ]),
                    ], className="bg-dark"),
                ], className="bg-dark border-secondary mb-3"),
            ]),
        ]),

        # Education Tabs by Category
        dbc.Tabs([
            dbc.Tab(label="₿ Крипто", tab_id="edu-crypto", children=[_create_crypto_education()]),
            dbc.Tab(label="💱 Форекс", tab_id="edu-forex", children=[_create_forex_education()]),
            dbc.Tab(label="💼 Инвестиции", tab_id="edu-invest", children=[_create_investment_education()]),
            dbc.Tab(label="🥇 Сырьё", tab_id="edu-commodities", children=[_create_commodities_education()]),
            dbc.Tab(label="🛡️ Риски", tab_id="edu-risk", children=[_create_risk_education()]),
        ], id="education-sub-tabs", active_tab="edu-crypto", className="nav-tabs-ecosystem mb-3"),

        # FAQ Section
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([html.H5("❓ FAQ", className="mb-0")], className="bg-dark"),
                    dbc.CardBody([
                        dbc.Accordion([
                            dbc.AccordionItem("Рекомендуем $500-1000. С меньшей суммой сложно соблюдать риск 1%.", title="Сколько денег нужно?"),
                            dbc.AccordionItem("5-15 по крипте + 5-10 по форексу в день. В боковике меньше.", title="Сколько сигналов в день?"),
                            dbc.AccordionItem("Forex: 24/5, волатильность 5-15%, больше плечо. Крипто: 24/7, волатильность 50-100%.", title="Чем Forex отличается от крипты?"),
                            dbc.AccordionItem("London+NY overlap: 16:00-19:00 MSK. Максимум ликвидности.", title="Когда торговать Forex?"),
                            dbc.AccordionItem("Консервативный: 40% золото, 30% форекс, 20% крипто. Агрессивный: 60% крипто.", title="Как распределить портфель?"),
                            dbc.AccordionItem("Золото - защита от инфляции и кризисов. 10-25% портфеля.", title="Зачем золото в портфеле?"),
                            dbc.AccordionItem("Крипто: до 3x. Forex: до 10x опытным. Высокое плечо = быстрая ликвидация!", title="Какое плечо использовать?"),
                            dbc.AccordionItem("0-25 = страх (покупать). 75-100 = жадность (фиксировать прибыль).", title="Как работает Fear & Greed?"),
                        ], start_collapsed=True, className="accordion-dark"),
                    ], className="bg-dark"),
                ], className="bg-dark border-secondary mt-3"),
            ]),
        ]),
    ], className="p-3")


def _create_crypto_education():
    """Create crypto trading education section."""
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.H5("📖 Криптотрейдинг", className="mb-0")], className="bg-dark"),
                dbc.CardBody([
                    dbc.Accordion([
                        dbc.AccordionItem([
                            html.H6("Что такое криптотрейдинг?", className="text-warning"),
                            html.P("Покупка и продажа криптовалют для прибыли на краткосрочных движениях."),
                            html.H6("Типы торговли:", className="text-info"),
                            html.Ul([
                                html.Li([html.Strong("Scalping"), " - 1-15 минут"]),
                                html.Li([html.Strong("Day trading"), " - внутри дня"]),
                                html.Li([html.Strong("Swing"), " - дни-недели (MaxFlash)"]),
                            ]),
                            html.Div("MaxFlash использует Swing trading на 1h", className="alert alert-info small mb-0 py-1"),
                        ], title="🎯 Основы криптотрейдинга"),
                        dbc.AccordionItem([
                            html.H6("Технический анализ", className="text-warning"),
                            html.Ul([
                                html.Li([html.Strong("Свечи"), " - OHLC за период"]),
                                html.Li([html.Strong("Уровни"), " - поддержка/сопротивление"]),
                                html.Li([html.Strong("RSI"), " - >70 продавать, <30 покупать"]),
                                html.Li([html.Strong("MACD"), " - сила тренда"]),
                                html.Li([html.Strong("ADX"), " - >25 есть тренд"]),
                            ]),
                        ], title="📊 Технический анализ"),
                        dbc.AccordionItem([
                            html.H6("Структура сигнала:", className="text-warning"),
                            html.Pre("🟢 BUY ETH | 78% | RSI:28 MACD:бычий\nTP1:+3% TP2:+7% TP3:+13% | SL:-4%", className="bg-dark border p-2 rounded small"),
                            html.Ul([
                                html.Li([html.Strong("85-100%"), " - отлично"]),
                                html.Li([html.Strong("70-84%"), " - хорошо"]),
                                html.Li([html.Strong("<70%"), " - пропускаем"]),
                            ]),
                        ], title="📡 Как читать сигналы"),
                    ], start_collapsed=True, className="accordion-dark"),
                ], className="bg-dark"),
            ], className="bg-dark border-secondary"),
        ], xs=12, lg=7, className="mb-3"),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.H5("📝 Словарь крипто", className="mb-0")], className="bg-dark"),
                dbc.CardBody([
                    html.Div([
                        html.H6("📊 Индикаторы:", className="text-warning mb-2"),
                        _glossary_item("RSI", ">70 продавать, <30 покупать"),
                        _glossary_item("MACD", "Направление тренда"),
                        _glossary_item("ADX", ">25 есть тренд"),
                        html.H6("💰 Ордера:", className="text-warning mb-2 mt-3"),
                        _glossary_item("Stop-Loss", "Закрытие при убытке"),
                        _glossary_item("Take-Profit", "Фиксация прибыли"),
                        html.H6("⚠️ Термины:", className="text-warning mb-2 mt-3"),
                        _glossary_item("HODL", "Долгосрочное удержание"),
                        _glossary_item("FOMO", "Страх упустить"),
                        _glossary_item("Whale", "Крупный держатель"),
                        _glossary_item("Liquidation", "Принудительное закрытие"),
                    ], style={"maxHeight": "350px", "overflowY": "auto"}),
                ], className="bg-dark"),
            ], className="bg-dark border-secondary"),
        ], xs=12, lg=5, className="mb-3"),
    ], className="g-3 mt-2")


def _create_forex_education():
    """Create forex trading education section."""
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.H5("📖 Торговля Forex", className="mb-0")], className="bg-dark"),
                dbc.CardBody([
                    dbc.Accordion([
                        dbc.AccordionItem([
                            html.H6("Что такое Forex?", className="text-warning"),
                            html.P("Крупнейший рынок мира. Оборот $7 трлн/день."),
                            html.H6("Основы:", className="text-info"),
                            html.Ul([
                                html.Li([html.Strong("Пара"), " - EUR/USD = USD за 1 EUR"]),
                                html.Li([html.Strong("Pip"), " - 0.0001 (4-й знак)"]),
                                html.Li([html.Strong("Lot"), " - 100,000 единиц"]),
                                html.Li("1 lot × 1 pip = $10"),
                            ]),
                            html.H6("Типы пар:", className="text-info mt-2"),
                            html.Ul([
                                html.Li([html.Strong("Majors"), " - EUR/USD, GBP/USD"]),
                                html.Li([html.Strong("Crosses"), " - EUR/GBP"]),
                            ]),
                        ], title="💱 Основы Forex"),
                        dbc.AccordionItem([
                            html.H6("Сессии:", className="text-warning"),
                            html.Div([html.Strong("Азия"), " 02-11 MSK - низкая волатильность"], className="alert alert-secondary py-1 small"),
                            html.Div([html.Strong("Европа"), " 10-19 MSK - высокая"], className="alert alert-info py-1 small"),
                            html.Div([html.Strong("Америка"), " 16-01 MSK - новости USD"], className="alert alert-warning py-1 small"),
                            html.Div([html.Strong("⭐ Overlap"), " 16-19 MSK - ЛУЧШЕЕ ВРЕМЯ"], className="alert alert-success py-1 small"),
                        ], title="🕐 Торговые сессии"),
                        dbc.AccordionItem([
                            html.H6("Ключевые индикаторы:", className="text-warning"),
                            html.Ul([
                                html.Li([html.Strong("Ставки ЦБ"), " - главный драйвер"]),
                                html.Li([html.Strong("NFP"), " - 1-я пятница месяца"]),
                                html.Li([html.Strong("CPI"), " - инфляция"]),
                            ]),
                            html.Div("⚠️ Не торгуй на новостях без опыта!", className="alert alert-danger small py-1 mb-0"),
                        ], title="📰 Фундаментал"),
                    ], start_collapsed=True, className="accordion-dark"),
                ], className="bg-dark"),
            ], className="bg-dark border-secondary"),
        ], xs=12, lg=7, className="mb-3"),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.H5("📝 Словарь Forex", className="mb-0")], className="bg-dark"),
                dbc.CardBody([
                    html.Div([
                        html.H6("💱 Термины:", className="text-warning mb-2"),
                        _glossary_item("Pip", "0.0001 - мин. изменение"),
                        _glossary_item("Lot", "100,000 единиц"),
                        _glossary_item("Spread", "Bid-Ask разница"),
                        _glossary_item("Swap", "Комиссия за перенос"),
                        html.H6("🏛️ Центробанки:", className="text-warning mb-2 mt-3"),
                        _glossary_item("ФРС", "США → USD"),
                        _glossary_item("ЕЦБ", "Европа → EUR"),
                        _glossary_item("BoE", "UK → GBP"),
                        html.H6("📊 Корреляции:", className="text-warning mb-2 mt-3"),
                        _glossary_item("EUR/USD↔GBP/USD", "+0.85"),
                        _glossary_item("EUR/USD↔USD/CHF", "-0.9"),
                    ], style={"maxHeight": "350px", "overflowY": "auto"}),
                ], className="bg-dark"),
            ], className="bg-dark border-secondary"),
        ], xs=12, lg=5, className="mb-3"),
    ], className="g-3 mt-2")


def _create_investment_education():
    """Create investment education section."""
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.H5("📖 Инвестирование", className="mb-0")], className="bg-dark"),
                dbc.CardBody([
                    dbc.Accordion([
                        dbc.AccordionItem([
                            html.H6("Классы активов MaxFlash:", className="text-warning"),
                            html.Ul([
                                html.Li([html.Strong("Крипто"), " - высокий риск/доход"]),
                                html.Li([html.Strong("Forex"), " - средний риск"]),
                                html.Li([html.Strong("Золото"), " - защита"]),
                                html.Li([html.Strong("Нефть"), " - волатильность"]),
                            ]),
                            html.H6("Профили:", className="text-info mt-2"),
                            html.Div("Консервативный: 40% золото, 30% forex, 20% крипто", className="alert alert-success py-1 small"),
                            html.Div("Агрессивный: 60% крипто, 25% forex, 10% золото", className="alert alert-danger py-1 small"),
                        ], title="💼 Построение портфеля"),
                        dbc.AccordionItem([
                            html.H6("DCA для всех активов:", className="text-warning"),
                            html.Ul([
                                html.Li([html.Strong("Крипто"), " - еженедельно"]),
                                html.Li([html.Strong("Forex"), " - частями по тренду"]),
                                html.Li([html.Strong("Золото"), " - ежемесячно"]),
                            ]),
                            html.Div("При падении >15% - удваивай покупку!", className="alert alert-info small py-1 mb-0"),
                        ], title="📈 DCA стратегия"),
                        dbc.AccordionItem([
                            html.H6("Ребалансировка:", className="text-warning"),
                            html.P("Возврат долей к целевым раз в квартал.", className="small"),
                            html.P("Пример: BTC вырос до 70% (цель 50%) → продать часть", className="small"),
                        ], title="⚖️ Ребалансировка"),
                    ], start_collapsed=True, className="accordion-dark"),
                ], className="bg-dark"),
            ], className="bg-dark border-secondary"),
        ], xs=12, lg=7, className="mb-3"),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.H5("📝 Словарь инвестора", className="mb-0")], className="bg-dark"),
                dbc.CardBody([
                    html.Div([
                        html.H6("💼 Портфель:", className="text-warning mb-2"),
                        _glossary_item("Diversification", "Распределение активов"),
                        _glossary_item("Rebalancing", "Возврат к целям"),
                        _glossary_item("ROI", "Возврат инвестиций"),
                        html.H6("🛡️ Защита:", className="text-warning mb-2 mt-3"),
                        _glossary_item("Safe Haven", "Защитный актив"),
                        _glossary_item("Hedge", "Страховка"),
                        _glossary_item("DCA", "Усреднение цены"),
                        html.H6("📊 Метрики:", className="text-warning mb-2 mt-3"),
                        _glossary_item("Volatility", "Колебания цены"),
                        _glossary_item("Compound", "Сложный %"),
                    ], style={"maxHeight": "350px", "overflowY": "auto"}),
                ], className="bg-dark"),
            ], className="bg-dark border-secondary"),
        ], xs=12, lg=5, className="mb-3"),
    ], className="g-3 mt-2")


def _create_commodities_education():
    """Create commodities (gold, oil) education section."""
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.H5("📖 Торговля сырьём", className="mb-0")], className="bg-dark"),
                dbc.CardBody([
                    dbc.Accordion([
                        dbc.AccordionItem([
                            html.H6("Почему золото важно:", className="text-warning"),
                            html.Ul([
                                html.Li("Хедж от инфляции"),
                                html.Li("Safe haven в кризисы"),
                                html.Li("Обратная корреляция с USD"),
                            ]),
                            html.Div("🟢 Растёт: падение USD, снижение ставок, кризисы", className="alert alert-success py-1 small"),
                            html.Div("🔴 Падает: рост USD, повышение ставок", className="alert alert-danger py-1 small"),
                        ], title="🥇 Золото (XAU/USD)"),
                        dbc.AccordionItem([
                            html.H6("Марки нефти:", className="text-warning"),
                            html.Ul([
                                html.Li([html.Strong("WTI"), " - США"]),
                                html.Li([html.Strong("Brent"), " - Европа"]),
                            ]),
                            html.H6("Факторы:", className="text-info"),
                            html.Ul([
                                html.Li("OPEC+ - решения о добыче"),
                                html.Li("Геополитика"),
                                html.Li("Запасы США (еженедельно)"),
                            ]),
                            html.Div("⚠️ Очень волатильна! Риск 1%, плечо до 3x", className="alert alert-warning small py-1 mb-0"),
                        ], title="🛢️ Нефть"),
                        dbc.AccordionItem([
                            html.H6("Корреляции:", className="text-warning"),
                            html.Ul([
                                html.Li("Gold ↔ USD: -0.8 (обратная)"),
                                html.Li("Gold ↔ Silver: +0.9"),
                                html.Li("Oil ↔ USD/CAD: Канада экспортёр"),
                            ]),
                        ], title="🔗 Корреляции"),
                    ], start_collapsed=True, className="accordion-dark"),
                ], className="bg-dark"),
            ], className="bg-dark border-secondary"),
        ], xs=12, lg=7, className="mb-3"),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.H5("📝 Словарь сырья", className="mb-0")], className="bg-dark"),
                dbc.CardBody([
                    html.Div([
                        html.H6("🥇 Золото:", className="text-warning mb-2"),
                        _glossary_item("XAU/USD", "Золото/доллар"),
                        _glossary_item("XAG/USD", "Серебро/доллар"),
                        _glossary_item("Troy Oz", "31.1 грамма"),
                        html.H6("🛢️ Нефть:", className="text-warning mb-2 mt-3"),
                        _glossary_item("WTI", "Американская"),
                        _glossary_item("Brent", "Европейская"),
                        _glossary_item("OPEC+", "Картель"),
                        _glossary_item("Barrel", "159 литров"),
                        html.H6("📊 Индексы:", className="text-warning mb-2 mt-3"),
                        _glossary_item("DXY", "Индекс доллара"),
                        _glossary_item("VIX", "Индекс страха"),
                    ], style={"maxHeight": "350px", "overflowY": "auto"}),
                ], className="bg-dark"),
            ], className="bg-dark border-secondary"),
        ], xs=12, lg=5, className="mb-3"),
    ], className="g-3 mt-2")


def _create_risk_education():
    """Create comprehensive risk management education."""
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.H5("📖 Риск-менеджмент", className="mb-0")], className="bg-dark"),
                dbc.CardBody([
                    dbc.Accordion([
                        dbc.AccordionItem([
                            html.H6("⚠️ САМОЕ ВАЖНОЕ!", className="text-danger"),
                            html.Div([
                                html.Strong("📌 Правило 1%"), " - макс. риск на сделку"
                            ], className="mb-2"),
                            html.Div([
                                html.Strong("📌 Stop-Loss"), " - ОБЯЗАТЕЛЕН всегда"
                            ], className="mb-2"),
                            html.Div([
                                html.Strong("📌 R:R 1:2"), " - прибыль > риска в 2 раза"
                            ], className="mb-2"),
                            html.Div([
                                html.Strong("📌 3 убытка"), " - пауза на день"
                            ]),
                        ], title="🛡️ Золотые правила"),
                        dbc.AccordionItem([
                            html.H6("Риск по активам:", className="text-warning"),
                            dbc.Table([
                                html.Thead(html.Tr([html.Th("Актив"), html.Th("Риск"), html.Th("Плечо")])),
                                html.Tbody([
                                    html.Tr([html.Td("Крипто"), html.Td("1%"), html.Td("3x")]),
                                    html.Tr([html.Td("Forex"), html.Td("1-2%"), html.Td("10x")]),
                                    html.Tr([html.Td("Золото"), html.Td("2-3%"), html.Td("5x")]),
                                    html.Tr([html.Td("Нефть"), html.Td("1%"), html.Td("3x")]),
                                ]),
                            ], bordered=True, color="dark", size="sm"),
                        ], title="📊 Риск по активам"),
                        dbc.AccordionItem([
                            html.H6("Опасные эмоции:", className="text-danger"),
                            html.Ul([
                                html.Li([html.Strong("FOMO"), " - покупки на хаях"]),
                                html.Li([html.Strong("Реванш"), " - отыгрыш после убытка"]),
                                html.Li([html.Strong("Жадность"), " - не закрыть прибыль"]),
                            ]),
                            html.Div("Лечение: план, дисциплина, паузы", className="alert alert-info small py-1 mb-0"),
                        ], title="🧠 Психология"),
                    ], start_collapsed=True, className="accordion-dark"),
                ], className="bg-dark"),
            ], className="bg-dark border-secondary"),
        ], xs=12, lg=7, className="mb-3"),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.H5("✅ Чек-лист", className="mb-0")], className="bg-dark"),
                dbc.CardBody([
                    html.Div([
                        html.H6("Перед сделкой:", className="text-success mb-2"),
                        html.Ul([
                            html.Li("Размер позиции (1-2%)"),
                            html.Li("Stop-Loss выставлен"),
                            html.Li("R:R минимум 1:2"),
                            html.Li("По тренду, не против"),
                        ], className="small"),
                        html.H6("Во время:", className="text-warning mb-2 mt-2"),
                        html.Ul([
                            html.Li("Не двигай SL дальше!"),
                            html.Li("Фиксируй на TP1"),
                        ], className="small"),
                        html.H6("🚫 НИКОГДА:", className="text-danger mb-2 mt-2"),
                        html.Ul([
                            html.Li("Торговать без SL"),
                            html.Li("Рисковать >2%"),
                            html.Li("Усреднять убыток"),
                        ], className="small"),
                    ], style={"maxHeight": "350px", "overflowY": "auto"}),
                ], className="bg-dark"),
            ], className="bg-dark border-secondary"),
        ], xs=12, lg=5, className="mb-3"),
    ], className="g-3 mt-2")


def _glossary_item(term, definition):
    """Helper to create a glossary item."""
    return html.Div([
        html.Strong(term, className="text-info"),
        html.Span(f" - {definition}", className="text-muted", style={"fontSize": "0.85rem"}),
    ], className="mb-2")


# ==================== MAIN TABS ====================

def create_ecosystem_tabs():
    """Create main ecosystem tabs with fixed layout."""
    return dbc.Tabs([
        dbc.Tab(label="🔥 Трейдинг", tab_id="eco-trading", children=[
            html.Div([
                create_trading_overview_cards(),
                dbc.Row([
                    dbc.Col([
                        html.Div(id="eco-trading-content"),
                    ]),
                ], className="mt-3"),
            ], className="p-3"),
        ]),

        dbc.Tab(label="💎 Инвестиции", tab_id="eco-invest", children=[
            create_investments_tab(),
        ]),

        dbc.Tab(label="📊 Аналитика", tab_id="eco-analytics", children=[
            create_analytics_tab(),
        ]),

        dbc.Tab(label="🛡️ Риск", tab_id="eco-risk", children=[
            html.Div([
                dbc.Row([
                    dbc.Col([create_position_calculator()], xs=12, lg=8, className="mb-3"),
                    dbc.Col([create_risk_dashboard()], xs=12, lg=4, className="mb-3"),
                ]),
            ], className="p-3"),
        ]),

        dbc.Tab(label="📚 Обучение", tab_id="eco-education", children=[
            create_education_tab(),
        ]),
    ], id="ecosystem-tabs", active_tab="eco-trading", className="nav-pills")


# ==================== HELPER FUNCTIONS FOR CHARTS ====================

def create_fear_greed_figure(value: int = 50, label: str = "Neutral"):
    """Create Fear & Greed gauge figure with proper sizing."""
    if value <= 25:
        color = "#ff4444"
        label = "Extreme Fear"
    elif value <= 45:
        color = "#ff8800"
        label = "Fear"
    elif value <= 55:
        color = "#ffff00"
        label = "Neutral"
    elif value <= 75:
        color = "#88ff00"
        label = "Greed"
    else:
        color = "#00ff00"
        label = "Extreme Greed"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0.1, 0.9], 'y': [0.15, 0.85]},
        title={'text': label, 'font': {'size': 18, 'color': 'white'}},
        number={'font': {'size': 48, 'color': 'white'}},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': 'white', 'tickwidth': 1},
            'bar': {'color': color, 'thickness': 0.75},
            'bgcolor': 'rgba(0,0,0,0)',
            'borderwidth': 0,
            'steps': [
                {'range': [0, 25], 'color': 'rgba(255,68,68,0.2)'},
                {'range': [25, 45], 'color': 'rgba(255,136,0,0.2)'},
                {'range': [45, 55], 'color': 'rgba(255,255,0,0.2)'},
                {'range': [55, 75], 'color': 'rgba(136,255,0,0.2)'},
                {'range': [75, 100], 'color': 'rgba(0,255,0,0.2)'},
            ],
        }
    ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        margin=dict(l=30, r=30, t=50, b=30),
        height=280,
    )

    return fig


def create_correlation_heatmap_figure(symbols=None, corr_matrix=None):
    """Create correlation heatmap with proper sizing."""
    # Try to get real data
    if symbols is None or corr_matrix is None:
        try:
            from services.market_analytics import get_market_analytics
            analytics = get_market_analytics()
            symbols, corr_matrix = analytics.calculate_correlation_matrix()
        except Exception:
            pass

    # Fallback to sample data
    if symbols is None or len(symbols) == 0:
        symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE']
        corr_matrix = np.array([
            [1.00, 0.85, 0.78, 0.72, 0.68, 0.65, 0.55],
            [0.85, 1.00, 0.82, 0.70, 0.65, 0.68, 0.52],
            [0.78, 0.82, 1.00, 0.65, 0.60, 0.62, 0.48],
            [0.72, 0.70, 0.65, 1.00, 0.70, 0.65, 0.50],
            [0.68, 0.65, 0.60, 0.70, 1.00, 0.72, 0.55],
            [0.65, 0.68, 0.62, 0.65, 0.72, 1.00, 0.58],
            [0.55, 0.52, 0.48, 0.50, 0.55, 0.58, 1.00],
        ])

    # Round for display
    text_matrix = np.round(corr_matrix, 2) if isinstance(corr_matrix, np.ndarray) else corr_matrix

    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix,
        x=symbols,
        y=symbols,
        colorscale=[
            [0, '#ff4444'],
            [0.5, '#333333'],
            [1, '#00ff00'],
        ],
        zmin=-1,
        zmax=1,
        text=text_matrix,
        texttemplate='%{text}',
        textfont={'size': 11, 'color': 'white'},
        hovertemplate='%{x} vs %{y}: %{z:.2f}<extra></extra>',
    ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white', 'size': 12},
        margin=dict(l=60, r=30, t=30, b=60),
        xaxis={'side': 'bottom', 'tickangle': -45},
        yaxis={'autorange': 'reversed'},
        height=350,
    )

    return fig


def get_volume_data_components():
    """Get volume data as Dash components."""
    try:
        from services.market_analytics import get_market_analytics
        analytics = get_market_analytics()

        # Top volume
        top_volume = analytics.get_top_volume(limit=5)
        volume_items = []
        for i, v in enumerate(top_volume, 1):
            vol_str = f"${v.volume_24h / 1e9:.1f}B" if v.volume_24h >= 1e9 else f"${v.volume_24h / 1e6:.0f}M"
            change_color = "text-success" if v.volume_change_pct >= 0 else "text-danger"
            volume_items.append(
                html.Div([
                    html.Span(f"{i}. {v.symbol}", className="text-warning"),
                    html.Span(f" {vol_str}", className="text-muted"),
                    html.Span(f" ({v.volume_change_pct:+.1f}%)", className=f"{change_color} float-end"),
                ], className="mb-1")
            )

        # Volume spikes
        spikes = analytics.get_volume_spikes()
        spike_items = []
        for s in spikes[:5]:
            spike_items.append(
                html.Div([
                    html.Span(s.symbol, className="text-success"),
                    html.Span(f" +{s.volume_change_pct:.0f}%", className="text-success float-end"),
                ], className="mb-1")
            )

        if not spike_items:
            spike_items = [html.Div("Нет аномалий", className="text-muted")]

        if not volume_items:
            volume_items = [html.Div("Загрузка...", className="text-muted")]

        return volume_items, spike_items

    except Exception:
        return (
            [html.Div("Загрузка данных...", className="text-muted")],
            [html.Div("Загрузка данных...", className="text-muted")]
        )


# Legacy compatibility
def create_fear_greed_gauge():
    """Create Fear & Greed gauge card (legacy)."""
    return dbc.Card([
        dbc.CardHeader([
            html.H5("😱 Fear & Greed", className="mb-0"),
        ], className="bg-dark"),
        dbc.CardBody([
            dcc.Graph(
                id="fear-greed-gauge",
                config={'displayModeBar': False},
                style={'height': '280px'},
            ),
            dcc.Store(id="fear-greed-data"),
        ], className="bg-dark"),
    ], className="bg-dark border-danger")


def create_volume_analysis():
    """Create volume analysis card (legacy)."""
    return dbc.Card([
        dbc.CardHeader([
            html.H5("📊 Объёмы", className="mb-0"),
        ], className="bg-dark"),
        dbc.CardBody([
            html.H6("🔝 Топ (24ч):", className="text-warning mb-2"),
            html.Div(id="top-volume-list"),
            html.Hr(className="border-secondary my-2"),
            html.H6("⚡ Аномалии:", className="text-danger mb-2"),
            html.Div(id="volume-spikes-list"),
        ], className="bg-dark"),
    ], className="bg-dark border-warning")


def create_correlation_matrix():
    """Create correlation matrix card (legacy)."""
    return dbc.Card([
        dbc.CardHeader([
            html.H5("🔗 Корреляции", className="mb-0"),
        ], className="bg-dark"),
        dbc.CardBody([
            dcc.Graph(
                id="correlation-heatmap",
                config={'displayModeBar': False},
                style={'height': '350px'},
            ),
        ], className="bg-dark"),
    ], className="bg-dark border-info")


def create_portfolio_builder():
    """Legacy - returns the investments tab section."""
    return create_investments_tab()


def create_dca_strategy_card():
    """Legacy - empty placeholder."""
    return html.Div()


def create_education_section():
    """Legacy - returns education tab."""
    return create_education_tab()


def create_glossary_card():
    """Legacy - empty placeholder."""
    return html.Div()
