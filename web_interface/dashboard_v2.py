"""
MaxFlash Dashboard v2.1 - Mobile-Friendly + Sensitive Signals
Senior-level trading dashboard with TOP 50 coins, responsive design, and improved signal detection.
"""

import logging
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
from datetime import datetime, timezone, timedelta
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import asyncio
import ccxt

from utils.logger_config import setup_logging
from utils.enhanced_signal_generator import EnhancedSignalGenerator

# Import signal validation modules
from trading.signal_direction import SignalDirection
from trading.signal_validator import SignalQualityChecker
from trading.trading_config import get_coin_tier, get_confidence_threshold

logger = setup_logging()

# Initialize signal generator and validator
signal_generator = EnhancedSignalGenerator()
signal_validator = SignalQualityChecker()

# TOP 55 Trading Pairs (synced with bot + hot coins)
TOP_50_PAIRS = [
    # TIER 1 - Mega
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "XRP/USDT", "SOL/USDT",
    # TIER 2 - Large
    "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "MATIC/USDT",
    "SHIB/USDT", "TRX/USDT", "LTC/USDT", "LINK/USDT", "NEAR/USDT",
    "UNI/USDT", "APT/USDT", "SUI/USDT", "BCH/USDT", "ETC/USDT",
    # TIER 3 - Mid + Hot
    "ATOM/USDT", "ALGO/USDT", "FTM/USDT", "AAVE/USDT", "ARB/USDT",
    "OP/USDT", "INJ/USDT", "ICP/USDT", "GALA/USDT", "CHZ/USDT",
    "LDO/USDT", "CRV/USDT", "SNX/USDT", "COMP/USDT", "MKR/USDT",
    "PEPE/USDT", "WIF/USDT", "BONK/USDT", "SAND/USDT", "MANA/USDT",
    "AXS/USDT", "EOS/USDT", "XLM/USDT", "HBAR/USDT", "FIL/USDT",
    # Extra hot coins
    "GUN/USDT", "FLOKI/USDT", "WLD/USDT", "RENDER/USDT", "THETA/USDT",
    "IMX/USDT", "RUNE/USDT", "EGLD/USDT", "FLOW/USDT", "XTZ/USDT",
    "VET/USDT", "GRT/USDT",
]

# Signal thresholds - MORE SENSITIVE
SIGNAL_CONFIG = {
    'rsi_oversold': 40,      # RSI ниже = BUY (было 30)
    'rsi_overbought': 60,    # RSI выше = SELL (было 70)
    'change_buy': -1.5,      # Падение % для BUY (было -5)
    'change_sell': 2.0,      # Рост % для SELL (было 5)
    'ma_diff_pct': 0.15,     # MA разница % (было 0.5)
    'volume_spike': 1.5,     # Объем выше среднего
}

# Supported exchanges
EXCHANGES = {
    'binance': {'name': 'Binance', 'icon': '🟡', 'fee': 0.1},
    'bybit': {'name': 'Bybit', 'icon': '🟠', 'fee': 0.1},
    'okx': {'name': 'OKX', 'icon': '⚪', 'fee': 0.08},
    'kraken': {'name': 'Kraken', 'icon': '🟣', 'fee': 0.16},
}

# Risk management defaults
RISK_CONFIG = {
    'default_risk_pct': 1.0,    # 1% риска на сделку
    'tp1_multiplier': 1.5,      # TP1 = 1.5R
    'tp2_multiplier': 2.5,      # TP2 = 2.5R  
    'tp3_multiplier': 4.0,      # TP3 = 4R
    'default_leverage': 5,      # Плечо по умолчанию
}

# Initialize Dash app with mobile viewport
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG, "/assets/neon.css", "/assets/mobile.css"],
    title="MaxFlash Pro | Trading Terminal",
    update_title=None,
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"},
        {"name": "theme-color", "content": "#0a0a1a"},
        {"name": "apple-mobile-web-app-capable", "content": "yes"},
    ],
)
server = app.server

# Exchange instances (multiple exchanges)
exchanges = {
    'binance': ccxt.binance({'enableRateLimit': True}),
    'bybit': ccxt.bybit({'enableRateLimit': True}),
    'okx': ccxt.okx({'enableRateLimit': True}),
    'kraken': ccxt.kraken({'enableRateLimit': True}),
}
exchange = exchanges['binance']  # Default exchange


def fmt_price(price: float) -> str:
    """Smart price formatting - more decimals for smaller prices."""
    if price is None or price == 0:
        return "$0"
    elif price >= 1000:
        return f"${price:,.0f}"
    elif price >= 100:
        return f"${price:,.1f}"
    elif price >= 1:
        return f"${price:,.2f}"
    elif price >= 0.01:
        return f"${price:.4f}"
    elif price >= 0.0001:
        return f"${price:.6f}"
    else:
        return f"${price:.8f}"  # PEPE, BONK, SHIB etc.


