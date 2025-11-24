"""
Tests for Risk Manager.
"""

import unittest

from utils.risk_manager import RiskManager


class TestRiskManager(unittest.TestCase):
    """Test Risk Management."""

    def setUp(self):
        """Set up test fixtures."""
        self.risk_manager = RiskManager(risk_per_trade=0.01, max_risk_per_trade=0.02, min_risk_reward_ratio=2.0)

    def test_calculate_position_size(self):
        """Test position size calculation."""
        entry_price = 100
        stop_loss_price = 98  # 2% risk
        account_balance = 10000

        position_size = self.risk_manager.calculate_position_size(entry_price, stop_loss_price, account_balance)

        # Should calculate correctly
        risk_amount = account_balance * 0.01  # 1% = 100
        risk_per_unit = abs(entry_price - stop_loss_price)  # 2
        expected_size = risk_amount / risk_per_unit  # 50

        self.assertAlmostEqual(position_size, expected_size, places=2)

    def test_calculate_stop_loss_long(self):
        """Test stop loss calculation for long position."""
        entry_price = 100
        order_block_low = 98
        atr = 2

        # With Order Block
        stop_loss = self.risk_manager.calculate_stop_loss(
            entry_price, order_block_low=order_block_low, direction="long"
        )

        assert stop_loss < order_block_low

        # With ATR only
        stop_loss_atr = self.risk_manager.calculate_stop_loss(entry_price, atr=atr, direction="long")

        assert stop_loss_atr < entry_price

    def test_calculate_stop_loss_short(self):
        """Test stop loss calculation for short position."""
        entry_price = 100
        order_block_high = 102
        atr = 2

        # With Order Block
        stop_loss = self.risk_manager.calculate_stop_loss(
            entry_price, order_block_high=order_block_high, direction="short"
        )

        assert stop_loss > order_block_high

        # With ATR only
        stop_loss_atr = self.risk_manager.calculate_stop_loss(entry_price, atr=atr, direction="short")

        assert stop_loss_atr > entry_price

    def test_calculate_take_profit_long(self):
        """Test take profit calculation for long position."""
        entry_price = 100
        stop_loss_price = 98  # 2% risk
        hvn_levels = [105, 110]
        fvg_levels = [{"high": 107, "low": 106, "type": "bullish"}]

        tp1, _tp2 = self.risk_manager.calculate_take_profit(
            entry_price, stop_loss_price, hvn_levels, fvg_levels, direction="long"
        )

        # TP1 should be at least min risk:reward
        risk = abs(entry_price - stop_loss_price)  # 2
        min_tp = entry_price + (risk * 2.0)  # 104

        assert tp1 >= min_tp

        # TP1 should use nearest HVN
        assert tp1 == 105

    def test_calculate_trailing_stop_long(self):
        """Test trailing stop for long position."""
        current_price = 105
        entry_price = 100
        current_stop_loss = 98
        atr = 2

        new_stop = self.risk_manager.calculate_trailing_stop(
            current_price, entry_price, current_stop_loss, atr, direction="long"
        )

        # Trailing stop should move up but not go below entry
        assert new_stop >= current_stop_loss
        assert new_stop <= current_price

    def test_validate_trade(self):
        """Test trade validation."""
        entry_price = 100
        stop_loss_price = 98
        take_profit_price = 104  # 2:1 risk:reward

        is_valid, _reason = self.risk_manager.validate_trade(entry_price, stop_loss_price, take_profit_price)

        assert is_valid

        # Test invalid trade (stop equals entry)
        is_valid_invalid, _reason_invalid = self.risk_manager.validate_trade(100, 100, 104)

        assert not is_valid_invalid

    def test_validate_trade_risk_reward(self):
        """Test trade validation with risk:reward ratio."""
        entry_price = 100
        stop_loss_price = 98  # 2% risk
        take_profit_price = 103  # 3% reward = 1.5:1 ratio (below 2.0 minimum)

        is_valid, reason = self.risk_manager.validate_trade(entry_price, stop_loss_price, take_profit_price)

        # Should fail because risk:reward is below minimum
        assert not is_valid
        assert "Risk:Reward" in reason


if __name__ == "__main__":
    unittest.main()
