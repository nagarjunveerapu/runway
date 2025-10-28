"""
Centralized Date Parser Utility

This module provides consistent date parsing across the entire application.
All date formats are normalized to ISO format (YYYY-MM-DD) for storage
and YYYY-MM for month fields.
"""

import logging
from datetime import datetime
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Supported date formats
DATE_FORMATS = [
    '%Y-%m-%d',      # ISO format: 2025-01-15
    '%d/%m/%Y',      # DD/MM/YYYY: 15/01/2025
    '%d-%m-%Y',      # DD-MM-YYYY: 15-01-2025
    '%m/%d/%Y',      # MM/DD/YYYY: 01/15/2025
    '%Y/%m/%d',      # YYYY/MM/DD: 2025/01/15
]


def parse_date(date_str: Optional[str]) -> Optional[str]:
    """
    Parse any date format to ISO format (YYYY-MM-DD)
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        ISO format date string (YYYY-MM-DD) or None if parsing fails
        
    Examples:
        >>> parse_date("15/01/2025")
        '2025-01-15'
        >>> parse_date("2025-01-15")
        '2025-01-15'
        >>> parse_date("01/15/2025")
        '2025-01-15'
    """
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # Already in ISO format?
    if date_str.startswith('20') and len(date_str) >= 10 and date_str[4] == '-' and date_str[7] == '-':
        return date_str[:10]
    
    # Try standard formats
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except (ValueError, AttributeError):
            continue
    
    # Fallback: Try to parse DD/MM/YYYY or DD/MM/YY manually
    if '/' in date_str:
        parts = date_str.split('/')
        if len(parts) >= 3:
            try:
                day = parts[0].zfill(2)
                month = parts[1].zfill(2)
                year = _fix_year(parts[2])
                return f"{year}-{month}-{day}"
            except Exception as e:
                logger.warning(f"Failed to parse date {date_str}: {e}")
    
    # Try DD-MM-YYYY
    if '-' in date_str and '/' not in date_str and len(date_str) >= 8:
        parts = date_str.split('-')
        if len(parts) == 3:
            try:
                if len(parts[0]) == 2 and len(parts[1]) == 2:
                    # Likely DD-MM-YYYY
                    day, month, year = parts[0], parts[1], _fix_year(parts[2])
                    return f"{year}-{month}-{day}"
            except Exception as e:
                logger.warning(f"Failed to parse DD-MM-YYYY date {date_str}: {e}")
    
    logger.warning(f"Could not parse date: {date_str}")
    return None


def parse_month_from_date(date_str: Optional[str]) -> str:
    """
    Parse month from any date format to YYYY-MM format
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        Month string in YYYY-MM format or empty string
        
    Examples:
        >>> parse_month_from_date("15/01/2025")
        '2025-01'
        >>> parse_month_from_date("2025-01-15")
        '2025-01'
        >>> parse_month_from_date("01/15/2025")
        '2025-01'
    """
    if not date_str:
        return ""
    
    date_str = str(date_str).strip()
    
    # Already in YYYY-MM format?
    if date_str.startswith('20') and len(date_str) >= 7 and date_str[4] == '-' and date_str[6] != '-':
        return date_str[:7]
    
    # Try to parse as full date first
    parsed_date = parse_date(date_str)
    if parsed_date:
        return parsed_date[:7]  # Return YYYY-MM
    
    return ""


def _fix_year(year_str: str) -> str:
    """
    Fix year string to 4-digit format
    
    Args:
        year_str: Year string (1, 2, or 4 digits)
        
    Returns:
        4-digit year string
        
    Examples:
        >>> _fix_year("25")
        '2025'
        >>> _fix_year("2")
        '2025'
        >>> _fix_year("2025")
        '2025'
    """
    year_str = year_str.strip()
    
    if len(year_str) == 1:
        # Single digit: assume current decade (e.g., "2" -> "2025")
        return '2025'
    elif len(year_str) == 2:
        # Two digits: add 20 prefix
        year = '20' + year_str
        # If year seems too old, assume 2025+
        if int(year) < 2024:
            return '2025'
        return year
    elif len(year_str) == 4:
        return year_str
    
    return '2025'  # Default fallback


def format_month_for_display(month_str: Optional[str]) -> str:
    """
    Format month string for display (YYYY-MM -> "Month YYYY")
    
    Args:
        month_str: Month in YYYY-MM format
        
    Returns:
        Formatted string like "January 2025"
    """
    if not month_str or len(month_str) < 7:
        return ""
    
    try:
        year, month = month_str[:7].split('-')
        dt = datetime(int(year), int(month), 1)
        return dt.strftime('%B %Y')
    except:
        return month_str


def get_current_month() -> str:
    """
    Get current month in YYYY-MM format
    
    Returns:
        Current month as YYYY-MM
    """
    return datetime.now().strftime('%Y-%m')


def is_valid_month(month_str: Optional[str]) -> bool:
    """
    Check if month string is in valid YYYY-MM format
    
    Args:
        month_str: Month string to validate
        
    Returns:
        True if valid YYYY-MM format
    """
    if not month_str or len(month_str) < 7:
        return False
    
    try:
        year, month = month_str[:7].split('-')
        if len(year) == 4 and len(month) == 2:
            y = int(year)
            m = int(month)
            if 2000 <= y <= 2100 and 1 <= m <= 12:
                return True
    except:
        pass
    
    return False

