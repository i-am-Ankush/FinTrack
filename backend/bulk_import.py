"""
bulk_import.py — Run this once to import ALL your PDFs directly into the DB.
Place this file in ~/Downloads/fintrack/backend/
Run: python3 bulk_import.py

This bypasses the web upload and imports directly, so file format differences don't matter.
"""

import os, sys, re, zipfile, io, glob
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models import get_db, init_db
from ml.classifier import predict_category
from routes.upload import _parse_sbi, _classify_line

# ── CONFIG: put the folder containing your PDF statements here ──
PDF_FOLDER = os.path.expanduser('~/Downloads')  # change if needed

def find_sbi_pdfs(folder):
    """Find all SBI statement PDFs in a folder."""
    patterns = [
        os.path.join(folder, '*unlocked*.pdf'),
        os.path.join(folder, '*statement*.pdf'),
        os.path.join(folder, '*SBI*.pdf'),
        os.path.join(folder, '9183250193*.pdf'),
    ]
    found = set()
    for p in patterns:
        found.update(glob.glob(p))
    return sorted(found)

def import_pdf(pdf_path, user_id=1):
    with open(pdf_path, 'rb') as f:
        file_bytes = f.read()
    
    txns = _parse_sbi(file_bytes)
    if not txns:
        return 0, 0, 'No transactions parsed'
    
    inserted = 0
    skipped = 0
    conn = get_db()
    
    for t in txns:
        existing = conn.execute(
            "SELECT id FROM transactions WHERE user_id=? AND date=? AND amount=? AND description=?",
            (user_id, t['date'], t['amount'], t['description'])
        ).fetchone()
        if existing:
            skipped += 1
            continue
        category = t['category']
        if category == 'Other':
            category = predict_category(t['description'])
        conn.execute(
            "INSERT INTO transactions (user_id, amount, category, description, date, source) VALUES (?,?,?,?,?,?)",
            (user_id, t['amount'], category, t['description'], t['date'], 'pdf')
        )
        inserted += 1
    
    conn.commit()
    conn.close()
    return inserted, skipped, 'OK'

if __name__ == '__main__':
    # Make sure DB exists
    init_db()
    
    pdfs = find_sbi_pdfs(PDF_FOLDER)
    
    if not pdfs:
        print(f"No SBI PDFs found in {PDF_FOLDER}")
        print("Edit PDF_FOLDER at the top of this script to point to your statements folder.")
        sys.exit(1)
    
    print(f"Found {len(pdfs)} PDF files in {PDF_FOLDER}\n")
    
    total_inserted = 0
    total_skipped = 0
    
    for pdf_path in pdfs:
        fname = os.path.basename(pdf_path)
        inserted, skipped, status = import_pdf(pdf_path)
        total_inserted += inserted
        total_skipped += skipped
        print(f"  {fname}: {inserted} imported, {skipped} skipped — {status}")
    
    print(f"\nDone. Total imported: {total_inserted}, skipped: {total_skipped}")
    print(f"\nDB now has:")
    conn = get_db()
    rows = conn.execute("SELECT strftime('%Y-%m', date) as month, COUNT(*) as cnt FROM transactions GROUP BY month ORDER BY month").fetchall()
    for r in rows:
        print(f"  {r['month']}: {r['cnt']}")
    total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    print(f"\nTotal: {total}")
    conn.close()
