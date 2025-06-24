# utils/formatting.py
"""
Formatting utilities for text and numbers
"""

from typing import Union, Optional


def format_currency(value: Union[int, float], decimals: int = 0) -> str:
    """
    Format number as currency

    Args:
        value: Numeric value
        decimals: Number of decimal places

    Returns:
        Formatted currency string
    """
    if decimals == 0:
        return f"${value:,.0f}"
    else:
        return f"${value:,.{decimals}f}"


def format_percentage(value: Union[int, float], decimals: int = 0) -> str:
    """
    Format number as percentage

    Args:
        value: Numeric value (0-100 or 0-1)
        decimals: Number of decimal places

    Returns:
        Formatted percentage string
    """
    # Convert to percentage if needed
    if 0 <= value <= 1:
        value = value * 100

    if decimals == 0:
        return f"{value:.0f}%"
    else:
        return f"{value:.{decimals}f}%"


def format_number(value: Union[int, float], decimals: int = 0) -> str:
    """
    Format number with thousands separator

    Args:
        value: Numeric value
        decimals: Number of decimal places

    Returns:
        Formatted number string
    """
    if decimals == 0:
        return f"{value:,.0f}"
    else:
        return f"{value:,.{decimals}f}"


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def format_merchant_name(merchant: str) -> str:
    """
    Format merchant name for display

    Args:
        merchant: Raw merchant name

    Returns:
        Formatted merchant name
    """
    # Basic formatting - can be enhanced
    return merchant.strip().title()


def wrap_text_for_slide(text: str, max_line_length: int = 50) -> str:
    """
    Wrap text for slide display

    Args:
        text: Text to wrap
        max_line_length: Maximum characters per line

    Returns:
        Wrapped text with newlines
    """
    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        if current_length + len(word) + 1 > max_line_length:
            lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)
        else:
            current_line.append(word)
            current_length += len(word) + 1

    if current_line:
        lines.append(' '.join(current_line))

    return '\n'.join(lines)