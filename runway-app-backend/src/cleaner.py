"""Cleaning utilities for transaction remarks."""
from typing import Dict
import re


def clean_remark(raw: str) -> str:
    """Return a cleaned, lower-cased remark suitable for matching and classification."""
    if raw is None:
        return ''
    s = raw
    # normalize whitespace and separators
    s = re.sub(r"[\t\n\r]+", ' ', s)
    s = re.sub(r"[\/\|_]+", ' ', s)
    s = re.sub(r"\s+", ' ', s)
    s = s.strip()
    return s


def enrich_transaction(tx: Dict) -> Dict:
    tx = dict(tx)
    tx['remark'] = clean_remark(tx.get('raw_remark', ''))
    # other cleaning steps could go here
    return tx
