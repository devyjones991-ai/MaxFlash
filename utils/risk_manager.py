"""
Risk Management module.
Handles position sizing, stop loss, take profit, and trailing stops.
"""

from typing import Optional


class RiskManager:
    """
    Manages risk for trading positions.
    """

    def __init__(
        self, risk_per_trade: float = 0.01, max_risk_per_trade: float = 0.02, min_risk_reward_ratio: float = 2.0
    ):
        """
        Initialize Risk Manager.

        Args:
            risk_per_trade: Risk percentage per trade (default 1%)
            max_risk_per_trade: Maximum risk percentage per trade (default 2%)
            min_risk_reward_ratio: Minimum risk:reward ratio (default 2.0)
        """
        self.risk_per_trade = risk_per_trade
        self.max_risk_per_trade = max_risk_per_trade
        self.min_risk_reward_ratio = min_risk_reward_ratio

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        account_balance: float,
        risk_percentage: Optional[float] = None,
    ) -> float:
        """
        Calculate position size based on risk.

        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            account_balance: Current account balance
            risk_percentage: Risk percentage (uses self.risk_per_trade if None)

        Returns:
            Position size in base currency
        """
        if risk_percentage is None:
            risk_percentage = self.risk_per_trade

        # Clamp risk percentage
        risk_percentage = min(risk_percentage, self.max_risk_per_trade)

        # Calculate risk per unit
        risk_per_unit = abs(entry_price - stop_loss_price)

        if risk_per_unit == 0:
            return 0.0

        # Calculate position size
        risk_amount = account_balance * risk_percentage
        position_size = risk_amount / risk_per_unit

        return position_size

    def calculate_stop_loss(
        self,
        entry_price: float,
        order_block_low: Optional[float] = None,
        order_block_high: Optional[float] = None,
        atr: Optional[float] = None,
        direction: str = "long",
    ) -> float:
        """
        Calculate stop loss based on zones or ATR.

        Args:
            entry_price: Entry price
            order_block_low: Order Block low level (for long)
            order_block_high: Order Block high level (for short)
            atr: Average True Range
            direction: 'long' or 'short'

        Returns:
            Stop loss price
        """
        if direction == "long":
            # For long: stop below Order Block low or use ATR
            if order_block_low is not None:
                stop_loss = order_block_low * 0.999  # 0.1% below OB
            elif atr is not None:
                stop_loss = entry_price - (atr * 1.5)
            else:
                stop_loss = entry_price * 0.98  # 2% default
        else:  # short
            # For short: stop above Order Block high or use ATR
            if order_block_high is not None:
                stop_loss = order_block_high * 1.001  # 0.1% above OB
            elif atr is not None:
                stop_loss = entry_price + (atr * 1.5)
            else:
                stop_loss = entry_price * 1.02  # 2% default

        return stop_loss

    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss_price: float,
        hvn_levels: Optional[list] = None,
        fvg_levels: Optional[list] = None,
        opposite_ob: Optional[dict] = None,
        direction: str = "long",
    ) -> tuple[float, Optional[float]]:
        """
        Calculate take profit levels.

        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            hvn_levels: List of HVN levels
            fvg_levels: List of FVG levels (dicts with 'high' and 'low')
            opposite_ob: Opposite Order Block (for second target)
            direction: 'long' or 'short'

        Returns:
            Tuple of (TP1, TP2) prices
        """
        # Calculate risk
        risk = abs(entry_price - stop_loss_price)

        # TP1: Minimum risk:reward ratio
        tp1_min = (
            entry_price + (risk * self.min_risk_reward_ratio)
            if direction == "long"
            else entry_price - (risk * self.min_risk_reward_ratio)
        )

        # TP1: Nearest HVN or FVG
        tp1 = tp1_min

        if direction == "long":
            # Find nearest HVN above entry
            if hvn_levels:
                valid_hvns = [hvn for hvn in hvn_levels if hvn > entry_price]
                if valid_hvns:
                    nearest_hvn = min(valid_hvns)
                    if nearest_hvn >= tp1_min:
                        tp1 = nearest_hvn

            # Check FVGs
            if fvg_levels:
                for fvg in fvg_levels:
                    if fvg.get("type") == "bullish" and fvg["low"] > entry_price:
                        if fvg["low"] >= tp1_min:
                            tp1 = min(tp1, fvg["low"])

            # TP2: Opposite OB or further FVG
            tp2 = None
            if opposite_ob:
                tp2 = opposite_ob.get("high")

            # Check for further FVG
            if fvg_levels and not tp2:
                for fvg in fvg_levels:
                    if fvg.get("type") == "bullish" and fvg["high"] > tp1:
                        tp2 = fvg["high"]
                        break

        else:  # short
            # Find nearest HVN below entry
            if hvn_levels:
                valid_hvns = [hvn for hvn in hvn_levels if hvn < entry_price]
                if valid_hvns:
                    nearest_hvn = max(valid_hvns)
                    if nearest_hvn <= tp1_min:
                        tp1 = nearest_hvn

            # Check FVGs
            if fvg_levels:
                for fvg in fvg_levels:
                    if fvg.get("type") == "bearish" and fvg["high"] < entry_price:
                        if fvg["high"] <= tp1_min:
                            tp1 = max(tp1, fvg["high"])

            # TP2: Opposite OB or further FVG
            tp2 = None
            if opposite_ob:
                tp2 = opposite_ob.get("low")

            # Check for further FVG
            if fvg_levels and not tp2:
                for fvg in fvg_levels:
                    if fvg.get("type") == "bearish" and fvg["low"] < tp1:
                        tp2 = fvg["low"]
                        break

        return (tp1, tp2)

    def calculate_trailing_stop(
        self,
        current_price: float,
        entry_price: float,
        current_stop_loss: float,
        atr: float,
        direction: str = "long",
        trailing_distance_pct: float = 0.005,
    ) -> float:
        """
        Calculate trailing stop loss.

        Args:
            current_price: Current price
            entry_price: Original entry price
            current_stop_loss: Current stop loss
            atr: Average True Range
            direction: 'long' or 'short'
            trailing_distance_pct: Trailing distance as percentage

        Returns:
            Updated stop loss price
        """
        trailing_distance = current_price * trailing_distance_pct

        if direction == "long":
            # Trailing stop moves up only
            new_stop = current_price - trailing_distance

            # Ensure stop doesn't go below entry or current stop
            new_stop = max(new_stop, current_stop_loss, entry_price * 0.99)
        else:  # short
            # Trailing stop moves down only
            new_stop = current_price + trailing_distance

            # Ensure stop doesn't go above entry or current stop
            new_stop = min(new_stop, current_stop_loss, entry_price * 1.01)

        return new_stop

    def validate_trade(
        self, entry_price: float, stop_loss_price: float, take_profit_price: Optional[float] = None
    ) -> tuple[bool, str]:
        """
        Validate trade setup meets risk requirements.

        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            take_profit_price: Take profit price (optional)

        Returns:
            Tuple of (is_valid, reason)
        """
        risk = abs(entry_price - stop_loss_price)

        if risk == 0:
            return (False, "Stop loss equals entry price")

        if take_profit_price:
            reward = abs(take_profit_price - entry_price)
            risk_reward = reward / risk

            if risk_reward < self.min_risk_reward_ratio:
                return (False, f"Risk:Reward ratio {risk_reward:.2f} below minimum {self.min_risk_reward_ratio}")

        return (True, "Trade valid")
