import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
import joblib
import os

def main():
    X = np.load("data/processed/X_emb.npy")
    y = np.load("data/processed/y.npy")

    print("X shape:", X.shape)
    print("y shape:", y.shape)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = LogisticRegression(
        max_iter=1000,
        class_weight="balanced"
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    for t in [0.3, 0.4, 0.5, 0.6, 0.7]:
       preds = (y_proba >= t).astype(int)
       print(f"Threshold {t}: F1 =", f1_score(y_test, preds))

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    os.makedirs("models", exist_ok=True)
    #joblib.dump(model, "models/prompt_injection_detector.pkl")
    joblib.dump(model, "models/classifier.joblib")
    print("\nModel saved to models/classifier.joblib")

if __name__ == "__main__":
    main()

'''
X shape: (4616, 384)
y shape: (4616,)

Classification Report:
              precision    recall  f1-score   support

           0       0.52      0.49      0.51       453
           1       0.54      0.56      0.55       471

    accuracy                           0.53       924
   macro avg       0.53      0.53      0.53       924
weighted avg       0.53      0.53      0.53       924

Confusion Matrix:
[[224 229]
 [205 266]]
'''


'''
X shape: (4616, 384)
y shape: (4616,)

Classification Report:
              precision    recall  f1-score   support

           0       0.99      0.98      0.98       453
           1       0.98      0.99      0.98       471

    accuracy                           0.98       924
X shape: (4616, 384)
y shape: (4616,)

   macro avg       0.98      0.98      0.98       924
weighted avg       0.98      0.98      0.98       924

Confusion Matrix:
[[443  10]
 [  6 465]]
'''