import os
from datetime import timedelta

class Config:
    SECRET_KEY               = os.getenv('SECRET_KEY', 'dev-secret-change-in-prod')
    JWT_SECRET_KEY            = os.getenv('JWT_SECRET_KEY', 'jwt-secret-change-in-prod')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
    DATABASE_URL             = os.getenv('DATABASE_URL', '')
    CORS_ORIGINS             = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    MAX_CONTENT_LENGTH       = 16 * 1024 * 1024   # 16 MB upload limit
    UPLOAD_FOLDER             = 'uploads'
