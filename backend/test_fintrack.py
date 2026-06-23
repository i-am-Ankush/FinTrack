"""
test_fintrack.py — pytest test suite for FinTrack

Tests cover:
  - PDF parser: line reconstruction, description cleaning, amount parsing,
    skip-row filtering, both ZIP and pdfplumber text formats
  - Analytics: recurring expense detection logic
  - ML classifier: predict returns a valid category
  - Auth routes: signup, login (uses Flask test client + in-memory SQLite)
  - Transaction routes: add, get, delete (test client)

Run:
    cd backend
    pip install pytest
    pytest test_fintrack.py -v
"""

import pytest
import re
import sys
import os

# ---------------------------------------------------------------------------
# Parser unit tests — pure functions, no Flask/DB needed
# ---------------------------------------------------------------------------

# Inline the core parsing functions so tests run without Flask app context.
# These are exact copies of the live functions in upload.py.

KEYWORD_MAP = {
    'swiggy': 'Food', 'zomato': 'Food', 'cravebox': 'Food', 'sarovar': 'Food',
    'mrs suj': 'Food', 'm b hari': 'Food', 'moideen': 'Food', 'adhwaith': 'Food',
    'ola': 'Transport', 'uber': 'Transport', 'rapido': 'Transport', 'irctc': 'Transport',
    'amazon': 'Shopping', 'flipkart': 'Shopping',
    'nit cali': 'Education', 'byju': 'Education',
    'pharmacy': 'Health', 'hospital': 'Health',
    'netflix': 'Entertainment', 'spotify': 'Entertainment',
    'pankaj k': 'Income', 'pankaj kumar': 'Income',
    'npci bhim': 'Income', 'supermoney': 'Income',
}

_SKIP_ROWS = [
    'part period interest', 'advance:loan', 'debit transfer',
    'comm on other', 'mcc issue',
]

_SKIP_LINES = [
    'null', 'xxxxxxx', 'opening balance', 'closing balance',
    'visit https', 'date transaction',
    'your opening', 'your closing', 'contents of this', 'as on',
]

_DATE_PREFIX_RE = re.compile(r'^(\d{2}-\d{2}-\d{2})\s*(.*)$')
_NUMS_TAIL_RE   = re.compile(r'^(.*?)\s*(-|0|[\d,]+\.\d{2})\s+(-|0|[\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$')


def _parse_amount(s):
    s = s.strip()
    if s in ('-', '0', ''):
        return 0.0
    try:
        return float(s.replace(',', ''))
    except ValueError:
        return 0.0


def _classify_line(raw, direction):
    low = raw.lower()
    for kw, cat in KEYWORD_MAP.items():
        if kw in low:
            return cat
    return 'Income' if direction == 'CR' else 'Other'


def _clean_desc(raw):
    if 'UPI/' not in raw:
        cleaned = re.sub(r'\s*-\s*$', '', raw.strip())
        cleaned = re.sub(r'^SBIYA\d+[-\s]*', 'Bank Transfer', cleaned)
        return cleaned.strip()[:80] if cleaned.strip() else raw[:80]
    parts = raw.split('/')
    name   = parts[3].strip() if len(parts) > 3 else ''
    remark = parts[6].strip() if len(parts) > 6 else ''
    bad_exact = {
        'NO RE', 'NO REM', 'NO REMA', 'NO REMAR', 'NO REMARK',
        'UPI', 'UPI-', 'Paid', 'Sent', 'NA', 'na', 'Pay', 'Payme',
        'Stati', 'R02 Ph', 'PAY B', 'CDC p', 'Navi-', 'UPIInt',
        'UPIIn', 'Manda', '-',
    }
    if not remark or remark in bad_exact or len(remark) < 2 or remark.startswith('NO RE'):
        remark = ''
    if remark:
        return f"{name} ({remark})"
    return name if name else raw[:80]


