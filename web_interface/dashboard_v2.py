"""
MaxFlash Dashboard v4.0 - Professional Trading System
Multi-indicator dashboard with ADX, BB, OBV, RSI Divergence detection.

Version: 4.0.0
Release: 2025-12-19
Signal Engine: v4.0
"""

# Version info
DASHBOARD_VERSION = "4.0.0"
DASHBOARD_RELEASE = "2025-12-19"
SIGNAL_ENGINE_VERSION = "4.0"

import os
import sys
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
import ccxt.async_support as ccxt_async

from utils.logger_config import setup_logging
from utils.signal_generator_v3 import SignalGeneratorV3

# Import signal validation modules
from trading.trading_config import get_coin_tier, get_confidence_threshold

# Forex module import
try:
    from forex.dashboard import (
        create_forex_tab_content,
        create_forex_signal_card,
        create_forex_indicators_card,
        create_forex_chart,
        create_forex_signals_table,
    )
    from forex.signal_generator import get_forex_signal_generator
    from forex.config import FOREX_PAIRS
    HAS_FOREX = True
except ImportError as e:
    HAS_FOREX = False
    print(f"Forex module not available: {e}")

# Ecosystem components import
try:
    from web_interface.ecosystem_components import (
        create_trading_overview_cards,
        create_portfolio_builder,
        create_dca_strategy_card,
        create_fear_greed_gauge,
        create_volume_analysis,
        create_correlation_matrix,
        create_position_calculator,
        create_risk_dashboard,
        create_education_section,
        create_glossary_card,
        create_fear_greed_figure,
        create_correlation_heatmap_figure,
        get_volume_data_components,
    )
    HAS_ECOSYSTEM = True
except ImportError as e:
    HAS_ECOSYSTEM = False
    print(f"Ecosystem components not available: {e}")

logger = setup_logging()

# Initialize signal generator v4.0
signal_generator = SignalGeneratorV3()
logger.info(f"Dashboard v{DASHBOARD_VERSION} initialized with Signal Engine v{SIGNAL_ENGINE_VERSION}")

# TOP 55 Trading Pairs (synced with bot + hot coins)
# TOP 55 Trading Pairs (Cleaned)
TOP_50_PAIRS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "XRP/USDT", "SOL/USDT",
    "ADA/USDT", "DOGE/USDT", "TRX/USDT", "LTC/USDT", "DOT/USDT",
    "AVAX/USDT", "LINK/USDT", "UNI/USDT", "ATOM/USDT",
    "XLM/USDT", "ETC/USDT", "FIL/USDT", "HBAR/USDT", "VET/USDT",
    "APT/USDT", "ARB/USDT", "OP/USDT", "NEAR/USDT",
    "INJ/USDT", "STX/USDT", "IMX/USDT", "GRT/USDT", "ALGO/USDT",
    "FTM/USDT", "SAND/USDT", "MANA/USDT", "THETA/USDT", "AXS/USDT",
    "EGLD/USDT", "AAVE/USDT", "EOS/USDT", "XTZ/USDT", "FLOW/USDT",
    "KAVA/USDT", "GALA/USDT", "MINA/USDT", "CHZ/USDT", "DYDX/USDT",
    "CRV/USDT", "COMP/USDT", "SNX/USDT", "LDO/USDT", "APE/USDT",
    "FET/USDT", "CFX/USDT", "PEPE/USDT", "SUI/USDT"
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
# Using cdnjs.cloudflare.com instead of jsdelivr (which may not resolve on some networks)
BOOTSTRAP_CYBORG_CDN = "https://cdnjs.cloudflare.com/ajax/libs/bootswatch/5.3.2/cyborg/bootstrap.min.css"
app = dash.Dash(
    __name__,
    external_stylesheets=[BOOTSTRAP_CYBORG_CDN, "/assets/neon.css", "/assets/mobile.css"],
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

# ==================== WEBHOOK ENDPOINT ====================
from flask import request, jsonify
import hmac
import hashlib

# Webhook secret for signature verification (set in environment)
WEBHOOK_SECRET = os.environ.get('MAXFLASH_WEBHOOK_SECRET', 'maxflash-default-secret-2024')

# Store for received webhook signals
webhook_signals = []
MAX_WEBHOOK_SIGNALS = 100


@server.route('/api/webhook', methods=['POST'])
def webhook_endpoint():
    """
    Webhook endpoint for external signals (TradingView, etc.)

    Expected JSON format:
    {
        "symbol": "BTC/USDT",
        "action": "BUY" or "SELL",
        "price": 45000.00,
        "confidence": 75,
        "source": "TradingView",
        "message": "RSI oversold + MACD cross"
    }

    Optional signature header: X-Webhook-Signature (HMAC-SHA256)
    """
    try:
        # Verify signature if provided
        signature = request.headers.get('X-Webhook-Signature')
        if signature:
            payload = request.get_data()
            expected = hmac.new(
                WEBHOOK_SECRET.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return jsonify({'error': 'Invalid signature'}), 401

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data'}), 400

        # Validate required fields
        required = ['symbol', 'action']
        for field in required:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}'}), 400

        # Normalize action
        action = data['action'].upper()
        if action not in ['BUY', 'SELL', 'CLOSE']:
            return jsonify({'error': 'Invalid action, must be BUY, SELL, or CLOSE'}), 400

        # Create signal record
        signal_record = {
            'timestamp': datetime.now().isoformat(),
            'symbol': data['symbol'].upper(),
            'action': action,
            'price': data.get('price'),
            'confidence': data.get('confidence', 70),
            'source': data.get('source', 'webhook'),
            'message': data.get('message', ''),
            'processed': False,
        }

        # Store signal
        webhook_signals.append(signal_record)
        if len(webhook_signals) > MAX_WEBHOOK_SIGNALS:
            webhook_signals.pop(0)  # Remove oldest

        logger.info(f"Webhook received: {action} {data['symbol']} from {signal_record['source']}")

        return jsonify({
            'status': 'ok',
            'message': f"Signal received: {action} {data['symbol']}",
            'signal_id': len(webhook_signals) - 1
        }), 200

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': str(e)}), 500


@server.route('/api/webhook/signals', methods=['GET'])
def get_webhook_signals():
    """Get recent webhook signals."""
    limit = request.args.get('limit', 20, type=int)
    return jsonify({
        'signals': webhook_signals[-limit:],
        'total': len(webhook_signals)
    })


@server.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'version': DASHBOARD_VERSION,
        'engine': SIGNAL_ENGINE_VERSION,
        'timestamp': datetime.now().isoformat()
    })


