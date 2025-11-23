# run_model.py
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline
import uvicorn

app = FastAPI()

print("Loading zero-shot model...")
classifier = pipeline(
    "zero-shot-classification",
    model="MoritzLaurer/deberta-v3-base-mnli",
    device=-1,  # CPU
)
print("Model loaded.")

class ClassificationRequest(BaseModel):
    text: str
    labels: list[str]

@app.post("/classify")
def classify(req: ClassificationRequest):
    result = classifier(req.text, candidate_labels=req.labels)
    # return only the top prediction
    return {"label": result["labels"][0], "scores": result["scores"]}

if __name__ == "__main__":
    # Run the API on localhost port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
