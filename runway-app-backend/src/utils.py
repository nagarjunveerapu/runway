"""Utility helpers for parsing and normalization."""
from typing import Optional, Tuple
import re
import uuid
import logging

logger = logging.getLogger(__name__)


def gen_uuid() -> str:
    return str(uuid.uuid4())


def extract_amount_from_text(text: str) -> Tuple[float, str]:
    """Extract the right-most, highest-precision numeric token as amount.

    Returns (amount, notes)
    """
    if not text or not text.strip():
        return 0.0, "empty line"
    # find numeric tokens (with commas and decimals)
    tokens = re.findall(r"[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?", text)
    if not tokens:
        return 0.0, "no numeric token found"
    # prefer right-most token with decimals, else highest precision
    tokens_sorted = sorted(tokens, key=lambda t: ('.' in t, len(t)), reverse=True)
    # try right-most among tokens with decimals
    rightmost = None
    for t in reversed(tokens):
        if '.' in t:
            rightmost = t
            break
    chosen = rightmost or tokens_sorted[0]
    # normalize commas
    try:
        amount = float(chosen.replace(',', ''))
        return amount, f"amount parsed from token '{chosen}'"
    except Exception as e:
        logger.warning("Failed to parse amount '%s': %s", chosen, e)
        return 0.0, f"failed to parse amount token '{chosen}'"


def detect_date(text: str) -> Optional[str]:
    """Try to find simple date patterns (DDMMYYYY, DDMMYY, DD/MM/YY, MMM YYYY) -> return as string or None.

    This is a lightweight heuristic for POC.
    """
    if not text:
        return None
    # simple day-month-year or ddmmyy
    m = re.search(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text)
    if m:
        return m.group(1)
    m2 = re.search(r"\b(0[1-9]|[12][0-9]|3[01])[ ]?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[ ]?\d{2,4}\b", text, re.I)
    if m2:
        return m2.group(0)
    return None