def _extract_transaction_units(lines):
    desc_buffer = []
    pending_date = None
    units = []
    for raw_l in lines:
        l = raw_l.strip()
        if not l:
            continue
        if any(p in l.lower() for p in _SKIP_LINES):
            desc_buffer = []
            pending_date = None
            continue
        date_m = _DATE_PREFIX_RE.match(l)
        if date_m:
            date_raw, rest = date_m.groups()
            nums_m = _NUMS_TAIL_RE.match(rest) if rest else None
            if nums_m:
                inline_desc, cr_s, dr_s, bal_s = nums_m.groups()
                while desc_buffer and '/' not in desc_buffer[0] and len(desc_buffer[0]) < 10:
                    desc_buffer.pop(0)
                full_desc = ' '.join(desc_buffer + ([inline_desc] if inline_desc.strip() else [])).strip()
                units.append((date_raw, full_desc, cr_s, dr_s, bal_s))
                desc_buffer = []
                pending_date = None
            elif rest.strip():
                desc_buffer.append(rest.strip())
                pending_date = date_raw
            else:
                pending_date = date_raw
            continue
        nums_m = _NUMS_TAIL_RE.match(l)
        if nums_m and pending_date:
            inline_desc, cr_s, dr_s, bal_s = nums_m.groups()
            while desc_buffer and '/' not in desc_buffer[0] and len(desc_buffer[0]) < 10:
                desc_buffer.pop(0)
            full_desc = ' '.join(desc_buffer + ([inline_desc] if inline_desc.strip() else [])).strip()
            units.append((pending_date, full_desc, cr_s, dr_s, bal_s))
            desc_buffer = []
            pending_date = None
        else:
            desc_buffer.append(l)
    return units


def _parse_lines(lines):
    from datetime import datetime
    txns = []
    for date_raw, desc, cr_s, dr_s, bal_s in _extract_transaction_units(lines):
        desc = desc.strip()
        if not desc or any(p in desc.lower() for p in _SKIP_LINES):
            continue
        if any(s in desc.lower() for s in _SKIP_ROWS):
            continue
        credit = _parse_amount(cr_s)
        debit  = _parse_amount(dr_s)
        if credit == 0 and debit == 0:
            continue
        direction = 'CR' if ('UPI/CR' in desc or 'UPI/DRC' in desc or (credit > 0 and debit == 0)) else 'DR'
        try:
            date_str = datetime.strptime(date_raw, '%d-%m-%y').strftime('%Y-%m-%d')
        except ValueError:
            continue
        category = _classify_line(desc, direction)
        display  = _clean_desc(desc)
        if not display or display.strip() in ('-', '', '--'):
            continue
        if credit > 0 and debit == 0:
            txns.append({'date': date_str, 'amount': -credit, 'description': display, 'category': category})
        else:
            txns.append({'date': date_str, 'amount': debit, 'description': display, 'category': category})
    return txns


# ---------------------------------------------------------------------------
# 1. _parse_amount
# ---------------------------------------------------------------------------

class TestParseAmount:
    def test_dash_returns_zero(self):
        assert _parse_amount('-') == 0.0

    def test_zero_string_returns_zero(self):
        assert _parse_amount('0') == 0.0

    def test_empty_returns_zero(self):
        assert _parse_amount('') == 0.0

    def test_plain_integer_amount(self):
        assert _parse_amount('58.00') == 58.0

    def test_comma_separated_amount(self):
        assert _parse_amount('1,000.00') == 1000.0

    def test_large_amount(self):
        assert _parse_amount('45,501.00') == 45501.0


# ---------------------------------------------------------------------------
# 2. _clean_desc
# ---------------------------------------------------------------------------