@server.route('/api/export/signals', methods=['GET'])
def export_signals_csv():
    """Export signal history as CSV."""
    from flask import Response
    import io
    import csv

    try:
        # Load performance tracker data
        from trading.performance_tracker import get_performance_tracker
        tracker = get_performance_tracker()

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'timestamp', 'symbol', 'direction', 'entry_price',
            'confidence', 'regime', 'rsi', 'adx', 'method', 'exchange'
        ])

        # Data rows
        for record in tracker.signals:
            writer.writerow([
                record.timestamp,
                record.symbol,
                record.direction,
                record.entry_price,
                record.confidence,
                record.regime,
                record.rsi,
                record.adx,
                record.method,
                record.exchange,
            ])

        output.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=maxflash_signals_{timestamp}.csv'
            }
        )

    except Exception as e:
        logger.error(f"CSV export error: {e}")
        return jsonify({'error': str(e)}), 500


@server.route('/api/export/paper-trades', methods=['GET'])
def export_paper_trades_csv():
    """Export paper trading history as CSV."""
    from flask import Response
    import io
    import csv

    try:
        from trading.paper_trading import get_paper_trader
        trader = get_paper_trader()

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'trade_id', 'symbol', 'side', 'entry_price', 'entry_time',
            'exit_price', 'exit_time', 'pnl_usd', 'pnl_percent',
            'status', 'confidence', 'position_size_usd'
        ])

        # Closed trades
        for trade in trader.closed_trades:
            writer.writerow([
                trade.trade_id,
                trade.symbol,
                trade.side,
                trade.entry_price,
                trade.entry_time,
                trade.exit_price,
                trade.exit_time,
                trade.pnl_usd,
                trade.pnl_percent,
                trade.status,
                trade.confidence,
                trade.position_size_usd,
            ])

        output.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=maxflash_paper_trades_{timestamp}.csv'
            }
        )

    except Exception as e:
        logger.error(f"Paper trades CSV export error: {e}")
        return jsonify({'error': str(e)}), 500


