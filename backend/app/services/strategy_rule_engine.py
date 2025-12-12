"""Strategy Rule Engine - Parses and evaluates strategy entry/exit rules against market data.

This module enables ML Bot to validate trading signals against user-defined strategy rules,
ensuring trades are only executed when both ML prediction and strategy conditions align.
"""

import re
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass

import pandas as pd
import numpy as np

from app.core.logging import get_logger


logger = get_logger(__name__)


@dataclass
class RuleEvaluationResult:
    """Result of evaluating a single rule."""
    rule_id: str
    condition: str
    action: str
    is_satisfied: bool
    indicator_values: Dict[str, float]
    error: Optional[str] = None


@dataclass
class StrategyValidationResult:
    """Result of validating ML signal against strategy rules."""
    valid: bool
    matched_rules: List[str]
    failed_rules: List[str]
    details: List[RuleEvaluationResult]
    current_indicators: Dict[str, float]
    message: str = ""


class StrategyRuleEngine:
    """
    Evaluates strategy entry/exit rules against market data.
    
    Supports conditions like:
    - "RSI < 30"
    - "RSI > 70 AND EMA(9) > EMA(21)"
    - "MACD > MACD_SIGNAL OR price > BB_UPPER"
    - "ADX > 25 AND price > SMA(50)"
    """
    
    # Regex patterns for parsing conditions
    INDICATOR_PATTERN = re.compile(
        r'(RSI|EMA|SMA|MACD|MACD_SIGNAL|MACD_HIST|ADX|STOCH_K|STOCH_D|'
        r'BB_UPPER|BB_LOWER|BB_MIDDLE|ATR|CCI|price|close|high|low|open|volume)'
        r'(?:\((\d+)\))?',
        re.IGNORECASE
    )
    
    COMPARISON_PATTERN = re.compile(
        r'([A-Za-z_]+(?:\(\d+\))?)\s*([<>=!]+)\s*([A-Za-z_]+(?:\(\d+\))?|-?\d+\.?\d*)',
        re.IGNORECASE
    )
    
    # Map indicator names to DataFrame columns
    INDICATOR_COLUMN_MAP = {
        'rsi': lambda period=14: f'rsi_{period}',
        'ema': lambda period: f'ema_{period}',
        'sma': lambda period: f'sma_{period}',
        'macd': lambda: 'macd',
        'macd_signal': lambda: 'macd_signal',
        'macd_hist': lambda: 'macd_hist',
        'adx': lambda: 'adx',
        'stoch_k': lambda: 'stoch_k',
        'stoch_d': lambda: 'stoch_d',
        'bb_upper': lambda: 'bb_upper',
        'bb_lower': lambda: 'bb_lower',
        'bb_middle': lambda: 'bb_middle',
        'atr': lambda: 'atr',
        'cci': lambda period=20: f'cci_{period}' if period != 20 else 'cci',
        'price': lambda: 'close',
        'close': lambda: 'close',
        'high': lambda: 'high',
        'low': lambda: 'low',
        'open': lambda: 'open',
        'volume': lambda: 'volume',
    }
    
    def __init__(self):
        self._indicator_cache: Dict[str, float] = {}
    
    def evaluate_entry_rules(
        self,
        rules: List[Dict[str, Any]],
        market_data: pd.DataFrame,
        ml_direction: str,
    ) -> StrategyValidationResult:
        """
        Evaluate entry rules and determine if ML signal should proceed.
        
        Args:
            rules: List of strategy entry rules from database
                   Each rule: {"id": "...", "condition": "RSI < 30", "action": "BUY", "description": "..."}
            market_data: DataFrame with OHLCV and indicator columns from FeatureEngineer
            ml_direction: ML model's prediction ("BUY", "SELL", or "HOLD")
            
        Returns:
            StrategyValidationResult with validation status and details
        """
        if not rules or len(rules) == 0:
            return StrategyValidationResult(
                valid=True,
                matched_rules=[],
                failed_rules=[],
                details=[],
                current_indicators={},
                message="No entry rules defined - allowing trade"
            )
        
        if ml_direction == "HOLD":
            return StrategyValidationResult(
                valid=True,
                matched_rules=[],
                failed_rules=[],
                details=[],
                current_indicators={},
                message="ML signal is HOLD - no validation needed"
            )
        
        # Clear cache for new evaluation
        self._indicator_cache = {}
        
        matched_rules = []
        failed_rules = []
        details = []
        
        # Get current indicator values
        current_indicators = self._get_current_indicators(market_data)
        
        # Filter rules that match ML direction
        relevant_rules = [
            r for r in rules 
            if r.get("action", "").upper() == ml_direction.upper()
        ]
        
        if not relevant_rules:
            # No rules for this direction - check if opposite rules are satisfied
            # If opposite rules are satisfied, block the trade
            opposite_direction = "SELL" if ml_direction == "BUY" else "BUY"
            opposite_rules = [
                r for r in rules 
                if r.get("action", "").upper() == opposite_direction
            ]
            
            if opposite_rules:
                for rule in opposite_rules:
                    result = self._evaluate_single_rule(rule, market_data)
                    if result.is_satisfied:
                        # Opposite rule is satisfied - block ML signal
                        return StrategyValidationResult(
                            valid=False,
                            matched_rules=[],
                            failed_rules=[result.rule_id],
                            details=[result],
                            current_indicators=current_indicators,
                            message=f"ML signal {ml_direction} blocked: opposite rule '{result.rule_id}' is satisfied"
                        )
            
            # No relevant rules and no blocking opposite rules
            return StrategyValidationResult(
                valid=True,
                matched_rules=[],
                failed_rules=[],
                details=[],
                current_indicators=current_indicators,
                message=f"No {ml_direction} rules defined - allowing trade"
            )
        
        # Evaluate relevant rules
        any_rule_satisfied = False
        
        for rule in relevant_rules:
            result = self._evaluate_single_rule(rule, market_data)
            details.append(result)
            
            if result.is_satisfied:
                matched_rules.append(result.rule_id)
                any_rule_satisfied = True
            else:
                failed_rules.append(result.rule_id)
        
        # Strategy is valid if at least one rule for the direction is satisfied
        valid = any_rule_satisfied
        
        if valid:
            message = f"Strategy validated: {len(matched_rules)} rule(s) matched for {ml_direction}"
        else:
            message = f"Strategy blocked: no {ml_direction} rules satisfied. Failed: {failed_rules}"
        
        return StrategyValidationResult(
            valid=valid,
            matched_rules=matched_rules,
            failed_rules=failed_rules,
            details=details,
            current_indicators=current_indicators,
            message=message
        )
    
    def evaluate_exit_rules(
        self,
        rules: List[Dict[str, Any]],
        market_data: pd.DataFrame,
        position_direction: str,
        entry_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> StrategyValidationResult:
        """
        Evaluate exit rules to determine if position should be closed.
        
        Args:
            rules: List of strategy exit rules
            market_data: DataFrame with OHLCV and indicators
            position_direction: Current position direction ("BUY" or "SELL")
            entry_price: Position entry price
            stop_loss: Stop loss price (if set)
            take_profit: Take profit price (if set)
            
        Returns:
            StrategyValidationResult indicating if exit is triggered
        """
        if not rules:
            return StrategyValidationResult(
                valid=False,  # Don't exit if no rules
                matched_rules=[],
                failed_rules=[],
                details=[],
                current_indicators={},
                message="No exit rules defined"
            )
        
        self._indicator_cache = {}
        current_indicators = self._get_current_indicators(market_data)
        current_price = current_indicators.get("close", 0)
        
        matched_rules = []
        failed_rules = []
        details = []
        
        for rule in rules:
            condition = rule.get("condition", "").lower()
            
            # Handle special exit conditions
            if "hit_stop_loss" in condition and stop_loss:
                is_hit = (
                    (position_direction == "BUY" and current_price <= stop_loss) or
                    (position_direction == "SELL" and current_price >= stop_loss)
                )
                result = RuleEvaluationResult(
                    rule_id=rule.get("id", "sl_check"),
                    condition="hit_stop_loss",
                    action="CLOSE",
                    is_satisfied=is_hit,
                    indicator_values={"current_price": current_price, "stop_loss": stop_loss}
                )
                details.append(result)
                if is_hit:
                    matched_rules.append(result.rule_id)
                continue
            
            if "hit_take_profit" in condition and take_profit:
                is_hit = (
                    (position_direction == "BUY" and current_price >= take_profit) or
                    (position_direction == "SELL" and current_price <= take_profit)
                )
                result = RuleEvaluationResult(
                    rule_id=rule.get("id", "tp_check"),
                    condition="hit_take_profit",
                    action="CLOSE",
                    is_satisfied=is_hit,
                    indicator_values={"current_price": current_price, "take_profit": take_profit}
                )
                details.append(result)
                if is_hit:
                    matched_rules.append(result.rule_id)
                continue
            
            # Evaluate regular indicator-based exit rules
            result = self._evaluate_single_rule(rule, market_data)
            details.append(result)
            
            if result.is_satisfied:
                matched_rules.append(result.rule_id)
            else:
                failed_rules.append(result.rule_id)
        
        # Exit is triggered if any exit rule is satisfied
        should_exit = len(matched_rules) > 0
        
        return StrategyValidationResult(
            valid=should_exit,
            matched_rules=matched_rules,
            failed_rules=failed_rules,
            details=details,
            current_indicators=current_indicators,
            message=f"Exit triggered by: {matched_rules}" if should_exit else "No exit conditions met"
        )
    
    def _evaluate_single_rule(
        self,
        rule: Dict[str, Any],
        market_data: pd.DataFrame
    ) -> RuleEvaluationResult:
        """Evaluate a single strategy rule."""
        rule_id = rule.get("id", "unknown")
        condition = rule.get("condition", "")
        action = rule.get("action", "")
        
        if not condition:
            return RuleEvaluationResult(
                rule_id=rule_id,
                condition=condition,
                action=action,
                is_satisfied=False,
                indicator_values={},
                error="Empty condition"
            )
        
        try:
            is_satisfied, indicator_values = self._evaluate_condition(condition, market_data)
            return RuleEvaluationResult(
                rule_id=rule_id,
                condition=condition,
                action=action,
                is_satisfied=is_satisfied,
                indicator_values=indicator_values
            )
        except Exception as e:
            logger.error(f"Error evaluating rule {rule_id}: {e}")
            return RuleEvaluationResult(
                rule_id=rule_id,
                condition=condition,
                action=action,
                is_satisfied=False,
                indicator_values={},
                error=str(e)
            )
    
    def _evaluate_condition(
        self,
        condition: str,
        market_data: pd.DataFrame
    ) -> Tuple[bool, Dict[str, float]]:
        """
        Parse and evaluate a condition string.
        
        Supports:
        - Simple: "RSI < 30"
        - Compound AND: "RSI < 30 AND EMA(9) > EMA(21)"
        - Compound OR: "MACD > 0 OR RSI < 30"
        - Mixed: "RSI < 30 AND (MACD > 0 OR ADX > 25)"
        """
        indicator_values = {}
        
        # Normalize condition
        condition = condition.strip()
        
        # Handle OR conditions (lower precedence)
        if ' OR ' in condition.upper():
            parts = re.split(r'\s+OR\s+', condition, flags=re.IGNORECASE)
            for part in parts:
                result, values = self._evaluate_condition(part.strip(), market_data)
                indicator_values.update(values)
                if result:  # OR: return True if any part is True
                    return True, indicator_values
            return False, indicator_values
        
        # Handle AND conditions
        if ' AND ' in condition.upper():
            parts = re.split(r'\s+AND\s+', condition, flags=re.IGNORECASE)
            all_true = True
            for part in parts:
                result, values = self._evaluate_condition(part.strip(), market_data)
                indicator_values.update(values)
                if not result:  # AND: return False if any part is False
                    all_true = False
            return all_true, indicator_values
        
        # Single comparison
        return self._evaluate_comparison(condition, market_data, indicator_values)
    
    def _evaluate_comparison(
        self,
        condition: str,
        market_data: pd.DataFrame,
        indicator_values: Dict[str, float]
    ) -> Tuple[bool, Dict[str, float]]:
        """Evaluate a single comparison like 'RSI < 30' or 'EMA(9) > EMA(21)'."""
        
        # Remove parentheses if wrapping entire condition
        condition = condition.strip('()')
        
        # Match comparison pattern
        match = self.COMPARISON_PATTERN.match(condition)
        if not match:
            logger.warning(f"Could not parse condition: {condition}")
            return False, indicator_values
        
        left_operand = match.group(1)
        operator = match.group(2)
        right_operand = match.group(3)
        
        # Get left value
        left_value = self._get_operand_value(left_operand, market_data)
        indicator_values[left_operand] = left_value
        
        # Get right value (could be number or indicator)
        try:
            right_value = float(right_operand)
        except ValueError:
            right_value = self._get_operand_value(right_operand, market_data)
            indicator_values[right_operand] = right_value
        
        # Evaluate comparison
        if left_value is None or right_value is None:
            return False, indicator_values
        
        result = self._compare(left_value, operator, right_value)
        
        logger.debug(f"Evaluated: {left_operand}({left_value}) {operator} {right_operand}({right_value}) = {result}")
        
        return result, indicator_values
    
    def _get_operand_value(self, operand: str, market_data: pd.DataFrame) -> Optional[float]:
        """Get the current value of an operand (indicator or price)."""
        
        # Check cache
        if operand in self._indicator_cache:
            return self._indicator_cache[operand]
        
        # Parse indicator name and period
        match = self.INDICATOR_PATTERN.match(operand)
        if not match:
            return None
        
        indicator_name = match.group(1).lower()
        period = int(match.group(2)) if match.group(2) else None
        
        # Get column name
        column_getter = self.INDICATOR_COLUMN_MAP.get(indicator_name)
        if not column_getter:
            logger.warning(f"Unknown indicator: {indicator_name}")
            return None
        
        try:
            if period is not None:
                column_name = column_getter(period)
            else:
                column_name = column_getter()
        except TypeError:
            # Indicator doesn't take period parameter
            column_name = column_getter()
        
        # Get value from DataFrame
        if column_name not in market_data.columns:
            logger.warning(f"Column {column_name} not found in market data")
            return None
        
        value = float(market_data[column_name].iloc[-1])
        
        # Handle NaN
        if pd.isna(value):
            return None
        
        # Cache the value
        self._indicator_cache[operand] = value
        
        return value
    
    def _compare(self, left: float, operator: str, right: float) -> bool:
        """Perform comparison operation."""
        operators = {
            '<': lambda a, b: a < b,
            '<=': lambda a, b: a <= b,
            '>': lambda a, b: a > b,
            '>=': lambda a, b: a >= b,
            '==': lambda a, b: abs(a - b) < 0.0001,  # Float comparison with tolerance
            '!=': lambda a, b: abs(a - b) >= 0.0001,
            '=': lambda a, b: abs(a - b) < 0.0001,
        }
        
        compare_func = operators.get(operator)
        if not compare_func:
            logger.warning(f"Unknown operator: {operator}")
            return False
        
        return compare_func(left, right)
    
    def _get_current_indicators(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Get current values of common indicators for logging/display."""
        indicators = {}
        
        common_indicators = [
            ('close', 'price'),
            ('rsi_14', 'RSI(14)'),
            ('ema_9', 'EMA(9)'),
            ('ema_21', 'EMA(21)'),
            ('sma_20', 'SMA(20)'),
            ('sma_50', 'SMA(50)'),
            ('macd', 'MACD'),
            ('macd_signal', 'MACD_Signal'),
            ('adx', 'ADX'),
            ('atr', 'ATR'),
            ('cci', 'CCI'),
            ('bb_upper', 'BB_Upper'),
            ('bb_lower', 'BB_Lower'),
            ('stoch_k', 'Stoch_K'),
        ]
        
        for col, name in common_indicators:
            if col in market_data.columns:
                value = market_data[col].iloc[-1]
                if not pd.isna(value):
                    indicators[name] = round(float(value), 5)
        
        return indicators


# Convenience function
def evaluate_strategy_rules(
    entry_rules: List[Dict],
    market_data: pd.DataFrame,
    ml_direction: str
) -> StrategyValidationResult:
    """Evaluate strategy rules against market data."""
    engine = StrategyRuleEngine()
    return engine.evaluate_entry_rules(entry_rules, market_data, ml_direction)
