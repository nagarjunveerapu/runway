"""Parser for messy bank statement text files.

Reads lines and emits transaction dictionaries with raw_remark, amount (best-effort), channel hints, merchant_raw.
"""
from typing import List, Dict, Any
import re
import logging
from .utils import extract_amount_from_text, detect_date, gen_uuid

logger = logging.getLogger(__name__)


CHANNEL_KEYWORDS = {
    'UPI': ['upi', '@', 'paytm', 'googlepay', 'gpay'],
    'NEFT': ['neft'],
    'IMPS': ['imps', 'imps/'],
    'ACH': ['ach'],
    'BIL': ['bill', 'bil', 'emi', 'loan'],
    'MMT': ['mmt'],
    'NFS': ['nfs', 'cash wdl', 'cashwdl'],
    'INF': ['inf'],
}


def detect_channel(text: str) -> str:
    if not text:
        return 'OTHER'
    t = text.lower()
    for ch, kws in CHANNEL_KEYWORDS.items():
        for kw in kws:
            if kw in t:
                return ch
    # default heuristics
    if 'upi' in t or '@' in t:
        return 'UPI'
    return 'OTHER'


def extract_merchant_raw(text: str) -> str:
    """A heuristic to extract merchant-like substrings: words after known channel tokens or before numeric amounts."""
    if not text:
        return ''
    # remove trailing amount-like token
    s = re.sub(r"[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?$", '', text).strip()
    # if contains '/', take parts and prefer middle segments
    parts = re.split(r"[\/\-|]{1}", s)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return s

    # For UPI transactions, the merchant is usually the second part (after "UPI/")
    # e.g., "UPI/Zepto/..." -> Zepto is the merchant
    if len(parts) > 1 and parts[0].upper() == 'UPI':
        # Return the second part if it looks like a merchant name
        second_part = parts[1]
        if re.search('[A-Za-z]', second_part) and not re.search(r'[@]|^\d{5,}', second_part):
            return second_part

    # heuristics: choose parts with letters, prefer parts that look like business names
    # Avoid parts that look like transaction IDs (e.g., contain @ or are mostly numbers)
    parts_alpha = [p for p in parts if re.search('[A-Za-z]', p)]
    if parts_alpha:
        # Filter out parts that look like transaction IDs or account handles
        merchant_like = [p for p in parts_alpha if not re.search(r'[@]|^\w*\d{5,}', p)]
        if merchant_like:
            return max(merchant_like, key=len)
        return max(parts_alpha, key=len)
    return parts[0]


def parse_line(line: str) -> Dict[str, Any]:
    raw = line.strip()
    amount, note = extract_amount_from_text(raw)
    channel = detect_channel(raw)
    merchant_raw = extract_merchant_raw(raw)
    date = detect_date(raw)
    tx = {
        'id': gen_uuid(),
        'raw_remark': raw,
        'remark': raw,
        'amount': float(amount),
        'channel': channel,
        'merchant_raw': merchant_raw,
        'merchant': None,
        'category': None,
        'date': date,
        'recurring': False,
        'recurrence_count': 0,
        'notes': note,
    }
    return tx


def parse_file(path: str) -> List[Dict[str, Any]]:
    with open(path, 'r', encoding='utf-8') as f:
        lines = [l.rstrip('\n') for l in f if l.strip()]
    return parse_lines(lines)


def parse_lines(lines: List[str]) -> List[Dict[str, Any]]:
    txs = []
    for l in lines:
        try:
            tx = parse_line(l)
            txs.append(tx)
        except Exception as e:
            logger.exception('Failed to parse line: %s', l)
    return txs
