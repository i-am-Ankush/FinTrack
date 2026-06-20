from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import get_db
from datetime import datetime
from collections import defaultdict
import calendar
import re

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/summary', methods=['GET'])
@jwt_required()
def summary():
    user_id = get_jwt_identity()
    now     = datetime.now()
    month   = int(request.args.get('month', now.month))
    year    = int(request.args.get('year',  now.year))
    month_str = f"{year}-{month:02d}"

    conn = get_db()

    # NOTE: ROUND(double precision, integer) doesn't exist in PostgreSQL —
    # must cast to numeric first. SQLite was permissive about this.
    by_category = conn.execute(
        """SELECT category, ROUND(SUM(amount)::numeric, 2) as total
           FROM transactions
           WHERE user_id=? AND date LIKE ? AND amount>0 AND category != 'Income'
           GROUP BY category ORDER BY total DESC""",
        (user_id, f"{month_str}%")
    ).fetchall()

    income_row = conn.execute(
        """SELECT ROUND(SUM(ABS(amount))::numeric, 2) as total
           FROM transactions
           WHERE user_id=? AND date LIKE ? AND amount<0""",
        (user_id, f"{month_str}%")
    ).fetchone()
    total_income = float(income_row['total']) if income_row['total'] else 0.0

    days_in_month = calendar.monthrange(year, month)[1]
    daily_rows = conn.execute(
        """SELECT date, ROUND(SUM(amount)::numeric, 2) as total
           FROM transactions
           WHERE user_id=? AND date LIKE ? AND amount>0 AND category != 'Income'
           GROUP BY date ORDER BY date""",
        (user_id, f"{month_str}%")
    ).fetchall()

    daily_map   = {r['date']: float(r['total']) for r in daily_rows}
    daily_trend = [
        {"date": f"{month_str}-{d:02d}", "amount": daily_map.get(f"{month_str}-{d:02d}", 0)}
        for d in range(1, days_in_month + 1)
    ]

    conn.close()
    return jsonify(
        by_category  = [{'category': r['category'], 'total': float(r['total'])} for r in by_category],
        daily_trend  = daily_trend,
        total_income = total_income,
        month        = month,
        year         = year
    )


def _normalize_desc(desc: str) -> str:
    base = re.sub(r'\(.*?\)', '', desc).strip().lower()
    base = re.sub(r'\d+', '', base).strip()
    return base


@analytics_bp.route('/recurring', methods=['GET'])
@jwt_required()
def recurring():
    user_id = get_jwt_identity()

    conn = get_db()
    rows = conn.execute(
        """SELECT description, amount, date FROM transactions
           WHERE user_id=? AND amount > 0 AND category != 'Income'
           ORDER BY date""",
        (user_id,)
    ).fetchall()
    conn.close()

    groups = defaultdict(list)
    for r in rows:
        key = _normalize_desc(r['description'])
        if not key:
            continue
        groups[key].append({'amount': float(r['amount']), 'date': r['date']})

    recurring_list = []
    for key, txns in groups.items():
        months = {t['date'][:7] for t in txns}
        if len(months) < 3:
            continue

        amounts = sorted(t['amount'] for t in txns)
        median = amounts[len(amounts) // 2]
        if median == 0:
            continue

        consistent = [a for a in amounts if abs(a - median) / median <= 0.25]
        if len(consistent) < len(amounts) * 0.6:
            continue

        recurring_list.append({
            'description': key.title(),
            'median_amount': round(median, 2),
            'months_seen': len(months),
            'total_occurrences': len(txns),
            'last_date': max(t['date'] for t in txns),
        })

    recurring_list.sort(key=lambda x: -x['months_seen'])

    return jsonify(recurring=recurring_list[:10])