@server.route('/api/stats', methods=['GET'])
def get_stats_api():
    """Get trading statistics as JSON."""
    try:
        from trading.performance_tracker import get_performance_tracker
        from trading.paper_trading import get_paper_trader

        perf = get_performance_tracker()
        paper = get_paper_trader()

        days = request.args.get('days', 30, type=int)
        perf_summary = perf.get_performance_by_confidence(days)

        return jsonify({
            'performance': {
                'total_signals': len(perf.signals),
                'by_confidence': perf_summary,
            },
            'paper_trading': {
                'balance': paper.portfolio.current_balance,
                'total_pnl': paper.portfolio.total_pnl,
                'total_trades': paper.portfolio.total_trades,
                'win_rate': (paper.portfolio.winning_trades / paper.portfolio.total_trades * 100)
                    if paper.portfolio.total_trades > 0 else 0,
                'open_positions': len(paper.open_trades),
            },
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Stats API error: {e}")
        return jsonify({'error': str(e)}), 500


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
    elif price >= 10:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:,.3f}"
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
    
    # FIXED: Correct R:R calculation using formula: Reward / Risk
    # Risk = |Entry - SL|
    # Reward = |TP - Entry|
    risk = abs(entry - sl)
    
    # Calculate R:R for each TP level
    if risk > 0:
        rr_tp1 = abs(tp1 - entry) / risk
        rr_tp2 = abs(tp2 - entry) / risk
        rr_tp3 = abs(tp3 - entry) / risk
    else:
        rr_tp1 = rr_tp2 = rr_tp3 = 0
    
    # Main risk_reward is based on TP3 (full position target)
    risk_reward = rr_tp3
    
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
        'rr_tp1': round(rr_tp1, 2),  # R:R for TP1
        'tp2': tp2,
        'tp2_pct': abs(tp2 - entry) / entry * 100,
        'rr_tp2': round(rr_tp2, 2),  # R:R for TP2
        'tp3': tp3,
        'tp3_pct': abs(tp3 - entry) / entry * 100,
        'rr_tp3': round(rr_tp3, 2),  # R:R for TP3
        'risk_reward': round(risk_reward, 2),  # Main R:R based on TP3
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


# ==================== DATA FETCHING (CACHE READER) ====================

PROJECT_ROOT = Path(__file__).parent.parent
CACHE_FILE_PATH = str(PROJECT_ROOT / "data" / "market_cache.json")
OHLCV_CACHE_PATH = str(PROJECT_ROOT / "data" / "ohlcv_cache.json")
FOREX_CACHE_PATH = str(PROJECT_ROOT / "data" / "forex_cache.json")

def get_market_data():
    """
    Fetch market data by reading the JSON cache file generated by 
    the background service (background_updater.py).
    Falls back to direct API call if cache is missing/stale.
    """
    try:
        # 1. Try to read from cache
        if os.path.exists(CACHE_FILE_PATH):
            try:
                # Check file age
                mtime = os.path.getmtime(CACHE_FILE_PATH)
                if time.time() - mtime < 180:  # Valid for 3 mins
                    with open(CACHE_FILE_PATH, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'data' in data and data['data']:
                            return pd.DataFrame(data['data'])
            except Exception as e:
                logger.error(f"Error reading cache: {e}")
        
        # 2. Fallback: Use MultiSourceDataProvider (NO BINANCE!)
        logger.warning("Cache missing or stale, using MultiSourceDataProvider fallback")
        # Blacklist stablecoins
        blacklist = {'usdt', 'usdc', 'busd', 'dai', 'tusd', 'usdp', 'usdd', 'gusd', 'frax',
                     'usdt0', 'usd1', 'wbtc', 'weth', 'steth', 'fdusd', 'pyusd'}
        try:
            from utils.multi_source_provider import get_data_provider
            provider = get_data_provider()
            overview = provider.get_market_overview()
            crypto_markets = overview.get('crypto_markets', [])

            data = []
            for coin in crypto_markets:
                if len(data) >= 50:
                    break
                symbol = coin.get('symbol', '').upper()
                # Skip stablecoins
                if symbol.lower() in blacklist:
                    continue

                price = coin.get('current_price', 0)
                change = coin.get('price_change_percentage_24h', 0) or 0
                volume = coin.get('total_volume', 0) or 0
                high = coin.get('high_24h', price) or price
                low = coin.get('low_24h', price) or price

                # Quick signal based on change
                if change > 5:
                    signal, signal_score = '🟢 BUY', 70
                elif change < -5:
                    signal, signal_score = '🔴 SELL', 30
                else:
                    signal, signal_score = '⚪ HOLD', 50

                data.append({
                    'symbol': symbol,
                    'full_symbol': f"{symbol}/USDT",
                    'price': price,
                    'change_24h': change,
                    'volume': volume,
                    'high': high,
                    'low': low,
                    'signal': signal,
                    'signal_score': signal_score,
                    'reasons': [f"24h change: {change:.1f}%"],
                })

            if data:
                return pd.DataFrame(data)
        except Exception as fallback_error:
            logger.error(f"MultiSource fallback failed: {fallback_error}")

        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")
        return pd.DataFrame()


def get_quick_signal(ticker: dict) -> tuple:
    """
    Quick signal based on ticker data only - NO OHLCV fetch.
    For fast table updates. Full analysis done on coin click.
    """
    change = ticker.get('percentage', 0) or 0
    price = ticker.get('last', 0)
    high = ticker.get('high', 0) or price
    low = ticker.get('low', 0) or price

    # Simple signal based on 24h change and price position
    buy_score = 0
    sell_score = 0
    reasons = []

    # 1. Price change signal
    if change <= -8:
        buy_score += 40  # Strong dip = potential buy
        reasons.append(f"📉 Сильное падение {change:.1f}%")
    elif change <= -4:
        buy_score += 25
        reasons.append(f"📉 Падение {change:.1f}%")
    elif change <= -1.5:
        buy_score += 10
    elif change >= 8:
        sell_score += 40  # Strong pump = potential sell
        reasons.append(f"📈 Сильный рост {change:+.1f}%")
    elif change >= 4:
        sell_score += 25
        reasons.append(f"📈 Рост {change:+.1f}%")
    elif change >= 1.5:
        sell_score += 10

    # 2. Price position in daily range
    if high > low and price > 0:
        range_pos = (price - low) / (high - low) if (high - low) > 0 else 0.5
        if range_pos < 0.2:  # Near daily low
            buy_score += 20
            reasons.append("💹 У дневного минимума")
        elif range_pos > 0.8:  # Near daily high
            sell_score += 20
            reasons.append("📊 У дневного максимума")

    # 3. Determine signal
    if buy_score >= 40 and buy_score > sell_score + 15:
        signal = "BUY"
        confidence = min(85, 50 + buy_score)
    elif sell_score >= 50 and sell_score > buy_score + 20:  # Stricter for SELL
        signal = "SELL"
        confidence = min(85, 50 + sell_score)
    else:
        signal = "HOLD"
        confidence = 40
        reasons = [f"24h: {change:+.1f}%"] if not reasons else reasons

    return signal, confidence, reasons


def get_ohlcv_data(symbol: str, timeframe: str = '15m', limit: int = 200):
    """Fetch OHLCV data for a symbol using MultiSourceDataProvider (NO BINANCE!)."""
    try:
        if not symbol.endswith('/USDT'):
            symbol = f"{symbol}/USDT"

        # Use MultiSourceDataProvider instead of Binance
        from utils.multi_source_provider import get_data_provider
        provider = get_data_provider()
        df = provider.get_ohlcv(symbol, timeframe, limit)

        if df is not None and not df.empty:
            # Ensure timestamp is a column, not index
            if 'timestamp' not in df.columns:
                df = df.reset_index()
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df

        # Fallback: check OHLCV cache
        if os.path.exists(OHLCV_CACHE_PATH):
            try:
                with open(OHLCV_CACHE_PATH, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    symbol_key = symbol.replace('/', '_')
                    if symbol_key in cache:
                        cached_df = pd.DataFrame(cache[symbol_key])
                        if 'timestamp' not in cached_df.columns and cached_df.index.name == 'timestamp':
                            cached_df = cached_df.reset_index()
                        if 'timestamp' in cached_df.columns:
                            cached_df['timestamp'] = pd.to_datetime(cached_df['timestamp'])
                        return cached_df
            except Exception as cache_error:
                logger.warning(f"OHLCV cache read error: {cache_error}")

        return pd.DataFrame()
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
                    dbc.Button(
                        [html.I(className="fas fa-info-circle"), " ℹ️"],
                        id="info-button",
                        size="sm",
                        color="info",
                        outline=True,
                        className="py-0 px-2",
                        style={"fontSize": "0.75rem"}
                    ),
                    width="auto"
                ),
                dbc.Col(
                    dbc.Badge(f"v{DASHBOARD_VERSION}", color="primary", id="version-badge"),
                    width="auto"
                ),
            ], align="center"),
        ], fluid=True, className="px-2"),
        color="dark",
        dark=True,
        className="border-bottom border-secondary mb-2 py-2",
        style={"position": "sticky", "top": "0", "zIndex": "1000"},
    )


