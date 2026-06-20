from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import get_db
from datetime import datetime

budget_bp = Blueprint('budget', __name__)

def _current_month_spending(user_id, month, year):
    conn  = get_db()
    month_str = f"{year}-{month:02d}"
    row   = conn.execute(
        "SELECT COALESCE(SUM(amount),0) as total FROM transactions WHERE user_id=? AND date LIKE ? AND amount > 0",
        (user_id, f"{month_str}%")
    ).fetchone()
    conn.close()
    return row['total']

@budget_bp.route('', methods=['GET'])
@jwt_required()
def get_budget():
    user_id = get_jwt_identity()
    now     = datetime.now()
    month   = int(request.args.get('month', now.month))
    year    = int(request.args.get('year',  now.year))

    conn = get_db()
    row  = conn.execute(
        "SELECT * FROM budgets WHERE user_id=? AND month=? AND year=?",
        (user_id, month, year)
    ).fetchone()
    conn.close()

    budget_amount = dict(row)['amount'] if row else 0
    spent         = _current_month_spending(user_id, month, year)

    return jsonify(
        budget=budget_amount,
        spent=spent,
        remaining=budget_amount - spent,
        month=month,
        year=year,
        alert=(spent >= budget_amount * 0.8) if budget_amount > 0 else False
    )

@budget_bp.route('', methods=['POST'])
@jwt_required()
def set_budget():
    user_id = get_jwt_identity()
    data    = request.get_json()
    now     = datetime.now()
    month   = int(data.get('month', now.month))
    year    = int(data.get('year',  now.year))
    amount  = float(data.get('amount', 0))

    conn = get_db()
    conn.execute(
        "INSERT INTO budgets (user_id, month, year, amount) VALUES (?,?,?,?) "
        "ON CONFLICT (user_id, month, year) DO UPDATE SET amount=EXCLUDED.amount",
        (user_id, month, year, amount)
    )
    conn.commit()
    conn.close()
    return jsonify(msg='Budget saved', month=month, year=year, amount=amount), 200
