"""
Signal Outcome Tracker

Tracks the outcomes of trading signals after the horizon period.
Used for:
1. Monitoring real-time signal quality
2. Calibrating confidence thresholds
3. Identifying best exchanges per symbol
4. Auto-retrain data collection

Stores signal + outcome data for analysis.
"""

import logging
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class TrackedSignal:
    """A signal being tracked for outcome."""
    id: str
    symbol: str
    exchange: str
    timeframe: str
    signal_type: str  # BUY, SELL
    confidence: float
    entry_price: float
    tp_price: float
    sl_price: float
    entry_time: datetime
    horizon_end: datetime
    outcome: Optional[str] = None  # WIN, LOSE, TIMEOUT, PENDING
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl_percent: Optional[float] = None
    method: Optional[str] = None  # integrated_consensus, enhanced_priority, etc.


class OutcomeTracker:
    """
    Tracks signal outcomes for quality monitoring and calibration.
    
    Features:
    - Stores pending signals with TP/SL levels
    - Checks outcomes after horizon period
    - Aggregates statistics by symbol, exchange, method
    - Persists data for analysis and retraining
    """
    
    def __init__(
        self,
        data_dir: Optional[str] = None,
        horizon_hours: int = 4,
        check_interval_minutes: int = 15,
    ):
        """
        Initialize outcome tracker.
        
        Args:
            data_dir: Directory to store tracking data
            horizon_hours: How many hours to wait before checking outcome
            check_interval_minutes: How often to check pending signals
        """
        self.data_dir = Path(data_dir) if data_dir else Path("data/outcome_tracking")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.horizon_hours = horizon_hours
        self.check_interval = timedelta(minutes=check_interval_minutes)
        
        # In-memory storage
        self.pending_signals: Dict[str, TrackedSignal] = {}
        self.completed_signals: List[TrackedSignal] = []
        
        # Statistics
        self.stats = defaultdict(lambda: {
            'total': 0,
            'wins': 0,
            'losses': 0,
            'timeouts': 0,
            'win_rate': 0.0,
            'avg_confidence': 0.0,
            'avg_pnl': 0.0,
        })
        
        # Load existing data
        self._load_data()
    
    def add_signal(
        self,
        symbol: str,
        signal_type: str,
        entry_price: float,
        tp_price: float,
        sl_price: float,
        confidence: float,
        exchange: str = 'binance',
        timeframe: str = '1h',
        method: str = 'unknown',
    ) -> str:
        """
        Add a new signal to track.
        
        Args:
            symbol: Trading pair
            signal_type: BUY or SELL
            entry_price: Entry price
            tp_price: Take profit price
            sl_price: Stop loss price
            confidence: Signal confidence (0-1)
            exchange: Exchange used
            timeframe: Timeframe
            method: Signal generation method
            
        Returns:
            Signal ID for reference
        """
        signal_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        entry_time = datetime.now()
        horizon_end = entry_time + timedelta(hours=self.horizon_hours)
        
        signal = TrackedSignal(
            id=signal_id,
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            signal_type=signal_type,
            confidence=confidence,
            entry_price=entry_price,
            tp_price=tp_price,
            sl_price=sl_price,
            entry_time=entry_time,
            horizon_end=horizon_end,
            method=method,
        )
        
        self.pending_signals[signal_id] = signal
        logger.info(f"Tracking signal: {signal_id} ({signal_type} {symbol} @ {entry_price:.4f})")
        
        # Persist
        self._save_pending()
        
        return signal_id
    
    def check_outcome(
        self,
        signal_id: str,
        current_price: float,
        high_since_entry: float,
        low_since_entry: float,
    ) -> Optional[str]:
        """
        Check if a signal has hit TP or SL.
        
        Args:
            signal_id: Signal ID
            current_price: Current price
            high_since_entry: Highest price since entry
            low_since_entry: Lowest price since entry
            
        Returns:
            Outcome string (WIN, LOSE, TIMEOUT) or None if still pending
        """
        if signal_id not in self.pending_signals:
            return None
        
        signal = self.pending_signals[signal_id]
        
        is_long = signal.signal_type == 'BUY'
        
        # Check if horizon expired
        horizon_expired = datetime.now() >= signal.horizon_end
        
        if is_long:
            # LONG: TP is above entry, SL is below
            tp_hit = high_since_entry >= signal.tp_price
            sl_hit = low_since_entry <= signal.sl_price
        else:
            # SHORT: TP is below entry, SL is above
            tp_hit = low_since_entry <= signal.tp_price
            sl_hit = high_since_entry >= signal.sl_price
        
        # Determine outcome
        outcome = None
        exit_price = current_price
        
        if tp_hit and not sl_hit:
            outcome = 'WIN'
            exit_price = signal.tp_price
        elif sl_hit and not tp_hit:
            outcome = 'LOSE'
            exit_price = signal.sl_price
        elif tp_hit and sl_hit:
            # Both hit - assume SL first (conservative)
            outcome = 'LOSE'
            exit_price = signal.sl_price
        elif horizon_expired:
            outcome = 'TIMEOUT'
            exit_price = current_price
        
        if outcome:
            # Calculate PnL
            if is_long:
                pnl_pct = (exit_price - signal.entry_price) / signal.entry_price * 100
            else:
                pnl_pct = (signal.entry_price - exit_price) / signal.entry_price * 100
            
            # Update signal
            signal.outcome = outcome
            signal.exit_price = exit_price
            signal.exit_time = datetime.now()
            signal.pnl_percent = pnl_pct
            
            # Move to completed
            self.completed_signals.append(signal)
            del self.pending_signals[signal_id]
            
            # Update stats
            self._update_stats(signal)
            
            # Persist
            self._save_completed()
            self._save_pending()
            
            logger.info(
                f"Signal {signal_id} completed: {outcome} | "
                f"PnL: {pnl_pct:+.2f}% | Exit: {exit_price:.4f}"
            )
        
        return outcome
    
    async def check_all_pending(self, get_price_func) -> List[Tuple[str, str]]:
        """
        Check all pending signals for outcomes.
        
        Args:
            get_price_func: Async function(symbol, exchange) -> (current, high, low)
            
        Returns:
            List of (signal_id, outcome) for resolved signals
        """
        results = []
        
        for signal_id, signal in list(self.pending_signals.items()):
            try:
                current, high, low = await get_price_func(
                    signal.symbol, 
                    signal.exchange
                )
                
                outcome = self.check_outcome(signal_id, current, high, low)
                if outcome:
                    results.append((signal_id, outcome))
                    
            except Exception as e:
                logger.warning(f"Failed to check {signal_id}: {e}")
        
        return results
    
    def _update_stats(self, signal: TrackedSignal):
        """Update statistics for a completed signal."""
        keys = [
            f"all",
            f"symbol:{signal.symbol}",
            f"exchange:{signal.exchange}",
            f"method:{signal.method}",
            f"type:{signal.signal_type}",
        ]
        
        for key in keys:
            stats = self.stats[key]
            stats['total'] += 1
            
            if signal.outcome == 'WIN':
                stats['wins'] += 1
            elif signal.outcome == 'LOSE':
                stats['losses'] += 1
            else:
                stats['timeouts'] += 1
            
            # Update averages
            stats['win_rate'] = stats['wins'] / stats['total'] * 100 if stats['total'] > 0 else 0
            
            # Rolling averages
            n = stats['total']
            stats['avg_confidence'] = (
                stats['avg_confidence'] * (n - 1) + signal.confidence
            ) / n
            
            if signal.pnl_percent is not None:
                stats['avg_pnl'] = (
                    stats['avg_pnl'] * (n - 1) + signal.pnl_percent
                ) / n
    
    def get_stats(self, key: str = 'all') -> Dict:
        """Get statistics for a specific key."""
        return dict(self.stats.get(key, {}))
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get all statistics."""
        return {k: dict(v) for k, v in self.stats.items()}
    
    def get_symbol_ranking(self) -> List[Tuple[str, float]]:
        """Get symbols ranked by win rate."""
        symbol_stats = [
            (k.replace('symbol:', ''), v['win_rate'])
            for k, v in self.stats.items()
            if k.startswith('symbol:') and v['total'] >= 5
        ]
        return sorted(symbol_stats, key=lambda x: x[1], reverse=True)
    
    def get_exchange_ranking(self) -> List[Tuple[str, float]]:
        """Get exchanges ranked by win rate."""
        exchange_stats = [
            (k.replace('exchange:', ''), v['win_rate'])
            for k, v in self.stats.items()
            if k.startswith('exchange:') and v['total'] >= 5
        ]
        return sorted(exchange_stats, key=lambda x: x[1], reverse=True)
    
    def get_confidence_calibration(self) -> Dict[str, float]:
        """
        Get suggested confidence thresholds based on outcomes.
        
        Returns recommended minimum confidence for profitable trading.
        """
        # Group completed signals by confidence bins
        bins = defaultdict(list)
        
        for signal in self.completed_signals:
            conf_bin = int(signal.confidence * 10) / 10  # 0.0, 0.1, 0.2, ...
            bins[conf_bin].append(signal.outcome == 'WIN')
        
        # Find minimum confidence where win rate > 50%
        calibration = {}
        for conf, outcomes in sorted(bins.items()):
            if len(outcomes) >= 10:  # Need enough samples
                win_rate = sum(outcomes) / len(outcomes) * 100
                calibration[f"{conf:.1f}"] = win_rate
        
        # Find threshold
        min_profitable = None
        for conf_str, wr in calibration.items():
            if wr >= 50:
                min_profitable = float(conf_str)
                break
        
        return {
            'calibration': calibration,
            'recommended_min_confidence': min_profitable or 0.6,
            'total_samples': len(self.completed_signals),
        }
    
    def export_for_retraining(self) -> List[Dict]:
        """
        Export completed signals for model retraining.
        
        Returns list of dicts suitable for creating training labels.
        """
        return [
            {
                'symbol': s.symbol,
                'exchange': s.exchange,
                'timeframe': s.timeframe,
                'signal_type': s.signal_type,
                'entry_price': s.entry_price,
                'tp_price': s.tp_price,
                'sl_price': s.sl_price,
                'entry_time': s.entry_time.isoformat(),
                'exit_time': s.exit_time.isoformat() if s.exit_time else None,
                'outcome': s.outcome,
                'pnl_percent': s.pnl_percent,
                'confidence': s.confidence,
                'method': s.method,
            }
            for s in self.completed_signals
        ]
    
    def _save_pending(self):
        """Save pending signals to disk."""
        path = self.data_dir / "pending_signals.json"
        data = {
            k: {
                **asdict(v),
                'entry_time': v.entry_time.isoformat(),
                'horizon_end': v.horizon_end.isoformat(),
            }
            for k, v in self.pending_signals.items()
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_completed(self):
        """Save completed signals to disk."""
        path = self.data_dir / "completed_signals.json"
        data = [
            {
                **asdict(s),
                'entry_time': s.entry_time.isoformat(),
                'horizon_end': s.horizon_end.isoformat(),
                'exit_time': s.exit_time.isoformat() if s.exit_time else None,
            }
            for s in self.completed_signals[-1000:]  # Keep last 1000
        ]
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Save stats
        stats_path = self.data_dir / "stats.json"
        with open(stats_path, 'w') as f:
            json.dump(self.get_all_stats(), f, indent=2)
    
    def _load_data(self):
        """Load existing data from disk."""
        # Load pending
        pending_path = self.data_dir / "pending_signals.json"
        if pending_path.exists():
            try:
                with open(pending_path) as f:
                    data = json.load(f)
                for k, v in data.items():
                    v['entry_time'] = datetime.fromisoformat(v['entry_time'])
                    v['horizon_end'] = datetime.fromisoformat(v['horizon_end'])
                    self.pending_signals[k] = TrackedSignal(**v)
                logger.info(f"Loaded {len(self.pending_signals)} pending signals")
            except Exception as e:
                logger.warning(f"Failed to load pending signals: {e}")
        
        # Load completed
        completed_path = self.data_dir / "completed_signals.json"
        if completed_path.exists():
            try:
                with open(completed_path) as f:
                    data = json.load(f)
                for item in data:
                    item['entry_time'] = datetime.fromisoformat(item['entry_time'])
                    item['horizon_end'] = datetime.fromisoformat(item['horizon_end'])
                    if item.get('exit_time'):
                        item['exit_time'] = datetime.fromisoformat(item['exit_time'])
                    self.completed_signals.append(TrackedSignal(**item))
                logger.info(f"Loaded {len(self.completed_signals)} completed signals")
            except Exception as e:
                logger.warning(f"Failed to load completed signals: {e}")
        
        # Rebuild stats from completed
        for signal in self.completed_signals:
            self._update_stats(signal)


# Singleton instance
_tracker: Optional[OutcomeTracker] = None


def get_outcome_tracker() -> OutcomeTracker:
    """Get or create OutcomeTracker singleton."""
    global _tracker
    if _tracker is None:
        _tracker = OutcomeTracker()
    return _tracker


if __name__ == "__main__":
    # Test the tracker
    print("=" * 60)
    print("OUTCOME TRACKER TEST")
    print("=" * 60)
    
    tracker = OutcomeTracker(data_dir="data/test_tracking")
    
    # Add test signal
    signal_id = tracker.add_signal(
        symbol="BTC/USDT",
        signal_type="BUY",
        entry_price=42000,
        tp_price=43500,  # +3.5%
        sl_price=41000,  # -2.4%
        confidence=0.75,
        exchange="binance",
        method="integrated_consensus",
    )
    
    print(f"\nAdded signal: {signal_id}")
    print(f"Pending signals: {len(tracker.pending_signals)}")
    
    # Simulate TP hit
    outcome = tracker.check_outcome(
        signal_id,
        current_price=43600,
        high_since_entry=43600,
        low_since_entry=41800,
    )
    
    print(f"\nOutcome: {outcome}")
    print(f"Completed signals: {len(tracker.completed_signals)}")
    
    # Show stats
    print(f"\nStats: {tracker.get_stats('all')}")
    
    # Show calibration
    print(f"\nCalibration: {tracker.get_confidence_calibration()}")