def create_info_modal():
    """Create info modal with dashboard features."""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle([
            "⚡ MaxFlash Dashboard v", DASHBOARD_VERSION
        ]), close_button=True),
        dbc.ModalBody([
            html.H5("🔬 Индикаторы", className="text-info"),
            html.Ul([
                html.Li("RSI-14 (перекупленность/перепроданность)"),
                html.Li("MACD 3-10-16 (Linda Raschke settings)"),
                html.Li("ADX-14 (фильтр силы тренда)"),
                html.Li("Bollinger Bands 20,2 (волатильность)"),
                html.Li("OBV (подтверждение объёмом)"),
                html.Li("ATR-14 (динамический стоп-лосс)"),
                html.Li("RSI Divergence (развороты)"),
            ]),
            html.Hr(),
            html.H5("📈 Режимы рынка", className="text-warning"),
            html.Ul([
                html.Li("STRONG_UPTREND (ADX > 40, +DI > -DI)"),
                html.Li("UPTREND (ADX > 25, +DI > -DI)"),
                html.Li("STRONG_DOWNTREND (ADX > 40, -DI > +DI)"),
                html.Li("DOWNTREND (ADX > 25, -DI > +DI)"),
                html.Li("RANGING (ADX < 25)"),
                html.Li("VOLATILE (высокий объём)"),
            ]),
            html.Hr(),
            html.H5("💰 Риск-менеджмент", className="text-success"),
            html.Ul([
                html.Li("Динамический размер позиции (1-5%)"),
                html.Li("ATR-based стоп-лосс (1.5 ATR)"),
                html.Li("3 уровня тейк-профита (2/3.5/5 ATR)"),
                html.Li("Уменьшение позиции в боковике"),
            ]),
            html.Hr(),
            html.H5("🎯 Логика сигналов", className="text-danger"),
            html.P([
                html.Strong("BUY: "), "RSI < 30 + MACD cross + ADX > 25 + OBV bullish"
            ]),
            html.P([
                html.Strong("SELL: "), "RSI > 70 + MACD cross + ADX > 25 + OBV bearish"
            ]),
            html.P([
                html.Strong("Фильтры: "), "Anti-FOMO (+15%), Anti-knife (-20%)"
            ]),
        ]),
        dbc.ModalFooter([
            html.Div([
                html.Span(f"📅 Релиз: {DASHBOARD_RELEASE}", className="text-muted me-3"),
                html.Span(f"⚙️ Signal Engine: v{SIGNAL_ENGINE_VERSION}", className="text-muted"),
            ]),
        ]),
    ], id="info-modal", size="lg", is_open=False)


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
                    html.H4(id="buy-count", children="...", className="text-success mb-0", style={"fontSize": "clamp(0.9rem, 3vw, 1.3rem)"}),
                ], className="py-2 px-2")
            ], className="bg-dark border-secondary h-100"),
            xs=6, sm=6, md=3, className="mb-2 px-1",
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H6("🔴 SELL", className="text-muted mb-0", style={"fontSize": "0.7rem"}),
                    html.H4(id="sell-count", children="...", className="text-danger mb-0", style={"fontSize": "clamp(0.9rem, 3vw, 1.3rem)"}),
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
                page_action='native',  # Enable native pagination
                page_current=0,        # Start on first page
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


def create_api_info_section():
    """Create API endpoints info section."""
    return dbc.Card([
        dbc.CardHeader([
            html.Span("🔌 API", style={"fontSize": "0.9rem"}),
            html.A(
                "📥 Export CSV",
                href="/api/export/signals",
                className="btn btn-sm btn-outline-success float-end",
                style={"fontSize": "0.7rem"}
            )
        ], className="py-2 px-2"),
        dbc.CardBody([
            html.Div([
                html.Code("/api/webhook", className="text-success me-2"),
                html.Span("POST - External signals", style={"fontSize": "0.75rem"})
            ], className="mb-1"),
            html.Div([
                html.Code("/api/stats", className="text-info me-2"),
                html.Span("GET - Statistics", style={"fontSize": "0.75rem"})
            ], className="mb-1"),
            html.Div([
                html.Code("/api/health", className="text-warning me-2"),
                html.Span("GET - Health check", style={"fontSize": "0.75rem"})
            ]),
        ], className="p-2", style={"fontSize": "0.8rem"})
    ], className="mt-2")


