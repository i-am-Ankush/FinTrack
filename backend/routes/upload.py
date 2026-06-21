"""
upload.py — SBI Yono statement parser.

ROOT CAUSE FOUND AND FIXED: the user's real PDFs are genuine PDF files
(not ZIP archives), so every upload fell through to the pdfplumber
fallback path. pdfplumber's text extraction splits each transaction
across TWO lines — the UPI description on one line, the date+amounts
on the NEXT line — which the old single-direction line-joiner never
handled (it only looked for date-prefixed lines and joined forward).

This version uses one unified parser that handles both:
  Format A (ZIP-based exports): "DD-MM-YY <desc> <cr> <dr> <bal>",
    optionally wrapped across multiple lines starting with the date.
  Format B (real PDF via pdfplumber): "<desc>" on its own line(s),
    followed later by "DD-MM-YY <cr> <dr> <bal>" with no description.
"""

import os, re, zipfile, io
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import get_db
from ml.classifier import predict_category, get_metrics

upload_bp = Blueprint('upload', __name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

KEYWORD_MAP = {
    'cravebox': 'Food', 'sarovar': 'Food', 'nandini': 'Food', 'mrs suj': 'Food',
    'jk foods': 'Food', 'j k foods': 'Food', 'zaika': 'Food', 'foodies': 'Food',
    'swiggy': 'Food', 'zomato': 'Food', 'dominos': 'Food', 'domino': 'Food',
    'one mart': 'Food', 'onemart': 'Food', 'big mart': 'Food', 'm b hari': 'Food',
    'bake hou': 'Food', 'r berry': 'Food', 'm r foods': 'Food', 'instacup': 'Food',
    'tastic l': 'Food', 'new coch': 'Food', 'vappus m': 'Food',
    'lavanya': 'Food', 'm a supe': 'Food', 'masuper': 'Food',
    'avenue f': 'Food', 'avenue s': 'Food', 'moideen': 'Food',
    'kamlaksh': 'Food', 'rudra gr': 'Food', 'adhwaith': 'Food',
    'blue dar': 'Food', 'saithala': 'Food', 'amr store': 'Food',
    'cafe': 'Food', 'restaurant': 'Food', 'mess': 'Food', 'canteen': 'Food',
    'pizza': 'Food', 'burger': 'Food', 'biryani': 'Food',
    'cheniyal': 'Food', 'kattanga': 'Food', 'rajani': 'Food',
    'ola': 'Transport', 'uber': 'Transport', 'rapido': 'Transport',
    'irctc': 'Transport', 'redbus': 'Transport', 'indian r': 'Transport',
    'metro': 'Transport', 'bp jaip': 'Transport',
    'amazon': 'Shopping', 'flipkart': 'Shopping', 'myntra': 'Shopping',
    'meesho': 'Shopping', 'nykaa': 'Shopping', 'ajio': 'Shopping',
    'gift zone': 'Shopping', 'lg elect': 'Shopping', 'woodland': 'Shopping',
    'reliance': 'Shopping', 'ekart': 'Shopping', 'dealshare': 'Shopping',
    'instakar': 'Shopping', 'apple my': 'Shopping', 'vendekin': 'Shopping',
    'nit cali': 'Education', 'byju': 'Education', 'openai': 'Education',
    'google i': 'Education', 'innvera': 'Education', 'scholar docum': 'Education',
    'kmct med': 'Health', 'ayisha n': 'Health', 'pharmacy': 'Health',
    'hospital': 'Health', 'medical': 'Health', 'netmeds': 'Health',
    'netflix': 'Entertainment', 'spotify': 'Entertainment',
    'hotstar': 'Entertainment', 'pvr': 'Entertainment',
    'inox': 'Entertainment', 'google p': 'Entertainment',
    'npci bhim': 'Income', 'bhimcashba': 'Income', 'phonepe': 'Income',
    'phonepemer': 'Income', 'supermoney': 'Income', 'cashfree': 'Income',
    'pankaj k': 'Income', 'pankaj kumar': 'Income',
    'dep tfr': 'Income', 'interest credit': 'Income',
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

# Anchor pattern: an optional leading date, then anything, then the
# three trailing numeric columns (credit, debit, balance).
_DATE_PREFIX_RE = re.compile(r'^(\d{2}-\d{2}-\d{2})\s*(.*)$')
_NUMS_TAIL_RE   = re.compile(r'^(.*?)\s*(-|0|[\d,]+\.\d{2})\s+(-|0|[\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$')


def _classify_line(raw: str, direction: str) -> str:
    low = raw.lower()
    for kw, cat in KEYWORD_MAP.items():
        if kw in low:
            return cat
    return 'Income' if direction == 'CR' else 'Other'


def _parse_amount(s: str) -> float:
    s = s.strip()
    if s in ('-', '0', ''):
        return 0.0
    try:
        return float(s.replace(',', ''))
    except ValueError:
        return 0.0


def _clean_desc(raw: str) -> str:
    """Build a readable display name from the raw UPI reference string."""
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


def _extract_transaction_units(lines: list) -> list:
    """
    Walks raw text lines and reconstructs (date, description, credit,
    debit, balance) tuples regardless of whether the source splits
    each transaction across 1, 2, or 3 physical lines, and regardless
    of whether the date leads the description or trails it.
    """
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
                # Full transaction on one line (date + desc + numbers)
                inline_desc, cr_s, dr_s, bal_s = nums_m.groups()
                while desc_buffer and '/' not in desc_buffer[0] and len(desc_buffer[0]) < 10:
                    desc_buffer.pop(0)
                full_desc = ' '.join(desc_buffer + ([inline_desc] if inline_desc.strip() else [])).strip()
                units.append((date_raw, full_desc, cr_s, dr_s, bal_s))
                desc_buffer = []
                pending_date = None
            elif rest.strip():
                # Date + partial description, more text follows (wrap)
                desc_buffer.append(rest.strip())
                pending_date = date_raw
            else:
                # Bare date line; numbers arrive on a later line
                pending_date = date_raw
            continue

        nums_m = _NUMS_TAIL_RE.match(l)
        if nums_m and pending_date:
            # Numbers-only line resolving a previously-seen date
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


def _parse_lines(lines: list) -> list:
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


def _parse_sbi(file_bytes: bytes) -> list:
    """
    Try ZIP-based extraction first (SBI Yono Relationship Summary
    exports that are actually ZIP archives), then fall back to
    pdfplumber for genuine PDF files. Both paths feed the same
    unified _parse_lines() so either source format is handled
    correctly.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            txt_names = sorted([n for n in zf.namelist() if n.endswith('.txt')])
            if txt_names:
                all_lines = []
                for tf in txt_names:
                    content = zf.read(tf).decode('utf-8', errors='replace')
                    all_lines.extend(content.replace('\r\n', '\n').replace('\r', '\n').split('\n'))
                txns = _parse_lines(all_lines)
                if txns:
                    return txns
    except (zipfile.BadZipFile, Exception):
        pass

    try:
        import pdfplumber
        full_text = ''
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    full_text += t + '\n'
        if full_text:
            lines = full_text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
            return _parse_lines(lines)
    except Exception:
        pass

    return []


@upload_bp.route('/pdf', methods=['POST'])
@jwt_required()
def upload_pdf():
    user_id = get_jwt_identity()
    if 'file' not in request.files:
        return jsonify(msg='No file uploaded'), 400
    file = request.files['file']
    if not file.filename.lower().endswith('.pdf'):
        return jsonify(msg='Only PDF files accepted'), 400

    file_bytes = file.read()
    raw_txns = _parse_sbi(file_bytes)

    if not raw_txns:
        return jsonify(msg='No transactions found. Make sure this is an SBI Yono Relationship Summary PDF.'), 422

    conn = get_db()

    existing_rows = conn.execute(
        "SELECT date, amount, description FROM transactions WHERE user_id=?",
        (user_id,)
    ).fetchall()
    existing_keys = {(r['date'], round(float(r['amount']), 2), r['description']) for r in existing_rows}

    to_insert = []
    skipped = 0
    for t in raw_txns:
        key = (t['date'], round(float(t['amount']), 2), t['description'])
        if key in existing_keys:
            skipped += 1
            continue
        category = t['category']
        if category == 'Other':
            category = predict_category(t['description'])
        to_insert.append((user_id, t['amount'], category, t['description'], t['date'], 'pdf'))
        existing_keys.add(key)

    inserted = 0
    if to_insert:
        cur = conn._cursor
        from psycopg2.extras import execute_values
        execute_values(
            cur,
            "INSERT INTO transactions (user_id, amount, category, description, date, source) VALUES %s",
            to_insert
        )
        inserted = len(to_insert)

    conn.commit()
    conn.close()

    return jsonify(
        msg=f'Imported {inserted} transactions ({skipped} duplicates skipped)',
        count=inserted, skipped=skipped, bank='SBI'
    ), 201


@upload_bp.route('/train', methods=['POST'])
@jwt_required()
def train_model():
    from ml.classifier import train
    user_id = get_jwt_identity()
    conn = get_db()
    rows = conn.execute("SELECT description, category FROM transactions WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    descriptions, labels = [], []
    for row in rows:
        desc  = row['description']
        label = row['category']
        if label == 'Other':
            label = _classify_line(desc, 'DR')
        descriptions.append(desc)
        labels.append(label)
    if len(descriptions) < 10:
        return jsonify(msg=f'Need at least 10 transactions, have {len(descriptions)}'), 400
    metrics = train(descriptions, labels)
    if 'error' in metrics:
        return jsonify(metrics), 400
    return jsonify(metrics), 200


@upload_bp.route('/metrics', methods=['GET'])
@jwt_required()
def model_metrics():
    return jsonify(get_metrics())