def calculate_full_signal(symbol: str, price: float, signal: str, signal_score: int, 
                          change: float, volume: float, reasons: list, 
                          deposit: float = 1000, risk_pct: float = 1.0,
                          exchange_fee: float = 0.001) -> dict:
    """
    Calculate full trading signal with entry, TP levels, SL, position size.
    exchange_fee: комиссия биржи в долях (0.001 = 0.1%)
    """
    if signal == 'HOLD':
        return None
    
    # ATR approximation based on 24h change
    atr_estimate = price * abs(change) / 100 * 0.5  # Half of daily range
    if atr_estimate < price * 0.005:
        atr_estimate = price * 0.005  # Minimum 0.5% ATR
    
    # Dynamic stop-loss based on confidence
    # Lower confidence = tighter stop-loss to limit risk
    if signal_score < 65:
        max_sl_pct = 0.05  # 5% max SL for weak signals
        atr_mult = 1.0
    elif signal_score < 75:
        max_sl_pct = 0.10  # 10% max SL for medium signals
        atr_mult = 1.25
    else:
        max_sl_pct = 0.15  # 15% max SL for strong signals
        atr_mult = 1.5
    
    if signal == 'BUY':
        entry = price
        sl_from_atr = price - (atr_estimate * atr_mult)
        sl_from_max = price * (1 - max_sl_pct)
        sl = max(sl_from_atr, sl_from_max)  # Use tighter SL
        sl_distance = entry - sl
        
        tp1 = entry + (sl_distance * RISK_CONFIG['tp1_multiplier'])
        tp2 = entry + (sl_distance * RISK_CONFIG['tp2_multiplier'])
        tp3 = entry + (sl_distance * RISK_CONFIG['tp3_multiplier'])
        
    else:  # SELL
        entry = price
        sl_from_atr = price + (atr_estimate * atr_mult)
        sl_from_max = price * (1 + max_sl_pct)
        sl = min(sl_from_atr, sl_from_max)  # Use tighter SL
        sl_distance = sl - entry
        
        tp1 = entry - (sl_distance * RISK_CONFIG['tp1_multiplier'])
        tp2 = entry - (sl_distance * RISK_CONFIG['tp2_multiplier'])
        tp3 = entry - (sl_distance * RISK_CONFIG['tp3_multiplier'])
    
    # Risk/Reward calculation
    risk_reward = RISK_CONFIG['tp2_multiplier']  # Based on TP2
    
    # Расчет TP percent для проверки
    tp2_pct = abs(tp2 - entry) / entry * 100
    
    # Position sizing с учетом confidence (исправлено)
    risk_amount = deposit * (risk_pct / 100)  # Фиксированный риск (например $10 при 1% и $1000 депозита)
    position_size_usd = risk_amount / (abs(entry - sl) / entry)  # Базовый размер
    
    # Корректировка на confidence (для слабых сигналов - меньший размер)
    # confidence_multiplier: 0.5-1.0 в зависимости от signal_score
    confidence_multiplier = max(0.5, min(1.0, signal_score / 100.0))
    position_size_usd = position_size_usd * confidence_multiplier
    
    # 4. Если tp_percent < 3 и confidence > 70 → position_size = "$100"
    if tp2_pct < 3 and signal_score > 70:
        position_size_usd = 100.0  # Фиксированный размер $100
    
    # Максимальный размер позиции (защита)
    position_size_usd = min(position_size_usd, deposit * 0.3)  # Max 30% of deposit
    
    # Quantity (базовый расчет)
    quantity = position_size_usd / entry
    
    # Расчет комиссий
    commission_entry = position_size_usd * exchange_fee
    # Комиссия на выходе (примерно на TP2)
    expected_profit_pct = (tp2 - entry) / entry if signal == 'BUY' else (entry - tp2) / entry
    position_value_exit = position_size_usd * (1 + expected_profit_pct)
    commission_exit = position_value_exit * exchange_fee
    total_commission = commission_entry + commission_exit
    
    return {
        'symbol': symbol,
        'signal': signal,
        'confidence': signal_score,
        'entry': entry,
        'sl': sl,
        'sl_pct': abs(entry - sl) / entry * 100,
        'tp1': tp1,
        'tp1_pct': abs(tp1 - entry) / entry * 100,
        'tp2': tp2,
        'tp2_pct': abs(tp2 - entry) / entry * 100,
        'tp3': tp3,
        'tp3_pct': abs(tp3 - entry) / entry * 100,
        'risk_reward': risk_reward,
        'position_size_usd': position_size_usd,
        'quantity': quantity,
        'change_24h': change,
        'volume': volume,
        'reasons': reasons,
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        # Комиссии
        'exchange_fee_pct': exchange_fee * 100,
        'commission_entry': commission_entry,
        'commission_exit': commission_exit,
        'total_commission': total_commission,
    }


def calculate_rsi(close: pd.Series, period: int = 14) -> float:
    """Calculate RSI for the last candle."""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if len(rsi) > 0 else 50


def calculate_macd(close: pd.Series) -> tuple:
    """Calculate MACD indicator."""
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1]


def get_enhanced_signal(ticker: dict, ohlcv_data: pd.DataFrame = None) -> tuple:
    """
    Enhanced signal generation using EnhancedSignalGenerator.
    Includes validation for better signal quality.
    
    Returns (signal, score, details)
    """
    # Use the new enhanced signal generator
    signal, confidence, reasons = signal_generator.generate_signal(ticker, ohlcv_data)
    
    # Optional: Apply additional validation if needed
    # (SignalDirection and signal_validator logic can be added here if required)
    # For now, we trust the enhanced generator
    return signal, confidence, reasons


