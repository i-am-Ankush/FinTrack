from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import get_db

transactions_bp = Blueprint('transactions', __name__)

@transactions_bp.route('', methods=['GET'])
@jwt_required()
def get_transactions():
    user_id  = get_jwt_identity()
    category = request.args.get('category')
    month    = request.args.get('month')   # YYYY-MM
    search   = request.args.get('search', '')

    query  = "SELECT * FROM transactions WHERE user_id=?"
    params = [user_id]

    if category:
        query += " AND category=?"
        params.append(category)
    if month:
        query += " AND date LIKE ?"
        params.append(f"{month}%")
    if search:
        query += " AND (description LIKE ? OR category LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]

    query += " ORDER BY date DESC, created_at DESC"

    conn = get_db()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@transactions_bp.route('', methods=['POST'])
@jwt_required()
def add_transaction():
    user_id = get_jwt_identity()
    data    = request.get_json()

    required = ['amount', 'description', 'date']
    if not all(data.get(k) for k in required):
        return jsonify(msg='amount, description, date are required'), 400

    category   = data.get('category', '').strip()
    confidence = None
    if not category or category == 'Other':
        from ml.classifier import predict_category_with_confidence
        result     = predict_category_with_confidence(data['description'])
        category   = result['category']
        confidence = result['confidence']

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO transactions (user_id, amount, category, description, date, source) VALUES (?,?,?,?,?,?) RETURNING id",
        (user_id, float(data['amount']), category, data['description'], data['date'], data.get('source', 'manual'))
    )
    row_id = cur.fetchone()[0]
    conn.commit()
    row = conn.execute("SELECT * FROM transactions WHERE id=?", (row_id,)).fetchone()
    conn.close()

    result = dict(row)
    if confidence is not None:
        result['ml_confidence'] = confidence
    return jsonify(result), 201

@transactions_bp.route('/<int:tid>', methods=['PUT'])
@jwt_required()
def update_transaction(tid):
    user_id = get_jwt_identity()
    data    = request.get_json()

    conn = get_db()
    row  = conn.execute("SELECT * FROM transactions WHERE id=? AND user_id=?", (tid, user_id)).fetchone()
    if not row:
        conn.close()
        return jsonify(msg='Not found'), 404

    amount      = data.get('amount',      row['amount'])
    category    = data.get('category',    row['category'])
    description = data.get('description', row['description'])
    date        = data.get('date',        row['date'])

    conn.execute(
        "UPDATE transactions SET amount=?, category=?, description=?, date=? WHERE id=?",
        (float(amount), category, description, date, tid)
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM transactions WHERE id=?", (tid,)).fetchone()
    conn.close()
    return jsonify(dict(updated))

@transactions_bp.route('/<int:tid>', methods=['DELETE'])
@jwt_required()
def delete_transaction(tid):
    user_id = get_jwt_identity()
    conn    = get_db()
    row     = conn.execute("SELECT id FROM transactions WHERE id=? AND user_id=?", (tid, user_id)).fetchone()
    if not row:
        conn.close()
        return jsonify(msg='Not found'), 404

    conn.execute("DELETE FROM transactions WHERE id=?", (tid,))
    conn.commit()
    conn.close()
    return jsonify(msg='Deleted'), 200