def create_signal_rows():
    """Create BUY and SELL signal rows section for crypto tab."""
    return html.Div([
        # BUY Signals Row
        dbc.Card([
            dbc.CardHeader([
                html.Span("🟢 BUY СИГНАЛЫ", className="text-success", style={"fontWeight": "bold"}),
            ], className="py-1 px-2 bg-dark"),
            dbc.CardBody([
                html.Div(id="buy-signals-row", className="d-flex flex-wrap gap-2", 
                         style={"overflowX": "auto", "whiteSpace": "nowrap"}),
            ], className="p-2 bg-dark", style={"minHeight": "50px"})
        ], className="bg-dark border-success mb-2"),
        
        # SELL Signals Row
        dbc.Card([
            dbc.CardHeader([
                html.Span("🔴 SELL СИГНАЛЫ", className="text-danger", style={"fontWeight": "bold"}),
            ], className="py-1 px-2 bg-dark"),
            dbc.CardBody([
                html.Div(id="sell-signals-row", className="d-flex flex-wrap gap-2",
                         style={"overflowX": "auto", "whiteSpace": "nowrap"}),
            ], className="p-2 bg-dark", style={"minHeight": "50px"})
        ], className="bg-dark border-danger mb-2"),
    ])


# Create Crypto tab content
def create_crypto_tab_content():
    """Create the main crypto trading content."""
    return html.Div([
        create_stats_cards(),
        create_signal_rows(),  # NEW: BUY/SELL signal rows
        dbc.Row([
            # Left column: Table + Hot Movers + API
            dbc.Col([
                create_market_table(),
                create_hot_movers(),
                create_api_info_section(),  # API info section
            ], xs=12, md=5, className="mb-2"),
            # Right column: Chart + Full Signal Panel
            dbc.Col([
                create_chart_section(),
                create_signal_panel(),
            ], xs=12, md=7),
        ], className="main-content"),
    ])


# Create ecosystem tab contents (lazy loading)
def create_invest_tab_content():
    """Create investment tools tab content."""
    if not HAS_ECOSYSTEM:
        return html.Div("Ecosystem components not available", className="text-muted p-3")
    return html.Div([
        create_trading_overview_cards(),
        dbc.Row([
            dbc.Col([create_portfolio_builder()], md=6),
            dbc.Col([create_dca_strategy_card()], md=6),
        ], className="mt-3"),
    ], className="p-2")


def create_analytics_tab_content():
    """Create analytics tab content."""
    if not HAS_ECOSYSTEM:
        return html.Div("Ecosystem components not available", className="text-muted p-3")
    return html.Div([
        dbc.Row([
            dbc.Col([create_fear_greed_gauge()], md=4),
            dbc.Col([create_volume_analysis()], md=4),
            dbc.Col([create_correlation_matrix()], md=4),
        ]),
    ], className="p-2")


def create_risk_tab_content():
    """Create risk management tab content."""
    if not HAS_ECOSYSTEM:
        return html.Div("Ecosystem components not available", className="text-muted p-3")
    return html.Div([
        dbc.Row([
            dbc.Col([create_position_calculator()], md=8),
            dbc.Col([create_risk_dashboard()], md=4),
        ]),
    ], className="p-2")


def create_education_tab_content():
    """Create education tab content."""
    if not HAS_ECOSYSTEM:
        return html.Div("Ecosystem components not available", className="text-muted p-3")
    return html.Div([
        dbc.Row([
            dbc.Col([create_education_section()], md=6),
            dbc.Col([create_glossary_card()], md=6),
        ]),
    ], className="p-2")


# Build tabs list
def build_tabs_list():
    """Build the complete tabs list for the ecosystem."""
    tabs = [
        dbc.Tab(label="💰 Crypto", tab_id="tab-crypto", children=[
            create_crypto_tab_content()
        ]),
    ]

    # Add Forex tab if available
    if HAS_FOREX:
        tabs.append(dbc.Tab(label="💱 Forex", tab_id="tab-forex", children=[
            create_forex_tab_content()
        ]))

    # Add Ecosystem tabs if available
    if HAS_ECOSYSTEM:
        tabs.extend([
            dbc.Tab(label="💎 Инвестиции", tab_id="tab-invest", children=[
                create_invest_tab_content()
            ]),
            dbc.Tab(label="📊 Аналитика", tab_id="tab-analytics", children=[
                create_analytics_tab_content()
            ]),
            dbc.Tab(label="🛡️ Риск", tab_id="tab-risk", children=[
                create_risk_tab_content()
            ]),
            dbc.Tab(label="📚 Обучение", tab_id="tab-education", children=[
                create_education_tab_content()
            ]),
        ])

    return tabs


# Responsive Layout with Tabs
app.layout = html.Div([
    create_header(),
    create_info_modal(),  # Add info modal
    dbc.Container([
        # Full ecosystem tabs
        dbc.Tabs(
            build_tabs_list(),
            id="dashboard-tabs",
            active_tab="tab-crypto",
            className="mb-3 nav-tabs-ecosystem",
        ),
    ], fluid=True, className="px-2"),


    dcc.Interval(id="interval-fast", interval=10*1000, n_intervals=0),  # 10s - signal & price update
    dcc.Interval(id="interval-slow", interval=5*1000, n_intervals=0),  # 5s - table update
    dcc.Interval(id="interval-time", interval=1*1000, n_intervals=0),   # 1s - real-time clock
    dcc.Store(id="market-data-store"),
    dcc.Store(id="fear-greed-store"),  # Store for Fear & Greed data
    dcc.Store(id="clicked-signal-symbol"),  # Store for clicked signal badge
], className="pb-4")


# ==================== CALLBACKS ====================

