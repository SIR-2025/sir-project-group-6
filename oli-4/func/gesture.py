'''
Functions to classify emote from LLM-response.
'''

from transformers import pipeline
import random
import threading

import requests

def classify_gesture_api(text, labels):
    """
    Classify text into a gesture category using the Gesture API.

    This function sends the text and candidate labels to a locally
    running FastAPI service that performs zero-shot classification.

    Args:
        text (str):
            LLM-generated text to classify.
        labels (list[str]):
            List of possible gesture categories.

    Returns:
        str:
            Predicted gesture category label.
    """
    url = "http://127.0.0.1:8000/classify"
    data = {"text": text, "labels": labels}
    response = requests.post(url, json=data, timeout=30)
    response.raise_for_status()
    result = response.json()
    return result["label"]

def select_gesture(gesture_dict, gesture_category):
    """
    Select a random concrete gesture from a gesture category.

    Args:
        gesture_dict (dict[str, list[str]]):
            Mapping from gesture categories to lists of gesture animation names.
        gesture_category (str):
            Selected gesture category.

    Returns:
        str:
            Name of the chosen gesture animation.
    """
    return random.choice(gesture_dict[gesture_category])
