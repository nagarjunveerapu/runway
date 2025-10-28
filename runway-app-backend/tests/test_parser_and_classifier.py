import pytest
from src import parser, merchant_normalizer, classifier


SAMPLE_LINES = [
    "UPI/518203569642/DHBHDBFS20261/ipo.hdbfsbse@ko/Kotak Mahindra    22940.00",
    "APY_500118843752_Rs.529 fr 072025    529.00",
    "UPI/Apollo Dia/Q19628802@axl/...    499.00",
    "NFS/CASH WDL/518716016430/...    10000.00",
    "BIL/Personal Loan XX15583 EMI V Na    65328.00",
]


def test_parse_count_and_amounts():
    txs = parser.parse_lines(SAMPLE_LINES)
    assert len(txs) == 5
    # amounts
    amounts = sorted([t['amount'] for t in txs])
    assert 499.0 in amounts
    assert 10000.0 in amounts


def test_channel_detection():
    txs = parser.parse_lines(SAMPLE_LINES)
    ch_map = {t['raw_remark']: t['channel'] for t in txs}
    assert any('UPI' == v for v in ch_map.values())
    assert any('NFS' == v for v in ch_map.values())


def test_merchant_and_category():
    norm = merchant_normalizer.MerchantNormalizer()
    parsed = parser.parse_lines([SAMPLE_LINES[2]])[0]
    merchant, score = norm.normalize(parsed['merchant_raw'])
    assert merchant == "Apollo Pharmacy"
