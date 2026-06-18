# FinTrack — Personal Finance Dashboard

A full-stack personal finance management app built for college students.

## Stack
- **Frontend:** React, Tailwind CSS, Recharts
- **Backend:** Flask, SQLite, JWT auth
- **ML:** scikit-learn (TF-IDF + Logistic Regression)
- **PDF Parsing:** pdfplumber

## Features
- JWT authentication
- CRUD transaction management
- Monthly budget tracking with alerts
- Category analytics (pie chart + spending trend)
- SBI bank statement PDF ingestion
- ML auto-categorisation trained on real transaction data
- PDF report export

## Setup
```bash
# Backend
cd backend && pip install -r requirements.txt && python3 app.py

# Frontend  
cd frontend && npm install && npm start
```
