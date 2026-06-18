"""
Run this after uploading some PDFs to retrain the classifier.
Usage: python ml/train.py

Pulls all transactions from the DB, labels them with rules, trains the model.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import get_db
from ml.rules import rule_classify
from ml.classifier import train

def main():
    conn = get_db()
    rows = conn.execute("SELECT description, category FROM transactions").fetchall()
    conn.close()

    descriptions, labels = [], []
    for row in rows:
        desc  = row['description']
        label = row['category'] if row['category'] != 'Other' else rule_classify(desc)
        descriptions.append(desc)
        labels.append(label)

    if len(descriptions) < 10:
        print(f"Only {len(descriptions)} transactions — need at least 10 to train.")
        return

    print(f"Training on {len(descriptions)} samples…")
    metrics = train(descriptions, labels)
    print(f"✅ Accuracy: {metrics['accuracy']}%  |  Samples: {metrics['samples']}")
    print("Model saved to ml/classifier.pkl")

if __name__ == '__main__':
    main()