def get_market_data():
    """
    OLD implementation - kept for reference, not used anymore.
    """
    """
    Simplified but effective signal generation.
    Focus on core indicators without excessive exclusions.
    
    Returns (signal, score, details)
    """
    change = ticker.get('percentage', 0) or 0
    
    # Initialize
    buy_score = 0
    sell_score = 0
    reasons = []
    
    # === 1. PRICE CHANGE (24h) - Most important for trend ===
    # Падающий рынок = больше SELL сигналов
    if change <= -5:
        sell_score += 30
        reasons.append(f"📉 Падение {change:.1f}%")
    elif change <= -2:
        sell_score += 20
        reasons.append(f"📉 Снижение {change:.1f}%")
    elif change <= -0.5:
        sell_score += 10
    elif change >= 5:
        buy_score += 30
        reasons.append(f"📈 Рост {change:+.1f}%")
    elif change >= 2:
        buy_score += 20
        reasons.append(f"📈 Подъем {change:+.1f}%")
    elif change >= 0.5:
        buy_score += 10
    
    # === 2. OHLCV-based indicators (if data available) ===
    if ohlcv_data is not None and len(ohlcv_data) >= 26:
        close = ohlcv_data['close']
        
        # --- RSI ---
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        rsi_series = 100 - (100 / (1 + rs))
        rsi = rsi_series.iloc[-1]
        rsi_prev = rsi_series.iloc[-2] if len(rsi_series) > 1 else rsi
        rsi_trend = rsi - rsi_prev
        
        # RSI signals
        if rsi < 30:
            buy_score += 25
            reasons.append(f"RSI {rsi:.0f} (перепродано)")
        elif rsi < 40:
            buy_score += 15
            reasons.append(f"RSI {rsi:.0f}↓")
        elif rsi > 70:
            sell_score += 25
            reasons.append(f"RSI {rsi:.0f} (перекуплено)")
        elif rsi > 60:
            sell_score += 15
            reasons.append(f"RSI {rsi:.0f}↑")
        elif rsi < 45 and rsi_trend < 0:
            sell_score += 10
            reasons.append(f"RSI {rsi:.0f}⬇")
        elif rsi > 55 and rsi_trend > 0:
            buy_score += 10
            reasons.append(f"RSI {rsi:.0f}⬆")
        
        # --- MACD (8-17-9) ---
        ema_fast = close.ewm(span=8, adjust=False).mean()
        ema_slow = close.ewm(span=17, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        
        macd = macd_line.iloc[-1]
        macd_prev = macd_line.iloc[-2] if len(macd_line) > 1 else macd
        signal = signal_line.iloc[-1]
        signal_prev = signal_line.iloc[-2] if len(signal_line) > 1 else signal
        
        # MACD crossover
        bullish_cross = macd_prev < signal_prev and macd > signal
        bearish_cross = macd_prev > signal_prev and macd < signal
        
        if bullish_cross:
            buy_score += 25
            reasons.append("MACD пересечение⬆")
        elif bearish_cross:
            sell_score += 25
            reasons.append("MACD пересечение⬇")
        elif macd > signal:
            buy_score += 10
            if "MACD" not in str(reasons):
                reasons.append("MACD+")
        elif macd < signal:
            sell_score += 10
            if "MACD" not in str(reasons):
                reasons.append("MACD-")
        
        # --- Price vs MA ---
        price = close.iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else ma20
        
        if price > ma20 > ma50:
            buy_score += 15
            reasons.append("Тренд⬆")
        elif price < ma20 < ma50:
            sell_score += 15
            reasons.append("Тренд⬇")
        elif price < ma20:
            sell_score += 5
        elif price > ma20:
            buy_score += 5
    else:
        # Simple signal based only on 24h change
        if change <= -3:
            sell_score += 15
        elif change >= 3:
            buy_score += 15
    
    # === 3. CALCULATE CONFIDENCE ===
    max_score = max(buy_score, sell_score)
    
    if max_score >= 60:
        confidence = 85
    elif max_score >= 45:
        confidence = 75
    elif max_score >= 30:
        confidence = 60
    elif max_score >= 20:
        confidence = 50
    else:
        confidence = 40
    
    # === 4. DETERMINE SIGNAL ===
    # Разница должна быть минимум 10 для сигнала
    diff = buy_score - sell_score
    
    if diff >= 20:
        signal = "BUY"
    elif diff <= -20:
        signal = "SELL"
    elif diff >= 10:
        signal = "BUY"
        confidence = min(confidence, 55)
    elif diff <= -10:
        signal = "SELL"
        confidence = min(confidence, 55)
    elif diff > 0:
        signal = "BUY"
        confidence = min(confidence, 45)
    elif diff < 0:
        signal = "SELL"
        confidence = min(confidence, 45)
    else:
        signal = "HOLD"
        confidence = 50
    
    # === 5. USE SignalDirection FOR CORRECT BUY/SELL (RSI-based) ===
    if ohlcv_data is not None and len(ohlcv_data) >= 26:
        # Get RSI and MACD for direction logic
        close = ohlcv_data['close']
        rsi = calculate_rsi(close) if len(close) >= 14 else 50
        macd_line, signal_line, macd_histogram = calculate_macd(close)
        price = close.iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        price_trend = "uptrend" if price > ma20 else "downtrend"
        
        direction, conf_adj, direction_reason = SignalDirection.determine_direction(
            rsi=rsi,
            macd_histogram=macd_histogram,
            macd_line=macd_line,
            signal_line=signal_line,
            price_trend=price_trend,
            confidence=confidence
        )
        
        # Apply direction override
        if direction != "NEUTRAL":
            signal = direction
            confidence = min(100, confidence + conf_adj)
            if direction_reason.split("=")[0].strip() not in str(reasons):
                reasons.insert(0, direction_reason.split("=")[0].strip())
        
        # === 6. VALIDATE SIGNAL FOR CONTRADICTIONS ===
        symbol = ticker.get('symbol', 'UNKNOWN')
        change = ticker.get('percentage', 0) or 0
        volume_ratio = 1.0  # Default
        
        validation = signal_validator.validate_and_fix(
            symbol=symbol,
            signal_direction=signal,
            confidence=confidence,
            rsi=rsi,
            macd_histogram=macd_histogram,
            price_change_24h=change,
            volume_ratio=volume_ratio
        )
        
        # Apply validation
        if validation['was_inverted']:
            signal = validation['final_signal']
            reasons.insert(0, "🔄 Инвертирован")
        
        confidence = validation['final_confidence']
        
        # Add any issues to reasons
        for issue in validation.get('issues', []):
            if len(reasons) < 5:  # Limit reasons
                reasons.append(issue[:20])
    
    if signal == "HOLD":
        return "HOLD", 50, reasons if reasons else ["⏳ Нейтрально"]
    
    return signal, confidence, reasons


def get_market_data():
    """Fetch market data for TOP 50 pairs with enhanced signals."""
    try:
        tickers = exchange.fetch_tickers([p for p in TOP_50_PAIRS])
        data = []
        
        for symbol, ticker in tickers.items():
            if symbol not in TOP_50_PAIRS:
                continue
            
            price = ticker.get('last', 0)
            change = ticker.get('percentage', 0) or 0
            volume = ticker.get('quoteVolume', 0) or 0
            high = ticker.get('high', 0) or 0
            low = ticker.get('low', 0) or 0
            
            # Get OHLCV for better signal calculation
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=50)
                ohlcv_df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            except:
                ohlcv_df = None
            
            # Calculate enhanced signal
            signal, signal_score, reasons = get_enhanced_signal(ticker, ohlcv_df)
            
            data.append({
                'symbol': symbol.replace('/USDT', ''),
                'full_symbol': symbol,
                'price': price,
                'change_24h': change,
                'volume': volume,
                'high': high,
                'low': low,
                'signal': signal,
                'signal_score': signal_score,
                'reasons': reasons,
            })
        
        return pd.DataFrame(data)
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")
        return pd.DataFrame()