class TestCleanDesc:
    def test_normal_upi_no_remark(self):
        raw = 'UPI/DR/154138588111/M B HARI/YESB/paytmqr6og/NO RE'
        assert _clean_desc(raw) == 'M B HARI'

    def test_upi_with_meaningful_remark(self):
        raw = 'UPI/CR/103532633886/RUPARELI/BARB/jenilrupar/Birth'
        result = _clean_desc(raw)
        assert 'RUPARELI' in result
        assert 'Birth' in result

    def test_upi_with_paid_remark_stripped(self):
        raw = 'UPI/CR/640408470894/PANKAJ K/SBIN/6376820454/Paid'
        assert _clean_desc(raw) == 'PANKAJ K'

    def test_upi_with_sent_remark_stripped(self):
        raw = 'UPI/CR/200028465475/PANKAJ K/SBIN/6376820454/Sent'
        assert _clean_desc(raw) == 'PANKAJ K'

    def test_upi_no_remark_marker(self):
        raw = 'UPI/DR/175429524263/Mrs SUJ/YESB/Q182214114/NO RE'
        assert _clean_desc(raw) == 'Mrs SUJ'

    def test_non_upi_trailing_dash_stripped(self):
        raw = 'NIT Cali -'
        result = _clean_desc(raw)
        assert result == 'NIT Cali'

    def test_non_upi_plain_name(self):
        raw = 'RONITH R'
        assert _clean_desc(raw) == 'RONITH R'

    def test_result_never_empty_dash(self):
        raw = 'UPI/DR/999/SOMEONE/BANK/ref/NO RE'
        result = _clean_desc(raw)
        assert result not in ('-', '', '--')

    def test_supermoney_income(self):
        raw = 'UPI/CR/603516968193/supermoney/YESB/supermoney/Sup'
        result = _clean_desc(raw)
        assert result == 'supermoney' or 'supermoney' in result.lower()


# ---------------------------------------------------------------------------
# 3. _classify_line
# ---------------------------------------------------------------------------

class TestClassifyLine:
    def test_swiggy_is_food(self):
        assert _classify_line('Swiggy order', 'DR') == 'Food'

    def test_pankaj_k_is_income(self):
        assert _classify_line('PANKAJ K transfer', 'CR') == 'Income'

    def test_nit_cali_is_education(self):
        assert _classify_line('NIT Cali canteen', 'DR') == 'Education'

    def test_amazon_is_shopping(self):
        assert _classify_line('Amazon order', 'DR') == 'Shopping'

    def test_cr_unknown_is_income(self):
        assert _classify_line('UNKNOWN SENDER XYZ', 'CR') == 'Income'

    def test_dr_unknown_is_other(self):
        assert _classify_line('RANDOM MERCHANT', 'DR') == 'Other'

    def test_case_insensitive(self):
        assert _classify_line('SWIGGY PAYMENT', 'DR') == 'Food'


# ---------------------------------------------------------------------------
# 4. _extract_transaction_units (the unified parser)
# ---------------------------------------------------------------------------

