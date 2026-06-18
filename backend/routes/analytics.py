from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import get_db
from datetime import datetime
import calendar

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

    # Spending by category — expenses only (positive amounts, exclude Income)
    by_category = conn.execute(
        """SELECT category, ROUND(SUM(amount),2) as total
           FROM transactions
           WHERE user_id=? AND date LIKE ? AND amount>0 AND category != 'Income'
           GROUP BY category ORDER BY total DESC""",
        (user_id, f"{month_str}%")
    ).fetchall()

    # Total income this month (negative amounts = money received)
    income_row = conn.execute(
        """SELECT ROUND(SUM(ABS(amount)),2) as total
           FROM transactions
           WHERE user_id=? AND date LIKE ? AND amount<0""",
        (user_id, f"{month_str}%")
    ).fetchone()
    total_income = income_row['total'] or 0.0

    # Daily spending trend (expenses only)
    days_in_month = calendar.monthrange(year, month)[1]
    daily_rows = conn.execute(
        """SELECT date, ROUND(SUM(amount),2) as total
           FROM transactions
           WHERE user_id=? AND date LIKE ? AND amount>0 AND category != 'Income'
           GROUP BY date ORDER BY date""",
        (user_id, f"{month_str}%")
    ).fetchall()

    daily_map   = {r['date']: r['total'] for r in daily_rows}
    daily_trend = [
        {"date": f"{month_str}-{d:02d}", "amount": daily_map.get(f"{month_str}-{d:02d}", 0)}
        for d in range(1, days_in_month + 1)
    ]

    conn.close()
    return jsonify(
        by_category  = [dict(r) for r in by_category],
        daily_trend  = daily_trend,
        total_income = total_income,
        month        = month,
        year         = year
    )
