from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer
import uvicorn
import os

app = FastAPI()

MODEL_NAME = "MoritzLaurer/deberta-v3-base-mnli"
LOCAL_DIR = "local_model"

# DEBUG: print absolute path for local_model
abs_local_dir = os.path.abspath(LOCAL_DIR)
print(f"[DEBUG] local_model folder will be looked for at: {abs_local_dir}")

def load_zero_shot_pipeline():
    """
    Load model from local folder if available,
    otherwise download it and save it locally.
    """
    # --- If the model folder already exists: load from disk ---
    if os.path.isdir(LOCAL_DIR):
        print(f"Loading model from local folder '{LOCAL_DIR}'...")
        classifier = pipeline(
            "zero-shot-classification",
            model=LOCAL_DIR,
            tokenizer=LOCAL_DIR,
            device=-1,
        )
        print("Model loaded from local directory.")
        return classifier

    # --- Otherwise download it from HuggingFace Hub ---
    print("Downloading model from HuggingFace...")
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    # --- Save to local folder ---
    print(f"Saving model to '{LOCAL_DIR}'...")
    model.save_pretrained(LOCAL_DIR)
    tokenizer.save_pretrained(LOCAL_DIR)
    print("Model saved locally.")

    # --- Create the pipeline using the local path ---
    classifier = pipeline(
        "zero-shot-classification",
        model=model,
        tokenizer=tokenizer,
        device=-1,
    )
    print("Model loaded from downloaded version.")
    return classifier


print("Initializing model...")
classifier = load_zero_shot_pipeline()
print("Model ready.")


class ClassificationRequest(BaseModel):
    text: str
    labels: list[str]


@app.post("/classify")
def classify(req: ClassificationRequest):
    result = classifier(req.text, candidate_labels=req.labels)
    return {"label": result["labels"][0], "scores": result["scores"]}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