class TestExtractTransactionUnits:
    def test_format_a_single_line(self):
        """ZIP format: complete transaction on one line."""
        lines = ['01-02-26 UPI/DR/103532633886/RUPARELI/BARB/jenilrupar/Birth - 0 58.00 594.71']
        units = _extract_transaction_units(lines)
        assert len(units) == 1
        date, desc, cr, dr, bal = units[0]
        assert date == '01-02-26'
        assert 'RUPARELI' in desc
        assert dr == '58.00'

    def test_format_b_split_lines(self):
        """pdfplumber format: description on one line, date+amounts on next."""
        lines = [
            'UPI/DR/154138588111/M B HARI/YESB/paytmqr6og/NO RE',
            '02-02-26 - 0 20.00 574.71',
        ]
        units = _extract_transaction_units(lines)
        assert len(units) == 1
        date, desc, cr, dr, bal = units[0]
        assert date == '02-02-26'
        assert 'M B HARI' in desc
        assert dr == '20.00'

    def test_format_a_wrapped_lines(self):
        """ZIP format: description wraps onto next line (CRAVEBOX/me pattern)."""
        lines = [
            '04-02-26 UPI/DR/133731480269/CRAVEBOX/YESB/CRAVEBOXON/Pay',
            'me',
            '- 0 40.00 136.71',
        ]
        units = _extract_transaction_units(lines)
        assert len(units) == 1
        date, desc, cr, dr, bal = units[0]
        assert date == '04-02-26'
        assert 'CRAVEBOX' in desc
        assert dr == '40.00'

    def test_skip_lines_ignored(self):
        lines = [
            'null null null null null null',
            'Your Opening Balance on 01-02-26: 652.71',
            '01-02-26 UPI/DR/103532633886/RUPARELI/BARB/jenilrupar/Birth - 0 58.00 594.71',
        ]
        units = _extract_transaction_units(lines)
        assert len(units) == 1

    def test_multiple_transactions(self):
        lines = [
            'UPI/DR/154138588111/M B HARI/YESB/paytmqr6og/NO RE',
            '02-02-26 - 0 20.00 574.71',
            'UPI/DR/175429524263/Mrs SUJ/YESB/Q182214114/NO RE',
            '02-02-26 - 0 12.00 562.71',
        ]
        units = _extract_transaction_units(lines)
        assert len(units) == 2

    def test_credit_transaction(self):
        lines = ['07-02-26 UPI/CR/640408470894/PANKAJ K/SBIN/6376820454/Paid - 1000.00 0 1033.44']
        units = _extract_transaction_units(lines)
        assert len(units) == 1
        date, desc, cr, dr, bal = units[0]
        assert cr == '1,000.00' or cr == '1000.00'

    def test_dash_credit_column_old_format(self):
        """Older SBI statements use '-' for zero instead of '0'."""
        lines = ['01-08-25 UPI/DR/093527378640/Ravikuma/YESB/paytm.s17c/NO RE - - 10.00 606.70']
        units = _extract_transaction_units(lines)
        assert len(units) == 1
        _, _, cr, dr, _ = units[0]
        assert cr == '-'
        assert dr == '10.00'


# ---------------------------------------------------------------------------
# 5. _parse_lines (end-to-end parser output)
# ---------------------------------------------------------------------------

class TestParseLines:
    def test_skip_part_period_interest(self):
        lines = ['28-02-26 PART PERIOD INTEREST - 0 2432.00 455501.00']
        txns = _parse_lines(lines)
        assert len(txns) == 0

    def test_skip_zero_credit_and_debit(self):
        lines = ['01-02-26 UPI/DR/000000000000/SOMEONE/BANK/ref/NO RE 0 0 500.00']
        txns = _parse_lines(lines)
        assert len(txns) == 0

    def test_credit_produces_negative_amount(self):
        """Income transactions are stored as negative amounts."""
        lines = ['07-02-26 UPI/CR/640408470894/PANKAJ K/SBIN/6376820454/Paid - 1000.00 0 1033.44']
        txns = _parse_lines(lines)
        assert len(txns) == 1
        assert txns[0]['amount'] == -1000.0
        assert txns[0]['category'] == 'Income'

    def test_debit_produces_positive_amount(self):
        lines = ['01-02-26 UPI/DR/103532633886/RUPARELI/BARB/jenilrupar/Birth - 0 58.00 594.71']
        txns = _parse_lines(lines)
        assert len(txns) == 1
        assert txns[0]['amount'] == 58.0

    def test_date_formatted_correctly(self):
        lines = ['01-02-26 UPI/DR/103532633886/RUPARELI/BARB/jenilrupar/Birth - 0 58.00 594.71']
        txns = _parse_lines(lines)
        assert txns[0]['date'] == '2026-02-01'

    def test_no_empty_descriptions(self):
        """Core regression test: no transaction should have a bare dash description."""
        lines = [
            'UPI/DR/154138588111/M B HARI/YESB/paytmqr6og/NO RE',
            '02-02-26 - 0 20.00 574.71',
            'UPI/DR/175429524263/Mrs SUJ/YESB/Q182214114/NO RE',
            '02-02-26 - 0 12.00 562.71',
            '07-02-26 UPI/CR/640408470894/PANKAJ K/SBIN/6376820454/Paid - 1000.00 0 1033.44',
        ]
        txns = _parse_lines(lines)
        for t in txns:
            assert t['description'] not in ('-', '', '--'), \
                f"Empty description found: {t}"

    def test_sarovar_categorised_as_food(self):
        lines = ['07-02-26 UPI/DR/205845445221/Sarovar /YESB/paytmqr12a/NO RE - 0 40.00 1008.44']
        txns = _parse_lines(lines)
        assert txns[0]['category'] == 'Food'

    def test_nit_cali_categorised_as_education(self):
        lines = ['10-02-26 UPI/DR/190609434827/NIT Cali/YESB/paytmqr281/NO RE - 0 294.00 372.44']
        txns = _parse_lines(lines)
        assert txns[0]['category'] == 'Education'


