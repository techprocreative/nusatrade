"""Input validation and sanitization utilities.

This module provides security-focused validation functions to prevent:
- Path traversal attacks
- SQL injection
- XSS attacks
- Invalid data formats
"""

import re
import uuid
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, status


class ValidationError(HTTPException):
    """Custom validation error exception."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


def validate_uuid(value: str, field_name: str = "id") -> uuid.UUID:
    """
    Validate and convert string to UUID.

    Args:
        value: String to validate as UUID
        field_name: Name of the field for error messages

    Returns:
        uuid.UUID object

    Raises:
        ValidationError: If value is not a valid UUID
    """
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError(f"Invalid {field_name} format. Must be a valid UUID.")


def validate_symbol(symbol: str) -> str:
    """
    Validate trading symbol format.

    Args:
        symbol: Trading symbol to validate

    Returns:
        Validated symbol in uppercase

    Raises:
        ValidationError: If symbol format is invalid
    """
    if not symbol or not isinstance(symbol, str):
        raise ValidationError("Symbol is required and must be a string")

    # Remove whitespace and convert to uppercase
    symbol = symbol.strip().upper()

    # Validate format: 6-10 alphanumeric characters (e.g., EURUSD, XAUUSD)
    if not re.match(r'^[A-Z0-9]{3,10}$', symbol):
        raise ValidationError(
            "Invalid symbol format. Must be 3-10 alphanumeric characters (e.g., EURUSD, XAUUSD)"
        )

    return symbol


def sanitize_model_path(
    model_id: str,
    base_dir: str = "models",
    extension: str = ".pkl"
) -> Path:
    """
    Sanitize and validate ML model file path to prevent path traversal attacks.

    Args:
        model_id: UUID of the model
        base_dir: Base directory for models (default: "models")
        extension: File extension (default: ".pkl")

    Returns:
        Validated Path object

    Raises:
        ValidationError: If path is invalid or unsafe

    Example:
        >>> sanitize_model_path("123e4567-e89b-12d3-a456-426614174000")
        PosixPath('models/123e4567-e89b-12d3-a456-426614174000.pkl')
    """
    # Validate model_id is a valid UUID
    model_uuid = validate_uuid(model_id, "model_id")

    # Construct safe path
    base_path = Path(base_dir).resolve()
    file_name = f"{model_uuid}{extension}"
    model_path = (base_path / file_name).resolve()

    # Ensure path is within base directory (prevent directory traversal)
    try:
        model_path.relative_to(base_path)
    except ValueError:
        raise ValidationError(
            "Invalid model path. Path traversal detected."
        )

    # Ensure base directory exists
    base_path.mkdir(parents=True, exist_ok=True)

    return model_path


def validate_file_size(file_path: Path, max_size_mb: int = 100) -> bool:
    """
    Validate file size.

    Args:
        file_path: Path to file
        max_size_mb: Maximum file size in MB

    Returns:
        True if file size is valid

    Raises:
        ValidationError: If file is too large
    """
    if file_path.exists():
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            raise ValidationError(
                f"File size ({size_mb:.2f}MB) exceeds maximum allowed size ({max_size_mb}MB)"
            )

    return True


def validate_lot_size(lot_size: float, min_lot: float = 0.01, max_lot: float = 100.0) -> float:
    """
    Validate trading lot size.

    Args:
        lot_size: Lot size to validate
        min_lot: Minimum allowed lot size
        max_lot: Maximum allowed lot size

    Returns:
        Validated lot size

    Raises:
        ValidationError: If lot size is invalid
    """
    try:
        lot_size = float(lot_size)
    except (ValueError, TypeError):
        raise ValidationError("Lot size must be a number")

    if lot_size < min_lot:
        raise ValidationError(f"Lot size must be at least {min_lot}")

    if lot_size > max_lot:
        raise ValidationError(f"Lot size cannot exceed {max_lot}")

    # Validate step size (0.01 increments)
    if round(lot_size, 2) != lot_size:
        raise ValidationError("Lot size must be in 0.01 increments")

    return lot_size


def validate_price(price: float, symbol: str) -> float:
    """
    Validate trading price.

    Args:
        price: Price to validate
        symbol: Trading symbol

    Returns:
        Validated price

    Raises:
        ValidationError: If price is invalid
    """
    try:
        price = float(price)
    except (ValueError, TypeError):
        raise ValidationError("Price must be a number")

    if price <= 0:
        raise ValidationError("Price must be positive")

    # Validate reasonable price range based on symbol
    if symbol.endswith("JPY"):
        # JPY pairs typically trade in 100-150 range
        if price < 50 or price > 200:
            raise ValidationError(f"Price {price} is outside reasonable range for {symbol}")
    elif "XAU" in symbol or "GOLD" in symbol:
        # Gold typically trades in 1000-3000 range
        if price < 500 or price > 5000:
            raise ValidationError(f"Price {price} is outside reasonable range for {symbol}")
    else:
        # Other pairs typically trade in 0.5-2.0 range
        if price < 0.1 or price > 10.0:
            raise ValidationError(f"Price {price} is outside reasonable range for {symbol}")

    return price


def validate_sl_tp(
    stop_loss: Optional[float],
    take_profit: Optional[float],
    entry_price: float,
    order_type: str
) -> tuple[Optional[float], Optional[float]]:
    """
    Validate stop loss and take profit levels.

    Args:
        stop_loss: Stop loss price
        take_profit: Take profit price
        entry_price: Entry price
        order_type: "BUY" or "SELL"

    Returns:
        Tuple of (validated_sl, validated_tp)

    Raises:
        ValidationError: If SL/TP levels are invalid
    """
    order_type = order_type.upper()

    if stop_loss is not None:
        try:
            stop_loss = float(stop_loss)
        except (ValueError, TypeError):
            raise ValidationError("Stop loss must be a number")

        if stop_loss <= 0:
            raise ValidationError("Stop loss must be positive")

        # Validate SL is on correct side of entry
        if order_type == "BUY" and stop_loss >= entry_price:
            raise ValidationError("Stop loss for BUY order must be below entry price")
        elif order_type == "SELL" and stop_loss <= entry_price:
            raise ValidationError("Stop loss for SELL order must be above entry price")

    if take_profit is not None:
        try:
            take_profit = float(take_profit)
        except (ValueError, TypeError):
            raise ValidationError("Take profit must be a number")

        if take_profit <= 0:
            raise ValidationError("Take profit must be positive")

        # Validate TP is on correct side of entry
        if order_type == "BUY" and take_profit <= entry_price:
            raise ValidationError("Take profit for BUY order must be above entry price")
        elif order_type == "SELL" and take_profit >= entry_price:
            raise ValidationError("Take profit for SELL order must be below entry price")

    return stop_loss, take_profit


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename to prevent directory traversal and invalid characters.

    Args:
        filename: Filename to sanitize
        max_length: Maximum filename length

    Returns:
        Sanitized filename

    Raises:
        ValidationError: If filename is invalid
    """
    if not filename or not isinstance(filename, str):
        raise ValidationError("Filename is required and must be a string")

    # Remove any path separators
    filename = filename.replace("/", "_").replace("\\", "_")

    # Remove null bytes
    filename = filename.replace("\x00", "")

    # Allow only alphanumeric, dash, underscore, and dot
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

    # Remove leading dots (hidden files on Unix)
    filename = filename.lstrip(".")

    # Limit length
    if len(filename) > max_length:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:max_length - len(ext) - 1] + "." + ext if ext else name[:max_length]

    if not filename:
        raise ValidationError("Filename contains only invalid characters")

    return filename


def validate_json_field(data: dict, allowed_keys: set) -> dict:
    """
    Validate JSON field contains only allowed keys.

    Args:
        data: Dictionary to validate
        allowed_keys: Set of allowed keys

    Returns:
        Validated dictionary

    Raises:
        ValidationError: If unknown keys are present
    """
    if not isinstance(data, dict):
        raise ValidationError("Data must be a dictionary")

    unknown_keys = set(data.keys()) - allowed_keys
    if unknown_keys:
        raise ValidationError(
            f"Unknown fields in data: {', '.join(unknown_keys)}"
        )

    return data


def validate_date_range(start_date: str, end_date: str) -> tuple[str, str]:
    """
    Validate date range format and logic.

    Args:
        start_date: Start date in ISO format
        end_date: End date in ISO format

    Returns:
        Tuple of (validated_start_date, validated_end_date)

    Raises:
        ValidationError: If dates are invalid
    """
    from datetime import datetime, timedelta

    try:
        start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise ValidationError("Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")

    # Validate end date is after start date
    if end <= start:
        raise ValidationError("End date must be after start date")

    # Validate range is not too large (max 2 years)
    if (end - start).days > 730:
        raise ValidationError("Date range cannot exceed 2 years")

    return start_date, end_date