def get_ohlcv_data(symbol: str, timeframe: str = '15m', limit: int = 200):
    """Fetch OHLCV data for a symbol."""
    try:
        if not symbol.endswith('/USDT'):
            symbol = f"{symbol}/USDT"
        
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        logger.error(f"Error fetching OHLCV: {e}")
        return pd.DataFrame()


def create_header():
    """Create responsive dashboard header."""
    return dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col(
                    html.H2("⚡ MAXFLASH", className="neon-text-blue mb-0",
                           style={"fontWeight": "bold", "letterSpacing": "2px", "fontSize": "clamp(1rem, 4vw, 1.5rem)"}),
                    width="auto",
                ),
                dbc.Col(
                    html.Div([
                        html.Div([
                            html.Span("●", className="live-indicator"),
                            html.Span("LIVE", className="text-success", style={"fontSize": "0.7rem", "fontWeight": "bold", "marginLeft": "8px"}),
                        ], style={"display": "flex", "alignItems": "center"}),
                    ]),
                    width="auto",
                    className="d-flex align-items-center",
                ),
            ], align="center", className="flex-grow-1"),
            dbc.Row([
                dbc.Col(
                    dbc.Badge("TOP 50", color="success", className="me-1 d-none d-md-inline"),
                    width="auto"
                ),
                dbc.Col(
                    html.Span(id="header-time", className="text-muted", 
                             style={"fontSize": "0.85rem", "fontWeight": "500", "fontFamily": "monospace"}),
                    width="auto",
                    className="d-flex align-items-center"
                ),
                dbc.Col(
                    dbc.Badge("v2.1", color="primary"),
                    width="auto"
                ),
            ], align="center"),
        ], fluid=True, className="px-2"),
        color="dark",
        dark=True,
        className="border-bottom border-secondary mb-2 py-2",
        style={"position": "sticky", "top": "0", "zIndex": "1000"},
    )


def create_stats_cards():
    """Create responsive stats cards."""
    return dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H6("BTC DOM", className="text-muted mb-0", style={"fontSize": "0.7rem"}),
                    html.H4(id="btc-dom", className="neon-text-blue mb-0", style={"fontSize": "clamp(0.9rem, 3vw, 1.3rem)"}),
                ], className="py-2 px-2")
            ], className="bg-dark border-secondary h-100"),
            xs=6, sm=6, md=3, className="mb-2 px-1",
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H6("🟢 BUY", className="text-muted mb-0", style={"fontSize": "0.7rem"}),
                    html.H4(id="buy-count", className="text-success mb-0", style={"fontSize": "clamp(0.9rem, 3vw, 1.3rem)"}),
                ], className="py-2 px-2")
            ], className="bg-dark border-secondary h-100"),
            xs=6, sm=6, md=3, className="mb-2 px-1",
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H6("🔴 SELL", className="text-muted mb-0", style={"fontSize": "0.7rem"}),
                    html.H4(id="sell-count", className="text-danger mb-0", style={"fontSize": "clamp(0.9rem, 3vw, 1.3rem)"}),
                ], className="py-2 px-2")
            ], className="bg-dark border-secondary h-100"),
            xs=6, sm=6, md=3, className="mb-2 px-1",
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H6("🔥 TOP", className="text-muted mb-0", style={"fontSize": "0.7rem"}),
                    html.H4(id="top-mover", className="neon-text-pink mb-0", style={"fontSize": "clamp(0.8rem, 2.5vw, 1.1rem)"}),
                ], className="py-2 px-2")
            ], className="bg-dark border-secondary h-100"),
            xs=6, sm=6, md=3, className="mb-2 px-1",
        ),
    ], className="mb-2 stats-row mx-0")