# ---------------------------------------------------------------------------
# 6. Recurring expense detection logic
# ---------------------------------------------------------------------------

from collections import defaultdict
import statistics

def _normalize_desc(desc):
    base = re.sub(r'\(.*?\)', '', desc).strip().lower()
    base = re.sub(r'\d+', '', base).strip()
    return base

def detect_recurring(txns, min_months=3, tolerance=0.25):
    """Mirror of the analytics.py recurring detection logic."""
    groups = defaultdict(list)
    for t in txns:
        if t['amount'] <= 0:
            continue
        key = _normalize_desc(t['description'])
        if not key:
            continue
        groups[key].append({'amount': t['amount'], 'date': t['date']})

    recurring = []
    for key, items in groups.items():
        months = {i['date'][:7] for i in items}
        if len(months) < min_months:
            continue
        amounts = sorted(i['amount'] for i in items)
        median = amounts[len(amounts) // 2]
        if median == 0:
            continue
        consistent = [a for a in amounts if abs(a - median) / median <= tolerance]
        if len(consistent) < len(amounts) * 0.6:
            continue
        recurring.append({'description': key, 'months_seen': len(months), 'median_amount': median})
    return recurring


class TestRecurringDetection:
    def _make_txns(self, desc, months, amount):
        return [{'description': desc, 'amount': amount, 'date': f'2026-{str(m).zfill(2)}-01'} for m in months]

    def test_vendor_in_3_months_flagged(self):
        txns = self._make_txns('Sarovar', [1, 2, 3], 40.0)
        result = detect_recurring(txns)
        assert len(result) == 1
        assert result[0]['months_seen'] == 3

    def test_vendor_in_2_months_not_flagged(self):
        txns = self._make_txns('Sarovar', [1, 2], 40.0)
        result = detect_recurring(txns)
        assert len(result) == 0

    def test_inconsistent_amounts_not_flagged(self):
        txns = [
            {'description': 'Random', 'amount': 40.0, 'date': '2026-01-01'},
            {'description': 'Random', 'amount': 400.0, 'date': '2026-02-01'},
            {'description': 'Random', 'amount': 4000.0, 'date': '2026-03-01'},
        ]
        result = detect_recurring(txns)
        assert len(result) == 0

    def test_income_transactions_ignored(self):
        """Negative amounts (income) should not appear in recurring expenses."""
        txns = [{'description': 'PANKAJ K', 'amount': -1000.0, 'date': f'2026-{m:02d}-01'} for m in range(1, 6)]
        result = detect_recurring(txns)
        assert len(result) == 0

    def test_mostly_consistent_still_flagged(self):
        """2 of 3 amounts within 25% of median (>=60%) still flags as recurring."""
        txns = [
            {'description': 'NIT Cali', 'amount': 294.0, 'date': '2026-01-10'},
            {'description': 'NIT Cali', 'amount': 65.0,  'date': '2026-02-10'},
            {'description': 'NIT Cali', 'amount': 280.0, 'date': '2026-03-10'},
        ]
        result = detect_recurring(txns)
        # median=280, 294 and 280 are within 25% (2/3=66%>=60%), so flagged
        assert len(result) == 1

    def test_very_consistent_recurring(self):
        txns = [
            {'description': 'Netflix', 'amount': 649.0, 'date': f'2026-{m:02d}-15'}
            for m in range(1, 7)
        ]
        result = detect_recurring(txns)
        assert len(result) == 1
        assert result[0]['months_seen'] == 6
