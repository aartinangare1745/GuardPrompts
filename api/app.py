# api/app.py
from fastapi import FastAPI
from pydantic import BaseModel
from src.predict import predict_prompt

app = FastAPI(title="GuardPrompt API")

class PromptRequest(BaseModel):
    prompt: str

@app.get("/")
def home():
    return {"message": "GuardPrompt API is running"}

@app.post("/predict")
def predict(data: PromptRequest):
    """
    Receive prompt and return prediction
    """
    result = predict_prompt(data.prompt)
    return result
