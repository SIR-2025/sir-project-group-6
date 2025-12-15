from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer
import uvicorn
import os

app = FastAPI()

# HuggingFace model identifier
MODEL_NAME = "MoritzLaurer/deberta-v3-base-mnli"
# Local directory for cached model
LOCAL_DIR = "local_model"

abs_local_dir = os.path.abspath(LOCAL_DIR)
print(f"local_model folder will be looked for at: {abs_local_dir}")

def load_zero_shot_pipeline():
    """
    Load a zero-shot classification pipeline.

    Behavior:
    - If a local model directory exists, load the model and tokenizer from disk.
    - Otherwise, download the model from HuggingFace Hub, save it locally,
      and then initialize the pipeline.

    Returns:
        transformers.pipeline:
            A zero-shot classification pipeline running on CPU.
    """
    # If the model folder already exists: load from disk
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

    # Otherwise download it from HuggingFace Hub
    print("Downloading model from HuggingFace...")
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    # Save to local folder
    print(f"Saving model to '{LOCAL_DIR}'...")
    model.save_pretrained(LOCAL_DIR)
    tokenizer.save_pretrained(LOCAL_DIR)
    print("Model saved locally.")

    # Create the pipeline using the local path
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

class ClassificationRequest(BaseModel):
    """
    Request schema for the /classify endpoint.

    Attributes:
        text (str):
            Input text to be classified (e.g., an LLM-generated response).
        labels (list[str]):
            Candidate labels to classify the text against.
    """
    text: str
    labels: list[str]


@app.post("/classify")
def classify(req: ClassificationRequest):
    """
    Classify input text into one of the provided candidate labels.

    This endpoint performs zero-shot classification and returns the
    highest-scoring label along with all label scores.

    Args:
        req (ClassificationRequest):
            Request containing text and candidate labels.

    Returns:
        dict:
            Dictionary with:
            - "label": The highest-scoring predicted label
            - "scores": List of confidence scores for each candidate label
    """
    result = classifier(req.text, candidate_labels=req.labels)
    return {"label": result["labels"][0], "scores": result["scores"]}


if __name__ == "__main__":
    print("Model ready.")
    uvicorn.run(app, host="127.0.0.1", port=8000)