def create_market_table():
    """Create responsive market table with signal filter buttons."""
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.Span("📊 ТОП 50", style={"fontSize": "clamp(0.9rem, 3vw, 1.1rem)"}),
                ], width="auto"),
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("ALL", id="filter-all", size="sm", color="secondary", outline=True, className="px-2 py-0"),
                        dbc.Button("🟢", id="filter-buy", size="sm", color="success", outline=True, className="px-2 py-0"),
                        dbc.Button("🔴", id="filter-sell", size="sm", color="danger", outline=True, className="px-2 py-0"),
                    ], size="sm"),
                ], width="auto", className="ms-auto"),
                dbc.Col([
                    dbc.Button("🔄", id="refresh-table", size="sm", className="py-0 px-2", color="primary"),
                ], width="auto"),
            ], align="center", className="g-1"),
        ], className="py-2 px-2"),
        dcc.Store(id="signal-filter-store", data="ALL"),
        dbc.CardBody([
            dash_table.DataTable(
                id='market-table',
                columns=[
                    {'name': '#', 'id': 'rank'},
                    {'name': 'Coin', 'id': 'symbol'},
                    {'name': 'Price', 'id': 'price_display'},
                    {'name': '24h', 'id': 'change_24h', 'type': 'numeric', 'format': {'specifier': '+.1f'}},
                    {'name': 'Vol', 'id': 'volume_str'},
                    {'name': 'Signal', 'id': 'signal'},
                ],
                style_table={'overflowX': 'auto'},
                style_cell={
                    'backgroundColor': '#1a1a2e',
                    'color': 'white',
                    'textAlign': 'center',
                    'padding': '8px 4px',
                    'border': '1px solid #333',
                    'fontSize': '0.8rem',
                    'minWidth': '45px',
                },
                style_header={
                    'backgroundColor': '#0f0f1a',
                    'fontWeight': 'bold',
                    'color': '#00f3ff',
                    'border': '1px solid #444',
                    'fontSize': '0.75rem',
                    'padding': '6px 4px',
                },
                style_data_conditional=[
                    {'if': {'filter_query': '{change_24h} > 0'}, 'color': '#00ff88'},
                    {'if': {'filter_query': '{change_24h} < 0'}, 'color': '#ff4466'},
                    {'if': {'filter_query': '{signal} = "BUY"'}, 'backgroundColor': 'rgba(0, 255, 136, 0.15)'},
                    {'if': {'filter_query': '{signal} = "SELL"'}, 'backgroundColor': 'rgba(255, 68, 102, 0.15)'},
                ],
                row_selectable='single',
                selected_rows=[0],
                page_size=12,
                style_as_list_view=True,
            )
        ], className="p-2")
    ], className="mb-2")


def create_chart_section():
    """Create responsive chart section."""
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col(html.Span(id="chart-title", style={"fontSize": "clamp(0.85rem, 2.5vw, 1rem)"}), width=8),
                dbc.Col([
                    dbc.Select(
                        id="timeframe-select",
                        options=[
                            {"label": "5m", "value": "5m"},
                            {"label": "15m", "value": "15m"},
                            {"label": "1h", "value": "1h"},
                            {"label": "4h", "value": "4h"},
                            {"label": "1d", "value": "1d"},
                        ],
                        value="15m",
                        className="form-select-sm",
                        style={"fontSize": "0.75rem", "padding": "2px 4px"}
                    ),
                ], width=4, className="text-end"),
            ], align="center"),
        ], className="py-2 px-2"),
        dbc.CardBody([
            dcc.Graph(id="main-chart", style={"height": "clamp(280px, 40vh, 450px)"}, 
                     config={
                         'displayModeBar': True,
                         'modeBarButtonsToInclude': ['zoom2d', 'pan2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d'],
                         'responsive': True,
                         'displaylogo': False,
                     }),
        ], className="p-1")
    ])


def create_signal_panel():
    """Create signal panel with full trading signal."""
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col(html.Span("🎯 ПОЛНЫЙ СИГНАЛ", className="neon-text-pink", style={"fontSize": "0.85rem"})),
                dbc.Col([
                    dbc.Select(
                        id="exchange-select",
                        options=[
                            {"label": "🟡 Binance", "value": "binance"},
                            {"label": "🟠 Bybit", "value": "bybit"},
                            {"label": "⚪ OKX", "value": "okx"},
                            {"label": "🟣 Kraken", "value": "kraken"},
                        ],
                        value="binance",
                        size="sm",
                        style={"fontSize": "0.7rem", "padding": "2px 4px", "height": "24px"},
                    ),
                ], width="auto"),
            ], align="center", className="g-1"),
        ], className="py-1 px-2"),
        dbc.CardBody(id="signal-panel", className="p-2 signal-panel")
    ], className="h-100")


