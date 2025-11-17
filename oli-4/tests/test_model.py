from func.gesture import classify_gesture, select_gesture, setup_classifier
import json
import time

with open('config/gestures.json', 'r') as file:
    gesture_dict = json.load(file)
    print("Imported gesture dict")

labels = list(gesture_dict.keys())
print(len(labels))

classifier = setup_classifier()
print("Classifier setup")

while True:
    text = input("What do you say?\n")
    start_time = time.time()
    category = classify_gesture(classifier, labels, text)
    end_time = time.time()
    print(f"Elapsed time {end_time - start_time}")
    print(category)
    gesture = select_gesture(gesture_dict, category)
    print(gesture)