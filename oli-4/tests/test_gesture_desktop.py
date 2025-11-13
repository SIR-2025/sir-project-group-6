# Import basic preliminaries
from func.gesture import classify_gesture_api, select_gesture
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging

# Import the device(s) we will be using
from sic_framework.devices.desktop import Desktop

# Import libraries necessary for the demo
import json
from os.path import abspath, join
import numpy as np
import threading

class DialogflowCXDemo(SICApplication):
    """
    Dialogflow CX (Conversational Agents) demo application using Desktop microphone for intent detection.

    IMPORTANT:
    1. You need to obtain your own keyfile.json from Google Cloud and place it in a location that the code can load.
       How to get a key? See https://social-ai-vu.github.io/social-interaction-cloud/external_apis/google_cloud.html
       Save the key in conf/google/google-key.json

    2. You need to create a Dialogflow CX agent and note:
       - Your agent ID (found in agent settings)
       - Your agent location (e.g., "global" or "us-central1")

    3. The Conversational Agents service needs to be running:
       - pip install social-interaction-cloud[dialogflow-cx]
       - run-dialogflow-cx

    Note: This uses the newer Dialogflow CX API (v3), which is different from the older Dialogflow ES (v2).
    """
    
    def __init__(self):
        # Call parent constructor (handles singleton initialization)
        super(DialogflowCXDemo, self).__init__()

        self.set_log_level(sic_logging.INFO)

        with open('config/gestures.json', 'r') as file:
            self.gesture_dict = json.load(file)
        print("Imported gesture dict")

        self.labels = list(self.gesture_dict.keys())
        print("extracted labels")

        self.text = ""
        self.category = ""
        self.gesture = ""
        
        self.setup()
    
    def setup(self):
        """Initialize and configure the desktop microphone and Conversational Agents service."""
        self.logger.info("Initializing Desktop")
        
        # Local desktop setup
        self.desktop = Desktop()
    
    def run(self):
        """Main application loop."""
        # Load a small, efficient zero-shot classifier
        self.logger.info("Classifier loaded in run()")
        try:
            # Demo starts
            self.logger.info("Requesting Stand posture")
            self.logger.info(" -- Ready -- ")

            while not self.shutdown_event.is_set():
                self.logger.info(" ----- Your turn to talk!")
                
                self.text = input("What does Nao say?\n")
                self.logger.info("Input received")
                print("In SIC on thread:", threading.current_thread().name)
                self.category = classify_gesture_api(self.text, self.labels)
                self.logger.info(f"Category is {self.category}")
                self.gesture = select_gesture(self.gesture_dict, self.category)
                self.logger.info(f"Gesture is {self.gesture}")
        except KeyboardInterrupt:
            self.logger.info("Demo interrupted by user")
        except Exception as e:
            self.logger.error("Exception: {}".format(e))
            import traceback
            traceback.print_exc()
        finally:
            self.shutdown()


if __name__ == "__main__":
    # Create and run the demo
    demo = DialogflowCXDemo()
    demo.run()