# Info modal callback
@app.callback(
    Output("info-modal", "is_open"),
    [Input("info-button", "n_clicks")],
    [State("info-modal", "is_open")],
    prevent_initial_call=True,
)
def toggle_info_modal(n_clicks, is_open):
    """Toggle info modal on button click."""
    if n_clicks:
        return not is_open
    return is_open

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
    # REVERTED: Async parallel fetch caused hanging. Back to fast ticker snapshot.
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


# Callback to populate BUY/SELL signal rows with CLICKABLE badges
@app.callback(
    [
        Output("buy-signals-row", "children"),
        Output("sell-signals-row", "children"),
    ],
    Input("market-data-store", "data"),
)
def update_signal_rows(market_data):
    """Populate BUY and SELL signal rows with clickable badges."""
    if not market_data:
        return [html.Span("Загрузка...", className="text-muted")], [html.Span("Загрузка...", className="text-muted")]
    
    buy_signals = []
    sell_signals = []
    
    for idx, row in enumerate(market_data):
        signal = row.get('signal', 'HOLD')
        symbol = row.get('symbol', '?')
        score = row.get('signal_score', 0)
        change = row.get('change_24h', 0)
        
        if signal not in ['BUY', 'SELL']:
            continue
        
        # Create CLICKABLE badge button with data attribute for symbol index
        badge = html.Button([
            html.Span(symbol, style={"fontWeight": "bold", "marginRight": "5px"}),
            html.Span(f"{score}%", className="badge bg-secondary me-1", style={"fontSize": "0.7rem"}),
            html.Span(f"{change:+.1f}%", className=f"{'text-success' if change > 0 else 'text-danger'}", 
                     style={"fontSize": "0.75rem"}),
        ], 
        id={"type": "signal-badge", "index": idx},
        className=f"btn btn-sm {'btn-success' if signal == 'BUY' else 'btn-danger'} text-white px-2 py-1 me-1 mb-1",
        style={"display": "inline-flex", "alignItems": "center", "fontSize": "0.8rem", "borderRadius": "6px", "border": "none"},
        n_clicks=0)
        
        if signal == 'BUY':
            buy_signals.append(badge)
        elif signal == 'SELL':
            sell_signals.append(badge)
    
    # Default messages if no signals - with helpful context
    if not buy_signals:
        buy_signals = [
            html.Span("⏳ Нет BUY сигналов", className="text-muted", style={"fontSize": "0.85rem"}),
            html.Small(" (рынок не перепродан, ждите просадку -4% и более)", className="text-muted ms-2", style={"fontSize": "0.7rem"}),
        ]
    if not sell_signals:
        sell_signals = [
            html.Span("⏳ Нет SELL сигналов", className="text-muted", style={"fontSize": "0.85rem"}),
            html.Small(" (рынок не перекуплен)", className="text-muted ms-2", style={"fontSize": "0.7rem"}),
        ]
    
    return buy_signals, sell_signals


# Pattern matching callback for signal badges - select row in market table
@app.callback(
    Output("market-table", "selected_rows"),
    Input({"type": "signal-badge", "index": dash.ALL}, "n_clicks"),
    State("market-data-store", "data"),
    prevent_initial_call=True,
)
def select_signal_from_badge(n_clicks_list, market_data):
    """Select the clicked signal badge's coin in the market table."""
    from dash import ctx
    
    if not ctx.triggered or not any(n_clicks_list):
        return dash.no_update
    
    # Find which badge was clicked
    triggered = ctx.triggered_id
    if triggered and isinstance(triggered, dict):
        clicked_index = triggered.get("index")
        if clicked_index is not None and market_data:
            # Return the index as selected row
            return [clicked_index]
    
    return dash.no_update


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
        
        # Bollinger Bands (20, 2)
        bb_period = 20
        bb_std = 2
        df['bb_middle'] = df['close'].rolling(bb_period).mean()
        df['bb_std'] = df['close'].rolling(bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * bb_std)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * bb_std)
        
        # BB Upper
        fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['bb_upper'],
            name='BB Upper', line=dict(color='rgba(255,0,255,0.5)', width=1, dash='dot'),
            hoverinfo='skip',
        ))
        
        # BB Lower  
        fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['bb_lower'],
            name='BB Lower', line=dict(color='rgba(255,0,255,0.5)', width=1, dash='dot'),
            fill='tonexty', fillcolor='rgba(255,0,255,0.05)',
            hoverinfo='skip',
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
        # Normalize signal - remove emojis and spaces, uppercase
        signal = signal.strip().upper().replace('🟢', '').replace('🔴', '').replace('⚪', '').strip()
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
        
        # Signal Reasons (Pro)
        reasons_list = []
        for r in reasons:
            if "PosSize" in r:
                continue
            icon = "⚠️" if ("WARNING" in r or "CRITICAL" in r) else "🔹"
            reasons_list.append(html.Div([
                html.Span(f"{icon} ", style={"fontSize": "0.8rem"}),
                html.Span(r, style={"fontSize": "0.75rem", "color": "#ccc"})
            ], className="mb-1"))

        if not reasons_list:
            reasons_list = [html.Small("Технический анализ в норме", className="text-muted")]

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
                html.Hr(className="my-2"),
                html.Div(reasons_list, className="mb-2"),
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
    hot = df.nlargest(10, 'abs_change')
    
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


