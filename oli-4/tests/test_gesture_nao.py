from func.gesture import classify_gesture_api, select_gesture
# Import basic preliminaries
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging

# Import the device(s) we will be using
from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_autonomous import NaoRestRequest
from sic_framework.devices.common_naoqi.naoqi_leds import NaoLEDRequest
from sic_framework.devices.nao_stub import NaoStub

# Import message types and requests
from sic_framework.devices.common_naoqi.naoqi_motion import (
    NaoPostureRequest,
    NaoqiAnimationRequest,
)

# Import libraries necessary for the demo
import time
import json
from transformers import pipeline
import random
import threading

class NaoGestureDemo(SICApplication):
    """
    NAO motion demo application.
    Demonstrates how to make NAO perform predefined postures and animations.
    
    For a list of postures, see NaoPostureRequest class or
    http://doc.aldebaran.com/2-4/family/robots/postures_robot.html#robot-postures
    
    A list of all NAO animations can be found here:
    http://doc.aldebaran.com/2-4/naoqi/motion/alanimationplayer-advanced.html#animationplayer-list-behaviors-nao
    """
    
    def __init__(self):
        # Call parent constructor (handles singleton initialization)
        super(NaoGestureDemo, self).__init__()
        
        # Demo-specific initialization
        self.nao_ip = "10.0.0.242"
        self.nao = None

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
        """Initialize and configure the NAO robot."""
        self.logger.info("Starting NAO Gesture from Dialogue Demo...")
        
        # Initialize the NAO robot
        self.nao = Nao(ip=self.nao_ip)
    
    def run(self):
        """Main application loop."""
        # Load a small, efficient zero-shot classifier
        try:
            # Demo starts
            self.logger.info("Requesting Stand posture")
            self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
            time.sleep(1)
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
                self.nao.motion.request(NaoqiAnimationRequest(self.gesture))
                
        except KeyboardInterrupt:
            self.logger.info("Demo interrupted by user")
        except Exception as e:
            self.logger.error("Exception: {}".format(e))
            import traceback
            traceback.print_exc()
        finally:
            # Reset the eyes when necessary
            self.nao.leds.request(NaoLEDRequest("FaceLeds", True))
            # always end with a rest, whenever you reach the end of your code
            self.nao.autonomous.request(NaoRestRequest())
            self.shutdown()

if __name__ == "__main__":
    # Create and run the demo
    demo = NaoGestureDemo()
    demo.run()
