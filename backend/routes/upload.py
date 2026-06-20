"""
upload.py — SBI Yono parser. DEBUG VERSION: traces _clean_desc() input/output
directly to nail down the description="-" bug at the exact line level.
"""

import os, re, zipfile, io, sys
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
    'visit https', 'as on ', 'date transaction',
    'your opening', 'your closing', 'contents of this',
]

TXN_RE = re.compile(
    r'^(\d{2}-\d{2}-\d{2})\s+'
    r'(.+?)\s+'
    r'(-|0|[\d,]+\.\d{2})\s+'
    r'(-|0|[\d,]+\.\d{2})\s+'
    r'([\d,]+\.\d{2})\s*$'
)


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


def _join_wrapped_lines(raw_lines: list) -> list:
    joined = []
    i = 0
    while i < len(raw_lines):
        l = raw_lines[i].strip()
        if re.match(r'^\d{2}-\d{2}-\d{2}\s', l):
            if not re.search(r'[\d,]+\.\d{2}\s*$', l):
                combined = l
                i += 1
                while i < len(raw_lines):
                    nxt = raw_lines[i].strip()
                    if not nxt:
                        i += 1
                        continue
                    if re.match(r'^\d{2}-\d{2}-\d{2}\s', nxt):
                        break
                    combined = combined + ' ' + nxt
                    i += 1
                    if re.search(r'[\d,]+\.\d{2}\s*$', combined):
                        break
                joined.append(combined)
            else:
                joined.append(l)
                i += 1
        else:
            i += 1
    return joined


def _parse_lines(lines: list) -> list:
    txns = []
    debug_count = 0
    for l in _join_wrapped_lines(lines):
        if any(p in l.lower() for p in _SKIP_LINES):
            continue
        m = TXN_RE.match(l)
        if not m:
            continue
        date_raw, desc, cr_s, dr_s, _ = m.groups()
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

        # ===== TEMPORARY DEBUG: trace the exact transform =====
        if debug_count < 8:
            print(f"DEBUG LINE: raw_line={l!r}", file=sys.stderr)
            print(f"DEBUG LINE: desc_captured={desc!r}", file=sys.stderr)
            print(f"DEBUG LINE: display_result={display!r}", file=sys.stderr)
            debug_count += 1
        # ===== END DEBUG =====

        if credit > 0 and debit == 0:
            txns.append({'date': date_str, 'amount': -credit, 'description': display, 'category': category})
        else:
            txns.append({'date': date_str, 'amount': debit, 'description': display, 'category': category})
    return txns


def _parse_sbi(file_bytes: bytes) -> list:
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