def create_hot_movers():
    """Create hot movers section."""
    return dbc.Card([
        dbc.CardHeader(html.Span("🔥 ДВИЖЕНИЯ", style={"fontSize": "0.9rem"}), className="py-2 px-2"),
        dbc.CardBody(id="hot-movers", className="p-2 hot-movers")
    ], className="h-100")


# Responsive Layout
app.layout = html.Div([
    create_header(),
    dbc.Container([
        create_stats_cards(),
        dbc.Row([
            # Left column: Table + Hot Movers
            dbc.Col([
                create_market_table(),
                create_hot_movers(),  # Переместили под таблицу
            ], xs=12, lg=5, className="mb-2"),
            # Right column: Chart + Full Signal Panel (расширенный)
            dbc.Col([
                create_chart_section(),
                create_signal_panel(),  # Теперь на всю ширину справа
            ], xs=12, lg=7),
        ], className="main-content"),
    ], fluid=True, className="px-2"),
    
    dcc.Interval(id="interval-fast", interval=10*1000, n_intervals=0),  # 10s - обновление сигнала и цены
    dcc.Interval(id="interval-slow", interval=20*1000, n_intervals=0),  # 20s - обновление таблицы TOP 50
    dcc.Interval(id="interval-time", interval=1*1000, n_intervals=0),  # 1s - обновление времени в реальном времени
    dcc.Store(id="market-data-store"),
], className="pb-4")


# ==================== CALLBACKS ====================

# Signal filter callback
@app.callback(
    Output("signal-filter-store", "data"),
    [
        Input("filter-all", "n_clicks"),
        Input("filter-buy", "n_clicks"),
        Input("filter-sell", "n_clicks"),
    ],
    prevent_initial_call=True,
)
def update_signal_filter(all_clicks, buy_clicks, sell_clicks):
    """Update signal filter based on button clicks."""
    from dash import ctx
    if not ctx.triggered:
        return "ALL"
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == "filter-buy":
        return "BUY"
    elif button_id == "filter-sell":
        return "SELL"
    else:
        return "ALL"


@app.callback(
    [
        Output("market-table", "data"),
        Output("market-data-store", "data"),
        Output("buy-count", "children"),
        Output("sell-count", "children"),
        Output("top-mover", "children"),
        Output("btc-dom", "children"),
    ],
    [
        Input("interval-slow", "n_intervals"), 
        Input("refresh-table", "n_clicks"),
        Input("signal-filter-store", "data"),
    ],
)
def update_market_data(n1, n2, signal_filter):
    """Update market table data with enhanced signals and filtering."""
    df = get_market_data()
    
    if df.empty:
        return [], {}, "0", "0", "-", "-"
    
    # Sort by volume
    df = df.sort_values('volume', ascending=False).reset_index(drop=True)
    df['rank'] = range(1, len(df) + 1)
    
    # Format volume
    df['volume_str'] = df['volume'].apply(lambda x: f"${x/1e6:.0f}M" if x > 1e6 else f"${x/1e3:.0f}K")
    
    # Smart price formatting for small coins (BONK, SHIB, PEPE, etc.)
    def format_price(price):
        if price is None or price == 0:
            return "$0"
        elif price >= 1000:
            return f"${price:,.0f}"
        elif price >= 1:
            return f"${price:,.2f}"
        elif price >= 0.01:
            return f"${price:.4f}"
        elif price >= 0.0001:
            return f"${price:.6f}"
        else:
            return f"${price:.8f}"
    
    df['price_display'] = df['price'].apply(format_price)
    
    # Count signals (before filtering)
    buy_count = len(df[df['signal'] == 'BUY'])
    sell_count = len(df[df['signal'] == 'SELL'])
    
    # Top mover
    top_mover_row = df.loc[df['change_24h'].abs().idxmax()]
    top_mover = f"{top_mover_row['symbol']} {top_mover_row['change_24h']:+.1f}%"
    
    # Apply signal filter
    if signal_filter == "BUY":
        df = df[df['signal'] == 'BUY']
    elif signal_filter == "SELL":
        df = df[df['signal'] == 'SELL']
    
    # Re-rank after filtering
    df = df.reset_index(drop=True)
    df['rank'] = range(1, len(df) + 1)
    
    # BTC dominance
    btc_vol = df[df['symbol'] == 'BTC']['volume'].values[0] if 'BTC' in df['symbol'].values else 0
    total_vol = df['volume'].sum()
    btc_dom = f"{(btc_vol/total_vol*100):.1f}%" if total_vol > 0 else "-"
    
    return df.to_dict('records'), df.to_dict('records'), str(buy_count), str(sell_count), top_mover, btc_dom


def get_moscow_time():
    """Get current Moscow time (UTC+3)."""
    # Moscow timezone is UTC+3
    moscow_tz = timezone(timedelta(hours=3))
    return datetime.now(moscow_tz)

@app.callback(
    Output("header-time", "children"),
    Input("interval-time", "n_intervals"),
)
def update_header_time(n):
    """Update header time (next to TOP 50) in Moscow time."""
    moscow_time = get_moscow_time()
    return moscow_time.strftime("%H:%M:%S MSK")