# ==================== FOREX CALLBACKS ====================
if HAS_FOREX:
    @app.callback(
        [
            Output("forex-signal-card", "children"),
            Output("forex-indicators-card", "children"),
            Output("forex-chart", "figure"),
        ],
        [
            Input("forex-refresh-btn", "n_clicks"),
            Input("forex-interval", "n_intervals"),
            Input("forex-pair-dropdown", "value"),
            Input("forex-timeframe-dropdown", "value"),
        ],
    )
    def update_forex_signal(n_clicks, n_intervals, pair, timeframe):
        """Update Forex signal card, indicators, and chart."""
        try:
            signal_gen = get_forex_signal_generator()
            signal = signal_gen.generate_signal(pair, timeframe)

            if signal:
                signal_card = create_forex_signal_card(signal)
                indicators_card = create_forex_indicators_card(signal)

                # Get chart data
                from forex.data_fetcher import get_forex_data_fetcher
                from forex.analyzer import get_forex_analyzer

                data_fetcher = get_forex_data_fetcher()
                analyzer = get_forex_analyzer()
                df = data_fetcher.get_candles(pair, timeframe, count=100)

                if df is not None:
                    analysis = analyzer.analyze(df, pair, timeframe)
                    if analysis and analysis.df is not None:
                        chart = create_forex_chart(analysis.df, pair, timeframe)
                    else:
                        chart = create_forex_chart(df, pair, timeframe)
                else:
                    chart = create_forex_chart(None, pair, timeframe)

                return signal_card, indicators_card, chart
            else:
                empty_card = html.P("Нет данных", style={"color": "#888"})
                return empty_card, empty_card, create_forex_chart(None, pair, timeframe)

        except Exception as e:
            logger.error(f"Forex update error: {e}", exc_info=True)
            error_msg = html.P(f"Ошибка: {str(e)[:50]}", style={"color": "#ff6666"})
            return error_msg, error_msg, create_forex_chart(None, "", "")

    @app.callback(
        Output("forex-signals-table", "children"),
        [
            Input("forex-scan-all-btn", "n_clicks"),
            Input("forex-interval", "n_intervals"),
        ],
        [State("forex-timeframe-dropdown", "value")],
    )
    def scan_all_forex(n_clicks, n_intervals, timeframe):
        """Scan all forex pairs - auto-load on start and refresh."""
        try:
            signal_gen = get_forex_signal_generator()
            # Get top 5 pairs for quick loading
            top_pairs = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF"]
            signals = signal_gen.generate_all_signals(top_pairs, timeframe or "H1")
            if signals:
                return create_forex_signals_table(signals)
            return html.P("Нет активных сигналов", className="text-muted text-center")
        except Exception as e:
            logger.error(f"Forex scan error: {e}", exc_info=True)
            return html.P("Загрузка сигналов...", className="text-muted text-center")


# ==================== ECOSYSTEM CALLBACKS ====================

if HAS_ECOSYSTEM:
    # Fear & Greed gauge callback
    @app.callback(
        [
            Output("fear-greed-gauge", "figure"),
            Output("fear-greed-store", "data"),
        ],
        Input("interval-slow", "n_intervals"),
    )
    def update_fear_greed_gauge(n):
        """Update Fear & Greed gauge from API."""
        try:
            from utils.fear_greed import get_fear_greed_cached
            data = get_fear_greed_cached()
            if data:
                # FearGreedData is a dataclass, access attributes directly
                value = data.value if hasattr(data, 'value') else 50
                label = data.classification if hasattr(data, 'classification') else 'Neutral'
                fig = create_fear_greed_figure(int(value), label)
                return fig, {"value": value, "classification": label}
        except Exception as e:
            logger.warning(f"Fear & Greed fetch error: {e}")

        # Default neutral gauge
        fig = create_fear_greed_figure(50, "Neutral")
        return fig, {"value": 50, "classification": "Neutral"}

    # Correlation heatmap callback
    @app.callback(
        Output("correlation-heatmap", "figure"),
        Input("interval-slow", "n_intervals"),
    )
    def update_correlation_heatmap(n):
        """Update correlation heatmap."""
        return create_correlation_heatmap_figure()

    # Volume analysis callback
    @app.callback(
        [
            Output("top-volume-list", "children"),
            Output("volume-spikes-list", "children"),
        ],
        Input("interval-slow", "n_intervals"),
    )
    def update_volume_analysis(n):
        """Update volume analysis with real data."""
        try:
            return get_volume_data_components()
        except Exception as e:
            logger.warning(f"Volume analysis error: {e}")
            from dash import html
            return (
                [html.Div("Ошибка загрузки", className="text-danger")],
                [html.Div("Ошибка загрузки", className="text-danger")]
            )

    # Position calculator callback
    @app.callback(
        [
            Output("calc-position-size", "children"),
            Output("calc-quantity", "children"),
            Output("calc-max-loss", "children"),
            Output("calc-tp1", "children"),
            Output("calc-tp2", "children"),
            Output("calc-tp3", "children"),
        ],
        [
            Input("calc-deposit", "value"),
            Input("calc-risk", "value"),
            Input("calc-entry", "value"),
            Input("calc-stoploss", "value"),
            Input("calc-leverage", "value"),
        ],
    )
    def calculate_position(deposit, risk_pct, entry, stoploss, leverage):
        """Calculate position size and TP levels."""
        try:
            deposit = float(deposit or 10000)
            risk_pct = float(risk_pct or 1)
            entry = float(entry or 100000)
            stoploss = float(stoploss or 95000)
            leverage = int(leverage or 1)

            # Calculate risk amount
            risk_amount = deposit * (risk_pct / 100)

            # Calculate stop distance percentage
            stop_distance = abs(entry - stoploss)
            stop_pct = (stop_distance / entry) * 100

            # Calculate position size
            if stop_pct > 0:
                position_size = (risk_amount / (stop_pct / 100)) * leverage
            else:
                position_size = 0

            # Limit to max leverage
            max_position = deposit * leverage
            position_size = min(position_size, max_position)

            # Calculate quantity
            quantity = position_size / entry if entry > 0 else 0

            # Calculate TP levels (based on R multiples)
            r_value = stop_distance
            tp1 = entry + (r_value * 1.5)  # 1.5R
            tp2 = entry + (r_value * 2.5)  # 2.5R
            tp3 = entry + (r_value * 4.0)  # 4R

            return (
                f"${position_size:,.0f}",
                f"{quantity:.6f}",
                f"${risk_amount:,.0f}",
                f" ${tp1:,.0f}",
                f" ${tp2:,.0f}",
                f" ${tp3:,.0f}",
            )

        except Exception as e:
            logger.warning(f"Position calc error: {e}")
            return "$0", "0", "$0", " $0", " $0", " $0"


