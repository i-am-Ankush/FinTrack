from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from models import get_db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify(msg='Email and password required'), 400
    if len(password) < 6:
        return jsonify(msg='Password must be at least 6 characters'), 400

    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?) RETURNING id",
            (email, generate_password_hash(password))
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        token = create_access_token(identity=str(user_id))
        return jsonify(token=token, email=email), 201
    except Exception:
        return jsonify(msg='Email already registered'), 409
    finally:
        conn.close()

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify(msg='Invalid credentials'), 401

    token = create_access_token(identity=str(user['id']))
    return jsonify(token=token, email=email), 200
