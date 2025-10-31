"""
Credit Card Parser Package

Provides parsers for credit card statements from various banks.
Uses factory pattern for bank-specific parsing logic.
"""

from ingestion.credit_card.base_credit_card_parser import BaseCreditCardParser
from ingestion.credit_card.icici_credit_card_parser import ICICICreditCardParser

__all__ = ['BaseCreditCardParser', 'ICICICreditCardParser']