# ==================== ECOSYSTEM OVERVIEW CARDS ====================

@app.callback(
    [
        Output("crypto-signals-count", "children"),
        Output("forex-signals-count", "children"),
        Output("gold-price", "children"),
        Output("gold-change", "children"),
        Output("gold-change", "className"),
        Output("oil-price", "children"),
        Output("oil-change", "children"),
        Output("oil-change", "className"),
        Output("fear-greed-mini", "children"),
        Output("fear-greed-label-mini", "children"),
        Output("btc-dominance", "children"),
    ],
    [Input("interval-fast", "n_intervals")],
    [State("market-data-store", "data")],
    prevent_initial_call=False,
)
def update_ecosystem_overview(n_intervals, market_data):
    """Update ecosystem overview cards with real data."""
    try:
        # Count crypto signals (from market_data store)
        crypto_count = 0
        if market_data:
            crypto_count = len([s for s in market_data if s.get('signal') in ['BUY', 'SELL']])

        # Count forex pairs
        try:
            from forex.config import FOREX_PAIRS
            forex_count = len(FOREX_PAIRS)
        except ImportError:
            forex_count = 28

        # Get gold price (XAU/USD) via exchange or commodities module
        gold_price = "$2,650"
        gold_change = "+0.5%"
        gold_class = "text-success"
        try:
            from commodities.signal_generator import get_commodity_signal_generator
            gen = get_commodity_signal_generator()
            gold_data = gen.get_price("XAU_USD")
            if gold_data:
                gold_price = f"${gold_data.get('price', 2650):,.0f}"
                change = gold_data.get('change_pct', 0)
                gold_change = f"{change:+.1f}%"
                gold_class = "text-success" if change >= 0 else "text-danger"
        except Exception:
            pass

        # Get oil price (WTI or Brent)
        oil_price = "$72"
        oil_change = "-0.3%"
        oil_class = "text-danger"
        try:
            from commodities.signal_generator import get_commodity_signal_generator
            gen = get_commodity_signal_generator()
            oil_data = gen.get_price("OIL_WTI")
            if oil_data:
                oil_price = f"${oil_data.get('price', 72):,.0f}"
                change = oil_data.get('change_pct', 0)
                oil_change = f"{change:+.1f}%"
                oil_class = "text-success" if change >= 0 else "text-danger"
        except Exception:
            pass

        # Get Fear & Greed Index
        fear_greed = 50
        fear_label = "Neutral"
        try:
            from utils.fear_greed import get_fear_greed_cached
            fg_data = get_fear_greed_cached()
            if fg_data:
                fear_greed = fg_data.get('value', 50)
                fear_label = fg_data.get('classification', 'Neutral')
        except Exception:
            pass

        # Get BTC Dominance
        btc_dom = "58%"
        try:
            # Try to get from CoinGecko or similar
            import requests
            resp = requests.get(
                "https://api.coingecko.com/api/v3/global",
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json().get('data', {})
                dom = data.get('market_cap_percentage', {}).get('btc', 58)
                btc_dom = f"{dom:.1f}%"
        except Exception:
            pass

        return (
            str(crypto_count),
            str(forex_count),
            gold_price,
            gold_change,
            gold_class,
            oil_price,
            oil_change,
            oil_class,
            str(fear_greed),
            fear_label,
            btc_dom,
        )

    except Exception as e:
        logger.warning(f"Ecosystem overview update error: {e}")
        return "0", "28", "$2,650", "+0%", "text-muted", "$72", "+0%", "text-muted", "50", "Neutral", "58%"


# Callback for navigation cards - click to switch tabs
@app.callback(
    Output("dashboard-tabs", "active_tab"),
    [
        Input("nav-card-crypto", "n_clicks"),
        Input("nav-card-forex", "n_clicks"),
        Input("nav-card-gold", "n_clicks"),
        Input("nav-card-oil", "n_clicks"),
        Input("nav-card-fear-greed", "n_clicks"),
        Input("nav-card-btc-dom", "n_clicks"),
    ],
    State("dashboard-tabs", "active_tab"),
    prevent_initial_call=True,
)
def navigate_from_cards(crypto_clicks, forex_clicks, gold_clicks, oil_clicks, fg_clicks, btc_clicks, current_tab):
    """Switch tabs when clicking overview cards in Investments tab."""
    from dash import ctx
    
    if not ctx.triggered:
        return current_tab
    
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Map card IDs to tab IDs
    card_to_tab = {
        "nav-card-crypto": "tab-crypto",
        "nav-card-forex": "tab-forex",
        "nav-card-gold": "tab-analytics",  # Gold → Analytics tab
        "nav-card-oil": "tab-analytics",   # Oil → Analytics tab
        "nav-card-fear-greed": "tab-analytics",  # Fear/Greed → Analytics tab
        "nav-card-btc-dom": "tab-crypto",  # BTC Dominance → Crypto tab
    }
    
    return card_to_tab.get(triggered_id, current_tab)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
