'''
Functions to classify emote from LLM-response.
'''

from transformers import pipeline
import random
import threading

import requests

def classify_gesture_api(text, labels):
    url = "http://127.0.0.1:8000/classify"
    data = {"text": text, "labels": labels}
    response = requests.post(url, json=data, timeout=30)
    response.raise_for_status()
    result = response.json()
    return result["label"]

def select_gesture(gesture_dict, gesture_category):
    """Pick a random gesture from the category"""
    return random.choice(gesture_dict[gesture_category])
