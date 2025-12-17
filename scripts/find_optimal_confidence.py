"""
Автоматический поиск оптимального порога confidence.

Тестирует разные пороги и выбирает лучший на основе:
- Win Rate > 50%
- Profit Factor > 1.5
- Максимальное количество сделок при соблюдении условий выше
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from ml.lightgbm_model import LightGBMSignalGenerator
from ml.labeling import calculate_atr, evaluate_barrier_outcome
from typing import Dict, List
import json

# Конфигурация
CONFIG = {
    'timeframe': '1h',
    'days_back': 90,  # 3 месяца для быстрого теста
    'tp_atr_mult': 2.5,
    'sl_atr_mult': 1.5,
    'horizon_bars': 4,
    'test_symbols': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ADA/USDT'],
    'confidence_thresholds': [0.40, 0.42, 0.45, 0.48, 0.50, 0.52, 0.55, 0.60],
}

try:
    from utils.universe_selector import get_top_n_pairs
    test_coins = get_top_n_pairs(5)
except:
    test_coins = CONFIG['test_symbols']


def load_data(symbol: str, timeframe: str = '1h', days_back: int = 90):
    """Загрузить данные для тестирования."""
    import ccxt
    from datetime import datetime, timedelta
    
    exchange = ccxt.binance({'enableRateLimit': True})
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days_back)
    since = int(start_time.timestamp() * 1000)
    
    all_ohlcv = []
    while since < int(end_time.timestamp() * 1000):
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        since = ohlcv[-1][0] + 1
    
    if not all_ohlcv:
        return None
    
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    return df


def test_confidence_threshold(
    model: LightGBMSignalGenerator,
    df: pd.DataFrame,
    threshold: float,
    symbol: str
) -> Dict:
    """Тестировать один порог confidence."""
    if len(df) < 500:
        return None
    
    # Получаем предсказания с вероятностями
    try:
        predictions, probs = model.predict_batch_with_probs(df)
    except:
        return None
    
    # Calculate ATR
    atr = calculate_atr(df, period=14)
    
    # Симулируем торговлю
    capital = 10000
    trades = []
    wins = 0
    losses = 0
    skipped = 0
    
    i = 0
    while i < len(predictions) - CONFIG['horizon_bars']:
        pred = predictions[i] if i < len(predictions) else 1
        
        # Получаем confidence
        if i < len(probs):
            sell_prob, hold_prob, buy_prob = probs[i]
            if pred == 2:  # BUY
                confidence = buy_prob
            elif pred == 0:  # SELL
                confidence = sell_prob
            else:
                confidence = hold_prob
        else:
            confidence = 0.5
        
        # Фильтруем по confidence
        if confidence < threshold:
            skipped += 1
            i += 1
            continue
        
        if pred == 1:  # HOLD
            i += 1
            continue
        
        current_price = df.iloc[i]['close']
        current_atr = atr.iloc[i]
        
        if pd.isna(current_atr) or current_atr <= 0:
            i += 1
            continue
        
        is_long = (pred == 2)
        
        if is_long:
            tp_price = current_price + (current_atr * CONFIG['tp_atr_mult'])
            sl_price = current_price - (current_atr * CONFIG['sl_atr_mult'])
        else:
            tp_price = current_price - (current_atr * CONFIG['tp_atr_mult'])
            sl_price = current_price + (current_atr * CONFIG['sl_atr_mult'])
        
        # Оцениваем исход
        future_df = df.iloc[i+1:i+1+CONFIG['horizon_bars']]
        outcome = evaluate_barrier_outcome(
            entry_price=current_price,
            tp_price=tp_price,
            sl_price=sl_price,
            future_ohlcv=future_df,
            is_long=is_long,
        )
        
        pnl_pct = outcome['pnl_percent']
        trades.append({
            'pnl': pnl_pct,
            'outcome': outcome['outcome'],
            'confidence': confidence,
        })
        
        if outcome['outcome'] == 'win':
            wins += 1
        elif outcome['outcome'] == 'lose':
            losses += 1
        
        i += CONFIG['horizon_bars'] + 1
    
    if len(trades) == 0:
        return None
    
    df_trades = pd.DataFrame(trades)
    
    # Вычисляем метрики
    win_rate = wins / len(trades) * 100 if len(trades) > 0 else 0
    
    gross_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
    gross_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999
    
    total_return = df_trades['pnl'].sum()
    avg_confidence = df_trades['confidence'].mean()
    
    return {
        'threshold': threshold,
        'symbol': symbol,
        'total_trades': len(trades),
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_return': total_return,
        'avg_confidence': avg_confidence,
        'skipped': skipped,
    }


def find_optimal_confidence():
    """Найти оптимальный порог confidence."""
    print("=" * 80)
    print("ПОИСК ОПТИМАЛЬНОГО ПОРОГА CONFIDENCE")
    print("=" * 80)
    print()
    
    # Загружаем модель
    model_path = Path(__file__).parent.parent / "models" / "lightgbm_latest.pkl"
    if not model_path.exists():
        print(f"[ERROR] Модель не найдена: {model_path}")
        return None
    
    print(f"[OK] Загружаем модель: {model_path}")
    model = LightGBMSignalGenerator(model_path=str(model_path))
    print()
    
    # Тестируем каждый порог
    all_results = []
    
    for threshold in CONFIG['confidence_thresholds']:
        print(f"\n{'='*80}")
        print(f"Тестируем порог: {threshold:.2f}")
        print(f"{'='*80}")
        
        threshold_results = []
        
        for symbol in test_coins:
            print(f"  {symbol}...", end=" ", flush=True)
            
            df = load_data(symbol, CONFIG['timeframe'], CONFIG['days_back'])
            if df is None or len(df) < 500:
                print("[SKIP]")
                continue
            
            result = test_confidence_threshold(model, df, threshold, symbol)
            if result:
                threshold_results.append(result)
                print(f"[OK] Trades: {result['total_trades']}, WR: {result['win_rate']:.1f}%, PF: {result['profit_factor']:.2f}")
            else:
                print("[SKIP]")
        
        if threshold_results:
            # Агрегируем результаты по порогу
            df_results = pd.DataFrame(threshold_results)
            
            aggregated = {
                'threshold': threshold,
                'total_trades': df_results['total_trades'].sum(),
                'avg_win_rate': df_results['win_rate'].mean(),
                'avg_profit_factor': df_results['profit_factor'].mean(),
                'total_return': df_results['total_return'].sum(),
                'avg_confidence': df_results['avg_confidence'].mean(),
                'total_skipped': df_results['skipped'].sum(),
                'symbols_tested': len(df_results),
            }
            
            all_results.append(aggregated)
            
            print(f"\n  Итого для {threshold:.2f}:")
            print(f"    Trades: {aggregated['total_trades']}")
            print(f"    Win Rate: {aggregated['avg_win_rate']:.1f}%")
            print(f"    Profit Factor: {aggregated['avg_profit_factor']:.2f}")
    
    if not all_results:
        print("\n[ERROR] Нет результатов для анализа")
        return None
    
    # Анализируем результаты
    df_all = pd.DataFrame(all_results)
    
    print(f"\n{'='*80}")
    print("РЕЗУЛЬТАТЫ ПО ПОРОГАМ")
    print(f"{'='*80}\n")
    
    print(f"{'Threshold':<12} {'Trades':<10} {'Win Rate':<12} {'PF':<10} {'Return':<12} {'Skipped':<10}")
    print("-" * 80)
    
    for _, row in df_all.iterrows():
        print(f"{row['threshold']:<12.2f} {row['total_trades']:<10.0f} "
              f"{row['avg_win_rate']:<12.1f} {row['avg_profit_factor']:<10.2f} "
              f"{row['total_return']:<12.2f} {row['total_skipped']:<10.0f}")
    
    # Выбираем оптимальный
    print(f"\n{'='*80}")
    print("ВЫБОР ОПТИМАЛЬНОГО ПОРОГА")
    print(f"{'='*80}\n")
    
    # Критерии: WR > 50%, PF > 1.5, максимум сделок
    candidates = df_all[
        (df_all['avg_win_rate'] >= 50) &
        (df_all['avg_profit_factor'] >= 1.5) &
        (df_all['total_trades'] >= 10)
    ].copy()
    
    if len(candidates) == 0:
        print("[WARNING] Нет порогов, удовлетворяющих критериям (WR>50%, PF>1.5)")
        print("Ищем лучший компромисс...")
        candidates = df_all[df_all['total_trades'] >= 5].copy()
        
        if len(candidates) == 0:
            print("[ERROR] Нет подходящих порогов")
            return None
    
    # Сортируем по комбинированному скору (WR * PF * log(trades))
    candidates['score'] = (
        candidates['avg_win_rate'] / 100 *
        candidates['avg_profit_factor'] *
        np.log1p(candidates['total_trades'])
    )
    
    best = candidates.nlargest(1, 'score').iloc[0]
    
    print(f"Рекомендуемый порог: {best['threshold']:.2f}")
    print(f"  Trades: {best['total_trades']:.0f}")
    print(f"  Win Rate: {best['avg_win_rate']:.1f}%")
    print(f"  Profit Factor: {best['avg_profit_factor']:.2f}")
    print(f"  Total Return: {best['total_return']:.2f}%")
    print(f"  Score: {best['score']:.3f}")
    
    # Сохраняем рекомендацию
    recommendation = {
        'optimal_threshold': float(best['threshold']),
        'metrics': {
            'total_trades': int(best['total_trades']),
            'win_rate': float(best['avg_win_rate']),
            'profit_factor': float(best['avg_profit_factor']),
            'total_return': float(best['total_return']),
        },
        'all_thresholds': df_all.to_dict('records'),
    }
    
    output_path = Path(__file__).parent.parent / "models" / "confidence_recommendation.json"
    with open(output_path, 'w') as f:
        json.dump(recommendation, f, indent=2)
    
    print(f"\n[OK] Рекомендация сохранена: {output_path}")
    
    return recommendation


if __name__ == "__main__":
    find_optimal_confidence()