@app.callback(
    [
        Output("main-chart", "figure"),
        Output("chart-title", "children"),
        Output("signal-panel", "children"),
    ],
    [
        Input("market-table", "selected_rows"),
        Input("timeframe-select", "value"),
        Input("exchange-select", "value"),
        Input("interval-fast", "n_intervals"),
    ],
    State("market-data-store", "data"),
)
def update_chart(selected_rows, timeframe, exchange_id, n_fast, market_data):
    """Update main chart and FULL signal panel."""
    if not selected_rows or not market_data:
        return go.Figure(), "Select coin", html.Div("Выберите монету из таблицы", className="text-muted text-center")
    
    try:
        row = market_data[selected_rows[0]]
        symbol = row['full_symbol']
        
        # Загружаем OHLCV данные (кэшируются внутри ccxt)
        df = get_ohlcv_data(symbol, timeframe)
        
        if df.empty:
            return go.Figure(), symbol, html.Div("No data")
        
        # Create candlestick chart
        fig = go.Figure()
        
        # Candlesticks
        fig.add_trace(go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price',
            increasing_line_color='#00ff88',
            decreasing_line_color='#ff4466',
        ))
        
        # MA10 (fast)
        df['ma10'] = df['close'].rolling(10).mean()
        fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['ma10'],
            name='MA10', line=dict(color='#ffff00', width=1),
        ))
        
        # MA20
        df['ma20'] = df['close'].rolling(20).mean()
        fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['ma20'],
            name='MA20', line=dict(color='#00f3ff', width=1),
        ))
        
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=40, r=10, t=20, b=30),
            xaxis_rangeslider_visible=False,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            # Preserve zoom/pan state on updates (changes only when symbol changes)
            uirevision=symbol,
        )
        
        # === CREATE FULL SIGNAL PANEL ===
        signal = row['signal']
        signal_score = row['signal_score']
        change = row['change_24h']
        volume = row['volume']
        reasons = row.get('reasons', [])
        
        # Get exchange info
        ex_info = EXCHANGES.get(exchange_id, EXCHANGES['binance'])
        
        # Получаем реальную цену с выбранной биржи (с защитой от rate limit)
        # Используем цену из таблицы как fallback для быстрой загрузки
        price = row['price']
        try:
            # Пытаемся получить свежую цену, но не блокируем если не получится
            selected_exchange = exchanges.get(exchange_id, exchanges['binance'])
            ticker = selected_exchange.fetch_ticker(symbol)
            price = ticker.get('last', row['price'])  # Реальная цена с выбранной биржи
        except Exception as e:
            # Используем цену из таблицы если не получилось
            logger.debug(f"Используем цену из таблицы для {symbol}: {e}")
            price = row['price']
        
        # Calculate full signal с учетом комиссии биржи
        exchange_fee = ex_info['fee'] / 100  # Комиссия в долях (0.1% = 0.001)
        full_signal = calculate_full_signal(
            symbol=symbol,
            price=price,  # Используем цену с выбранной биржи
            signal=signal,
            signal_score=signal_score,
            change=change,
            volume=volume,
            reasons=reasons,
            deposit=1000,  # Default deposit
            risk_pct=1.0,  # Default 1% risk
            exchange_fee=exchange_fee,  # Комиссия биржи
        )
        
        if signal == 'HOLD' or not full_signal:
            # HOLD signal - waiting
            signal_panel = html.Div([
                html.Div([
                    html.Span("⚪", style={"fontSize": "1.5rem"}),
                    html.Span(" HOLD", className="text-secondary", style={"fontSize": "1.2rem", "fontWeight": "bold"}),
                ], className="text-center mb-2"),
                html.P(fmt_price(price), className="text-center mb-1", style={"fontSize": "1.1rem"}),
                html.P(f"{change:+.2f}%", className=f"text-center text-{'success' if change > 0 else 'danger'}", 
                      style={"fontSize": "0.9rem"}),
                html.Hr(className="my-2"),
                html.P("⏳ Ожидайте сигнала", className="text-muted text-center"),
                html.Small("Рынок в боковике", className="text-muted d-block text-center"),
            ])
        else:
            # Active signal - BUY or SELL
            signal_color = 'success' if signal == 'BUY' else 'danger'
            signal_icon = '🟢' if signal == 'BUY' else '🔴'
            direction = 'LONG' if signal == 'BUY' else 'SHORT'
            
            signal_panel = html.Div([
                # Header with direction
                html.Div([
                    html.Span(signal_icon, style={"fontSize": "1.3rem"}),
                    html.Span(f" {direction}", className=f"text-{signal_color}", 
                             style={"fontSize": "1.1rem", "fontWeight": "bold"}),
                    html.Span(f" {row['symbol']}", style={"fontSize": "0.9rem", "marginLeft": "5px"}),
                ], className="mb-1"),
                
                # Exchange badge
                html.Div([
                    dbc.Badge(f"{ex_info['icon']} {ex_info['name']}", color="dark", className="me-1"),
                    dbc.Badge(f"{signal_score}%", color=signal_color),
                ], className="mb-2"),
                
                # Entry price
                html.Div([
                    html.Small("📍 ВХОД", className="text-muted"),
                    html.Div(fmt_price(full_signal['entry']), style={"fontSize": "1rem", "fontWeight": "bold", "color": "#ffc107"}),
                ], className="mb-2 p-1", style={"backgroundColor": "rgba(255,193,7,0.1)", "borderRadius": "4px"}),
                
                # TP levels
                html.Div([
                    html.Small("🎯 TAKE PROFIT", className="text-muted d-block mb-1"),
                    html.Div([
                        html.Span("TP1: ", className="text-muted", style={"fontSize": "0.75rem"}),
                        html.Span(fmt_price(full_signal['tp1']), className="text-success", style={"fontSize": "0.8rem"}),
                        html.Span(f" (+{full_signal['tp1_pct']:.1f}%)", className="text-muted", style={"fontSize": "0.7rem"}),
                    ]),
                    html.Div([
                        html.Span("TP2: ", className="text-muted", style={"fontSize": "0.75rem"}),
                        html.Span(fmt_price(full_signal['tp2']), className="text-success", style={"fontSize": "0.8rem"}),
                        html.Span(f" (+{full_signal['tp2_pct']:.1f}%)", className="text-muted", style={"fontSize": "0.7rem"}),
                    ]),
                    html.Div([
                        html.Span("TP3: ", className="text-muted", style={"fontSize": "0.75rem"}),
                        html.Span(fmt_price(full_signal['tp3']), className="text-success", style={"fontSize": "0.8rem"}),
                        html.Span(f" (+{full_signal['tp3_pct']:.1f}%)", className="text-muted", style={"fontSize": "0.7rem"}),
                    ]),
                ], className="mb-2"),
                
                # Stop Loss
                html.Div([
                    html.Small("🛑 СТОП-ЛОСС", className="text-muted"),
                    html.Div([
                        html.Span(fmt_price(full_signal['sl']), className="text-danger", style={"fontSize": "0.9rem", "fontWeight": "bold"}),
                        html.Span(f" (-{full_signal['sl_pct']:.1f}%)", className="text-muted", style={"fontSize": "0.75rem"}),
                    ]),
                ], className="mb-2 p-1", style={"backgroundColor": "rgba(255,68,102,0.1)", "borderRadius": "4px"}),
                
                # Position info
                html.Div([
                    html.Div([
                        html.Small("💰 Позиция", className="text-muted d-block"),
                        html.Span(f"${full_signal['position_size_usd']:,.0f}", style={"fontSize": "0.85rem"}),
                    ], className="d-inline-block me-3"),
                    html.Div([
                        html.Small("📊 R:R", className="text-muted d-block"),
                        html.Span(f"1:{full_signal['risk_reward']:.1f}", className="text-info", style={"fontSize": "0.85rem"}),
                    ], className="d-inline-block"),
                ], className="mb-2"),
                
                # Commission info
                html.Div([
                    html.Small("💸 Комиссия биржи", className="text-muted d-block mb-1"),
                    html.Div([
                        html.Span(f"{full_signal.get('exchange_fee_pct', ex_info['fee']):.2f}%", 
                                 className="text-warning", style={"fontSize": "0.75rem"}),
                        html.Span(" | ", className="text-muted", style={"fontSize": "0.7rem"}),
                        html.Span(f"Вход: ${full_signal.get('commission_entry', 0):.2f}", 
                                 className="text-muted", style={"fontSize": "0.7rem"}),
                        html.Span(" | ", className="text-muted", style={"fontSize": "0.7rem"}),
                        html.Span(f"Итого: ${full_signal.get('total_commission', 0):.2f}", 
                                 className="text-muted", style={"fontSize": "0.7rem"}),
                    ]),
                ], className="mb-2 p-1", style={"backgroundColor": "rgba(255,255,255,0.05)", "borderRadius": "4px"}),
                
                # Reasons
                html.Div([
                    dbc.Badge(r, color="dark", className="me-1 mb-1", style={"fontSize": "0.65rem"}) 
                    for r in reasons[:3]
                ] if reasons else [], className="mb-1"),
                
                # Time
                html.Small(f"⏰ {datetime.now().strftime('%H:%M:%S')}", className="text-muted"),
            ])
        
        return fig, f"📈 {row['symbol']} ({timeframe})", signal_panel
        
    except Exception as e:
        logger.error(f"Chart error: {e}")
        return go.Figure(), "Error", html.Div(f"Error: {e}")


@app.callback(
    Output("hot-movers", "children"),
    Input("market-data-store", "data"),
)
def update_hot_movers(market_data):
    """Update hot movers panel."""
    if not market_data:
        return html.Div("Loading...")
    
    df = pd.DataFrame(market_data)
    
    # Sort by absolute change
    df['abs_change'] = df['change_24h'].abs()
    hot = df.nlargest(5, 'abs_change')
    
    items = []
    for _, row in hot.iterrows():
        change = row['change_24h']
        signal = row['signal']
        emoji = "🚀" if change > 3 else "📈" if change > 0 else "📉" if change > -3 else "💥"
        color = "success" if change > 0 else "danger"
        signal_badge = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else ""
        
        items.append(
            html.Div([
                html.Span(f"{emoji} ", style={"fontSize": "1em"}),
                html.Strong(row['symbol'], style={"fontSize": "0.85rem"}),
                html.Span(f" {change:+.1f}%", className=f"text-{color}", style={"fontSize": "0.8rem"}),
                html.Span(f" {signal_badge}", style={"fontSize": "0.7rem"}) if signal_badge else None,
            ], className="mb-1", style={"lineHeight": "1.4"})
        )
    
    return html.Div(items)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
