"""
Advanced risk management for trading operations.
Implements position sizing, portfolio risk limits, and trade validation.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.config import settings
from utils.logger_config import setup_logging

logger = setup_logging()


@dataclass
class PositionInfo:
    """Information about an open position."""

    symbol: str
    side: str  # 'buy' or 'sell'
    entry_price: float
    amount: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    opened_at: datetime
    unrealized_pnl: float = 0.0


class AdvancedRiskManager:
    """
    Production-grade risk management system.
    Implements Kelly Criterion, portfolio limits, correlation checks, and circuit breakers.
    """

    def __init__(
        self,
        account_balance: float,
        max_risk_per_trade: Optional[float] = None,
        max_portfolio_risk: Optional[float] = None,
        max_correlated_exposure: Optional[float] = None,
        daily_loss_limit: Optional[float] = None,
        max_positions: int = 10,
    ):
        """
        Initialize risk manager.

        Args:
            account_balance: Total account balance
            max_risk_per_trade: Maximum risk per single trade (as fraction)
            max_portfolio_risk: Maximum total portfolio risk (as fraction)
            max_correlated_exposure: Maximum correlated positions exposure
            daily_loss_limit: Maximum daily loss before halting (as fraction)
            max_positions: Maximum number of concurrent positions
        """
        risk_params = settings.get_risk_params()

        self.account_balance = account_balance
        self.max_risk_per_trade = max_risk_per_trade or risk_params.get("max_risk_per_trade", 0.01)
        self.max_portfolio_risk = max_portfolio_risk or 0.05  # 5% default
        self.max_correlated_exposure = max_correlated_exposure or 0.10  # 10% default
        self.daily_loss_limit = daily_loss_limit or (
            settings.MAX_DAILY_LOSS_USD / account_balance if account_balance > 0 else 0.02
        )
        self.max_positions = max_positions

        # Tracking
        self.current_positions: list[PositionInfo] = []
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        self.total_trades = 0
        self.winning_trades = 0

        logger.info(
            f"RiskManager initialized: balance=${account_balance:,.2f}, "
            f"max_risk={self.max_risk_per_trade * 100}%, daily_limit={self.daily_loss_limit * 100}%"
        )

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        confidence: float = 0.6,
        use_kelly: bool = True,
    ) -> float:
        """
        Calculate optimal position size using fixed risk + Kelly Criterion.

        Args:
            entry_price: Entry price
            stop_loss: Stop-loss price
            confidence: Signal confidence (0.5-1.0)
            use_kelly: Use Kelly Criterion adjustment

        Returns:
            Position size in base currency
        """
        # Risk amount
        risk_amount = self.account_balance * self.max_risk_per_trade

        # Price risk per unit
        price_risk = abs(entry_price - stop_loss)

        if price_risk == 0:
            logger.warning("Zero price risk - using 2% of entry price as fallback")
            price_risk = entry_price * 0.02

        # Base position size (fixed risk)
        base_position_size = risk_amount / price_risk

        # Kelly Criterion adjustment
        if use_kelly and self.total_trades > 10:  # Need history for Kelly
            win_rate = self.winning_trades / self.total_trades
            avg_win_loss_ratio = 2.0  # Assume 2:1 reward:risk

            # Kelly percentage: (p*b - q) / b where p=win_rate, q=1-p, b=win/loss ratio
            kelly_pct = (win_rate * avg_win_loss_ratio - (1 - win_rate)) / avg_win_loss_ratio
            kelly_pct = max(0, min(kelly_pct, 0.25))  # Cap at 25% Kelly

            # Adjust by confidence
            confidence_adj = min(confidence, 1.0)
            kelly_multiplier = (kelly_pct / 0.25) * confidence_adj

            position_size = base_position_size * (1 + kelly_multiplier)
        else:
            # Simple confidence adjustment
            position_size = base_position_size * min(confidence, 1.0)

        logger.debug(f"Position size calculated: ${position_size * entry_price:,.2f} ({position_size:.4f} units)")

        return position_size

    def validate_trade(
        self,
        symbol: str,
        side: str,
        amount: float,
        entry_price: float,
        stop_loss: Optional[float] = None,
    ) -> tuple[bool, str]:
        """
        Multi-layer trade validation.

        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Position amount
            entry_price: Entry price
            stop_loss: Stop-loss price

        Returns:
            (is_valid, reason) tuple
        """
        # Check daily loss limit (circuit breaker)
        if self._check_daily_loss_limit():
            return False, "Daily loss limit reached - trading halted"

        # Check maximum positions
        if len(self.current_positions) >= self.max_positions:
            return False, f"Maximum positions limit reached ({self.max_positions})"

        # Check portfolio risk
        total_risk = self._calculate_total_portfolio_risk()
        if stop_loss:
            trade_risk = abs(entry_price - stop_loss) * amount
            if (total_risk + trade_risk) > self.account_balance * self.max_portfolio_risk:
                return (
                    False,
                    f"Portfolio risk limit exceeded ({self.max_portfolio_risk * 100}%)",
                )

        # Check correlation exposure
        if self._check_correlation_exposure(symbol):
            return (
                False,
                f"Correlated exposure limit exceeded ({self.max_correlated_exposure * 100}%)",
            )

        # Check position size sanity
        position_value = amount * entry_price
        if position_value > self.account_balance * 0.5:  # Max 50% of account in one trade
            return False, "Position size exceeds 50% of account balance"

        if position_value < self.account_balance * 0.001:  # Min 0.1% of account
            return False, "Position size too small (< 0.1% of account)"

        return True, "Trade validated"

    def _check_daily_loss_limit(self) -> bool:
        """
        Check if daily loss limit is reached.

        Returns:
            True if limit reached (halt trading)
        """
        # Reset daily P&L if new day
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = current_date
            logger.info("Daily P&L reset")

        # Check limit
        daily_loss = -self.daily_pnl if self.daily_pnl < 0 else 0
        limit_amount = self.account_balance * self.daily_loss_limit

        if daily_loss >= limit_amount:
            logger.warning(f"⛔ Daily loss limit reached: -${daily_loss:,.2f} / -${limit_amount:,.2f}")
            return True

        return False

    def _calculate_total_portfolio_risk(self) -> float:
        """Calculate total portfolio risk from open positions."""
        total_risk = 0.0

        for position in self.current_positions:
            if position.stop_loss:
                risk = abs(position.entry_price - position.stop_loss) * position.amount
                total_risk += risk

        return total_risk

    def _check_correlation_exposure(self, symbol: str) -> bool:
        """
        Check if adding this symbol would exceed correlation exposure limit.

        Args:
            symbol: Symbol to check

        Returns:
            True if correlation limit would be exceeded
        """
        # Extract base currency (e.g., 'BTC' from 'BTC/USDT')
        base_currency = symbol.split("/")[0]

        # Count exposure to same base currency
        same_currency_value = 0.0

        for position in self.current_positions:
            if position.symbol.startswith(base_currency):
                position_value = position.amount * position.entry_price
                same_currency_value += position_value

        # Check if adding new position would exceed limit
        limit_value = self.account_balance * self.max_correlated_exposure

        if same_currency_value >= limit_value:
            logger.warning(f"Correlation limit for {base_currency}: ${same_currency_value:,.2f} / ${limit_value:,.2f}")
            return True

        return False

    def add_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        amount: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ):
        """Add a new position to tracking."""
        position = PositionInfo(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            amount=amount,
            stop_loss=stop_loss,
            take_profit=take_profit,
            opened_at=datetime.now(),
        )

        self.current_positions.append(position)
        self.total_trades += 1

        logger.info(f"Position added: {symbol} {side} {amount} @ ${entry_price:,.2f} (SL: ${stop_loss or 'None'})")

    def close_position(self, symbol: str, exit_price: float, update_stats: bool = True) -> Optional[float]:
        """
        Close a position and calculate P&L.

        Args:
            symbol: Trading pair
            exit_price: Exit price
            update_stats: Update trading statistics

        Returns:
            Realized P&L
        """
        # Find position
        position = None
        for i, pos in enumerate(self.current_positions):
            if pos.symbol == symbol:
                position = self.current_positions.pop(i)
                break

        if not position:
            logger.warning(f"Position not found for {symbol}")
            return None

        # Calculate P&L
        if position.side == "buy":
            pnl = (exit_price - position.entry_price) * position.amount
        else:  # sell
            pnl = (position.entry_price - exit_price) * position.amount

        # Update statistics
        if update_stats:
            self.daily_pnl += pnl
            self.account_balance += pnl

            if pnl > 0:
                self.winning_trades += 1

        logger.info(
            f"Position closed: {symbol} P&L=${pnl:+,.2f} "
            f"(daily=${self.daily_pnl:+,.2f}, balance=${self.account_balance:,.2f})"
        )

        return pnl

    def update_position_pnl(self, symbol: str, current_price: float):
        """Update unrealized P&L for a position."""
        for position in self.current_positions:
            if position.symbol == symbol:
                if position.side == "buy":
                    position.unrealized_pnl = (current_price - position.entry_price) * position.amount
                else:
                    position.unrealized_pnl = (position.entry_price - current_price) * position.amount

    def get_portfolio_stats(self) -> dict[str, Any]:
        """Get current portfolio statistics."""
        total_value = sum(pos.amount * pos.entry_price for pos in self.current_positions)
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.current_positions)
        total_risk = self._calculate_total_portfolio_risk()

        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0

        return {
            "account_balance": self.account_balance,
            "daily_pnl": self.daily_pnl,
            "daily_pnl_pct": (self.daily_pnl / self.account_balance * 100),
            "open_positions": len(self.current_positions),
            "total_position_value": total_value,
            "total_unrealized_pnl": total_unrealized_pnl,
            "total_risk": total_risk,
            "risk_percentage": (total_risk / self.account_balance * 100),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "win_rate": win_rate,
            "max_positions": self.max_positions,
            "daily_loss_limit": self.account_balance * self.daily_loss_limit,
            "trading_halted": self._check_daily_loss_limit(),
        }
