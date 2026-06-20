"""
ML classifier: TF-IDF + Logistic Regression via sklearn.pipeline.
Handles singleton classes gracefully (no crash on small datasets).
Now also exposes prediction confidence via predict_proba().
"""

import pickle
import json
from pathlib import Path
from collections import Counter

MODEL_PATH   = Path(__file__).parent / 'classifier.pkl'
METRICS_PATH = Path(__file__).parent / 'metrics.json'

_model = None

def _load_model():
    global _model
    if _model is None and MODEL_PATH.exists():
        with open(MODEL_PATH, 'rb') as f:
            _model = pickle.load(f)
    return _model

def predict_category(description: str) -> str:
    model = _load_model()
    if model:
        return model.predict([description])[0]
    from ml.rules import rule_classify
    return rule_classify(description)

def predict_category_with_confidence(description: str) -> dict:
    """
    Returns {"category": str, "confidence": float|None}.
    confidence is the model's probability for the predicted class,
    rounded to 2 decimals as a percentage (e.g. 87.42).
    None if no trained model exists yet (rule-based fallback has no
    meaningful probability).
    """
    model = _load_model()
    if model:
        category = model.predict([description])[0]
        try:
            proba = model.predict_proba([description])[0]
            classes = model.classes_
            idx = list(classes).index(category)
            confidence = round(float(proba[idx]) * 100, 2)
        except Exception:
            confidence = None
        return {"category": category, "confidence": confidence}

    from ml.rules import rule_classify
    return {"category": rule_classify(description), "confidence": None}

def train(descriptions: list, labels: list) -> dict:
    """
    Train TF-IDF + LogisticRegression pipeline.
    Filters out singleton classes so train_test_split never crashes.
    """
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score

    if len(set(labels)) < 2:
        return {"error": "Need at least 2 categories to train"}

    counts = Counter(labels)
    filtered = [(d, l) for d, l in zip(descriptions, labels) if counts[l] >= 2]
    dropped = len(descriptions) - len(filtered)

    if len(filtered) < 10:
        return {"error": f"Too few samples after filtering singletons. Have {len(filtered)}, need 10+."}

    descriptions_f = [x[0] for x in filtered]
    labels_f       = [x[1] for x in filtered]

    n_classes = len(set(labels_f))
    test_size = max(0.2, n_classes / len(labels_f))
    test_size = min(test_size, 0.4)

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            descriptions_f, labels_f,
            test_size=test_size, random_state=42, stratify=labels_f
        )
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(
            descriptions_f, labels_f, test_size=0.2, random_state=42
        )

    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=5000)),
        ('clf',   LogisticRegression(max_iter=1000, C=1.0, random_state=42))
    ])
    pipeline.fit(X_train, y_train)

    y_pred   = pipeline.predict(X_test)
    accuracy = round(accuracy_score(y_test, y_pred) * 100, 2)
    report   = classification_report(y_test, y_pred, output_dict=True)

    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(pipeline, f)

    metrics = {
        "accuracy": accuracy,
        "samples": len(descriptions_f),
        "dropped_singletons": dropped,
        "report": report
    }
    with open(METRICS_PATH, 'w') as f:
        json.dump(metrics, f)

    global _model
    _model = pipeline
    return metrics

def get_metrics() -> dict:
    if METRICS_PATH.exists():
        with open(METRICS_PATH) as f:
            return json.load(f)
    return {}
