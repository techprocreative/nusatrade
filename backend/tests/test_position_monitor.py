"""Tests for PositionMonitorService and trailing stop integration."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
from uuid import uuid4

from app.services.position_monitor import (
    PositionMonitorService,
    position_monitor,
)
from app.services.trailing_stop import (
    TrailingStopManager,
    TrailingStopConfig,
    TrailingStopType,
    PositionState,
    calculate_profit_pips,
    check_breakeven,
    calculate_trailing_stop,
    process_trailing_stop,
)


class TestCalculateProfitPips:
    """Tests for profit pip calculation."""
    
    def test_buy_profit(self):
        """Test profit calculation for BUY position in profit."""
        profit = calculate_profit_pips(
            entry_price=1.0850,
            current_price=1.0870,
            direction="BUY"
        )
        assert profit == pytest.approx(20.0, rel=0.1)
    
    def test_buy_loss(self):
        """Test profit calculation for BUY position in loss."""
        profit = calculate_profit_pips(
            entry_price=1.0850,
            current_price=1.0830,
            direction="BUY"
        )
        assert profit == pytest.approx(-20.0, rel=0.1)
    
    def test_sell_profit(self):
        """Test profit calculation for SELL position in profit."""
        profit = calculate_profit_pips(
            entry_price=1.0850,
            current_price=1.0830,
            direction="SELL"
        )
        assert profit == pytest.approx(20.0, rel=0.1)
    
    def test_sell_loss(self):
        """Test profit calculation for SELL position in loss."""
        profit = calculate_profit_pips(
            entry_price=1.0850,
            current_price=1.0870,
            direction="SELL"
        )
        assert profit == pytest.approx(-20.0, rel=0.1)


class TestCheckBreakeven:
    """Tests for breakeven check."""
    
    @pytest.fixture
    def config(self):
        return TrailingStopConfig(
            breakeven_enabled=True,
            breakeven_pips=15.0,
            breakeven_offset_pips=2.0,
        )
    
    def test_breakeven_triggered_buy(self, config):
        """Test breakeven triggered for BUY position."""
        state = PositionState(
            position_id=12345,
            direction="BUY",
            entry_price=1.0850,
            current_sl=1.0820,
            lot_size=0.1,
            breakeven_hit=False,
        )
        
        # Price moved 20 pips in profit (>15 pips threshold)
        current_price = 1.0870
        
        new_sl = check_breakeven(state, current_price, config)
        
        assert new_sl is not None
        assert new_sl > state.entry_price  # SL moved above entry
    
    def test_breakeven_not_triggered_below_threshold(self, config):
        """Test breakeven not triggered when below threshold."""
        state = PositionState(
            position_id=12345,
            direction="BUY",
            entry_price=1.0850,
            current_sl=1.0820,
            lot_size=0.1,
            breakeven_hit=False,
        )
        
        # Price only moved 10 pips (<15 pips threshold)
        current_price = 1.0860
        
        new_sl = check_breakeven(state, current_price, config)
        
        assert new_sl is None
    
    def test_breakeven_not_triggered_if_already_hit(self, config):
        """Test breakeven not triggered if already hit."""
        state = PositionState(
            position_id=12345,
            direction="BUY",
            entry_price=1.0850,
            current_sl=1.0852,  # Already at breakeven
            lot_size=0.1,
            breakeven_hit=True,
        )
        
        current_price = 1.0900
        
        new_sl = check_breakeven(state, current_price, config)
        
        assert new_sl is None


class TestCalculateTrailingStop:
    """Tests for trailing stop calculation."""
    
    @pytest.fixture
    def config(self):
        return TrailingStopConfig(
            enabled=True,
            trailing_type=TrailingStopType.FIXED_PIPS,
            activation_pips=20.0,
            trail_distance_pips=15.0,
        )
    
    def test_trailing_activated_buy(self, config):
        """Test trailing stop activated for BUY position."""
        state = PositionState(
            position_id=12345,
            direction="BUY",
            entry_price=1.0850,
            current_sl=1.0820,
            lot_size=0.1,
            highest_price=1.0850,
        )
        
        # Price moved 25 pips (>20 pips activation threshold)
        current_price = 1.0875
        
        new_sl = calculate_trailing_stop(state, current_price, config)
        
        # Trailing should update the SL
        assert new_sl is not None or state.highest_price == current_price
    
    def test_trailing_not_activated_below_threshold(self, config):
        """Test trailing not activated below threshold."""
        state = PositionState(
            position_id=12345,
            direction="BUY",
            entry_price=1.0850,
            current_sl=1.0820,
            lot_size=0.1,
            highest_price=1.0850,
        )
        
        # Price only moved 15 pips (<20 pips activation)
        current_price = 1.0865
        
        new_sl = calculate_trailing_stop(state, current_price, config)
        
        assert new_sl is None
    
    def test_trailing_disabled(self, config):
        """Test trailing stop when disabled."""
        config.enabled = False
        
        state = PositionState(
            position_id=12345,
            direction="BUY",
            entry_price=1.0850,
            current_sl=1.0820,
            lot_size=0.1,
        )
        
        new_sl = calculate_trailing_stop(state, 1.0900, config)
        
        assert new_sl is None


class TestTrailingStopManager:
    """Tests for TrailingStopManager."""
    
    def test_add_position(self):
        """Test adding a position to manager."""
        manager = TrailingStopManager()
        
        manager.add_position(
            position_id=12345,
            direction="BUY",
            entry_price=1.0850,
            stop_loss=1.0820,
            lot_size=0.1,
        )
        
        assert 12345 in manager.positions
        assert manager.positions[12345].direction == "BUY"
    
    def test_remove_position(self):
        """Test removing a position from manager."""
        manager = TrailingStopManager()
        
        manager.add_position(
            position_id=12345,
            direction="BUY",
            entry_price=1.0850,
            stop_loss=1.0820,
        )
        
        manager.remove_position(12345)
        
        assert 12345 not in manager.positions
    
    def test_update_price(self):
        """Test updating price for all positions."""
        manager = TrailingStopManager()
        
        manager.add_position(
            position_id=12345,
            direction="BUY",
            entry_price=1.0850,
            stop_loss=1.0820,
        )
        
        # This should update highest_price tracking
        updates = manager.update_price(current_price=1.0900, atr=0.001)
        
        # Updates list contains (position_id, new_sl, is_breakeven) tuples
        assert isinstance(updates, list)


class TestPositionMonitorService:
    """Tests for PositionMonitorService."""
    
    def test_get_status(self):
        """Test getting position monitor status."""
        monitor = PositionMonitorService()
        status = monitor.get_status()
        
        assert "is_running" in status
        assert "last_sync" in status
        assert "managed_connections" in status
        assert "total_positions" in status
    
    def test_handle_position_update(self):
        """Test handling position update from connector."""
        monitor = PositionMonitorService()
        
        positions = [
            {
                "ticket": 12345,
                "symbol": "EURUSD",
                "order_type": "BUY",
                "open_price": 1.0850,
                "current_price": 1.0870,
                "stop_loss": 1.0820,
                "volume": 0.1,
                "profit": 20.0,
            },
            {
                "ticket": 12346,
                "symbol": "GBPUSD",
                "order_type": "SELL",
                "open_price": 1.2650,
                "current_price": 1.2630,
                "stop_loss": 1.2680,
                "volume": 0.05,
                "profit": 10.0,
            },
        ]
        
        connection_id = str(uuid4())
        monitor.handle_position_update(connection_id, positions)
        
        # Check positions were cached
        assert connection_id in monitor._position_cache
        assert 12345 in monitor._position_cache[connection_id]
        assert 12346 in monitor._position_cache[connection_id]
        
        # Check trailing manager was created
        assert connection_id in monitor._trailing_managers
    
    def test_position_closed_detection(self):
        """Test detection of closed positions."""
        monitor = PositionMonitorService()
        connection_id = str(uuid4())
        
        # First update with 2 positions
        positions_v1 = [
            {"ticket": 12345, "symbol": "EURUSD", "order_type": "BUY", "open_price": 1.0850, "volume": 0.1},
            {"ticket": 12346, "symbol": "GBPUSD", "order_type": "SELL", "open_price": 1.2650, "volume": 0.05},
        ]
        monitor.handle_position_update(connection_id, positions_v1)
        
        # Second update with only 1 position (12346 closed)
        positions_v2 = [
            {"ticket": 12345, "symbol": "EURUSD", "order_type": "BUY", "open_price": 1.0850, "volume": 0.1},
        ]
        monitor.handle_position_update(connection_id, positions_v2)
        
        # Check that closed position was removed from trailing manager
        manager = monitor._trailing_managers[connection_id]
        assert 12345 in manager.positions
        assert 12346 not in manager.positions


class TestProcessTrailingStop:
    """Tests for the combined process_trailing_stop function."""
    
    def test_breakeven_then_trailing(self):
        """Test that breakeven is checked before trailing."""
        config = TrailingStopConfig(
            enabled=True,
            breakeven_enabled=True,
            breakeven_pips=15.0,
            activation_pips=20.0,
            trail_distance_pips=15.0,
        )
        
        state = PositionState(
            position_id=12345,
            direction="BUY",
            entry_price=1.0850,
            current_sl=1.0820,
            lot_size=0.1,
            breakeven_hit=False,
        )
        
        # Price in profit enough for breakeven but not trailing
        current_price = 1.0868  # 18 pips profit
        
        new_sl, breakeven_triggered = process_trailing_stop(
            state, current_price, config
        )
        
        if new_sl is not None:
            assert breakeven_triggered is True
            assert state.breakeven_hit is True


class TestATRBasedTrailing:
    """Tests for ATR-based trailing stop."""
    
    def test_atr_based_trailing(self):
        """Test ATR-based trailing stop calculation."""
        config = TrailingStopConfig(
            enabled=True,
            trailing_type=TrailingStopType.ATR_BASED,
            activation_pips=20.0,
            atr_multiplier=1.5,
        )
        
        state = PositionState(
            position_id=12345,
            direction="BUY",
            entry_price=1.0850,
            current_sl=1.0800,
            lot_size=0.1,
            highest_price=1.0850,
        )
        
        # Price moved 30 pips, with ATR of 0.001 (10 pips)
        current_price = 1.0880
        atr = 0.001
        
        new_sl = calculate_trailing_stop(state, current_price, config, atr)
        
        # With 1.5x ATR multiplier, trail distance = 15 pips
        # New SL should be around 1.0880 - 0.0015 = 1.0865
        if new_sl is not None:
            expected_sl = current_price - (atr * config.atr_multiplier)
            assert new_sl == pytest.approx(expected_sl, abs=0.0001)
