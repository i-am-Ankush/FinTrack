from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import Config
from models import init_db

from routes.auth import auth_bp
from routes.transactions import transactions_bp
from routes.budget import budget_bp
from routes.analytics import analytics_bp
from routes.upload import upload_bp
from routes.export import export_bp

app = Flask(__name__)
app.config.from_object(Config)

CORS(app)
JWTManager(app)
init_db()

app.register_blueprint(auth_bp,         url_prefix='/auth')
app.register_blueprint(transactions_bp, url_prefix='/transactions')
app.register_blueprint(budget_bp,       url_prefix='/budget')
app.register_blueprint(analytics_bp,    url_prefix='/analytics')
app.register_blueprint(upload_bp,       url_prefix='/upload')
app.register_blueprint(export_bp,       url_prefix='/export')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
