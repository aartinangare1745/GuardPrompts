# src/train.py
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
import joblib
import os

def main():
    # Load embeddings and labels
    X = np.load('data/processed/X.npy')
    y = np.load('data/processed/y.npy')

    # Split into train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Initialize model (you can try LogisticRegression or RandomForest)
    model = RandomForestClassifier(n_estimators=200, random_state=42)

    # Train model
    model.fit(X_train, y_train)

    # Predict on test
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:,1]

    # Metrics
    print("Classification Report:")
    print(classification_report(y_test, y_pred))
    print(f"ROC-AUC: {roc_auc_score(y_test, y_prob):.4f}")

    # Save model
    os.makedirs('models', exist_ok=True)
    joblib.dump(model, 'models/attack_model.pkl')
    print("Trained model saved to models/attack_model.pkl")

if __name__ == "__main__":
    main()
