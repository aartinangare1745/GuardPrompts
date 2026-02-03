# api/app.py
from fastapi import FastAPI
from pathlib import Path
from pydantic import BaseModel
import joblib
from sentence_transformers import SentenceTransformer


app = FastAPI(title="GuardPrompts – Prompt Injection Detector")
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "classifier.joblib"
model = joblib.load(MODEL_PATH)
embedder = SentenceTransformer("all-MiniLM-L6-v2")

class PromptRequest(BaseModel):
    prompt: str

@app.post("/predict")
def predict(req: PromptRequest):
    emb = embedder.encode([req.prompt])
    prob = model.predict_proba(emb)[0][1]

    return {
        "attack_probability": round(float(prob), 4),
        "risk_level": (
            "low" if prob < 0.3 else
            "medium" if prob < 0.6 else
            "high"
        )
    }
