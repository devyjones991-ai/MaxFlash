"""
Signal Logger - Logs ALL signals to CSV for analysis.
Based on quick_start_code.md specifications.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class SignalLogger:
    """
    Logs ALL trading signals to CSV for analysis.
    
    Columns: timestamp, symbol, tier, signal, confidence, rsi, macd,
             price_change_24h, volume_ratio, issues, was_inverted, final_confidence, result
    """
    
    def __init__(self, log_file: str = 'signal_log.csv'):
        self.log_file = log_file
        self._init_csv()
    
    def _init_csv(self):
        """Creates CSV with headers if not exists."""
        if not Path(self.log_file).exists():
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'symbol',
                    'tier',
                    'signal',
                    'confidence',
                    'rsi',
                    'macd',
                    'price_change_24h',
                    'volume_ratio',
                    'issues',
                    'was_inverted',
                    'final_confidence',
                    'result'  # Later: WIN/LOSS
                ])
    
    def log_signal(
        self,
        symbol: str,
        tier: str,
        signal_direction: str,
        confidence: float,
        rsi: float,
        macd: float,
        price_change_24h: float,
        volume_ratio: float,
        validation_result: Dict
    ) -> None:
        """Writes signal to CSV."""
        
        issues_str = "; ".join(validation_result.get('issues', [])) or "OK"
        
        row = [
            datetime.now().isoformat(),
            symbol,
            tier,
            signal_direction,
            f"{confidence:.1f}",
            f"{rsi:.1f}",
            f"{macd:.6f}",
            f"{price_change_24h:.2f}",
            f"{volume_ratio:.2f}",
            issues_str,
            "YES" if validation_result.get('was_inverted', False) else "NO",
            f"{validation_result.get('final_confidence', confidence):.1f}",
            ""  # Empty for now, filled later
        ]
        
        with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)
        
        # Print to console with colors
        self._print_signal(symbol, signal_direction, confidence, validation_result)
    
    def _print_signal(self, symbol: str, signal: str, confidence: float, validation: Dict):
        """Pretty print to console."""
        
        if validation.get('is_valid', True):
            logger.info(f"✅ {symbol:12} | {signal:6} {confidence:5.0f}%")
        else:
            logger.warning(f"⚠️  {symbol:12} | {signal:6} {confidence:5.0f}%")
            for issue in validation.get('issues', []):
                logger.warning(f"   └─ {issue}")
    
    def update_result(self, timestamp: str, symbol: str, result: str):
        """Updates signal result (WIN/LOSS) after trade completion."""
        # Read all rows
        rows = []
        with open(self.log_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Find and update the row
        for i, row in enumerate(rows):
            if len(row) >= 2 and row[0] == timestamp and row[1] == symbol:
                rows[i][-1] = result
                break
        
        # Write back
        with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)


# Singleton instance
_signal_logger: Optional[SignalLogger] = None


def get_signal_logger() -> SignalLogger:
    """Get or create SignalLogger singleton."""
    global _signal_logger
    if _signal_logger is None:
        _signal_logger = SignalLogger()
    return _signal_logger
