import time
import json
import threading
import speech_recognition as sr
import google.generativeai as genai
import os

# Gesture functions
from func.gesture import classify_gesture_api, select_gesture

# SIC framework
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging

from sic_framework.devices import Nao
from sic_framework.devices.nao import NaoqiTextToSpeechRequest
from sic_framework.devices.common_naoqi.naoqi_motion import (
    NaoPostureRequest,
    NaoqiAnimationRequest
)
from sic_framework.devices.common_naoqi.naoqi_autonomous import NaoRestRequest
from sic_framework.devices.common_naoqi.naoqi_leds import NaoLEDRequest

from os.path import abspath, join

from sic_framework.devices.common_naoqi.naoqi_leds import (
    NaoFadeRGBRequest,
    NaoLEDRequest,
)

# Import message types and requests
from sic_framework.devices.common_naoqi.naoqi_stiffness import Stiffness
from sic_framework.devices.common_naoqi.naoqi_tracker import (
    RemoveTargetRequest,
    StartTrackRequest,
    StopAllTrackRequest,
)

from sic_framework.devices.common_naoqi.naoqi_motion import NaoqiBreathingRequest


class NaoTrackerDemo(SICApplication):
    """
    NAO tracker demo application.
    Demonstrates how to make NAO:
    1. Track a face with its head.
    2. Move its end-effector (both arms in this case) to track a red ball, given a position relative to the ball.
    """
    
    def __init__(self):
        # Call parent constructor (handles singleton initialization)
        super(NaoTrackerDemo, self).__init__()
        
        # Demo-specific initialization
        self.nao_ip = "10.0.0.212"
        self.nao = None
        
        # Log files will only be written if set_log_file is called. Must be a valid full path to a directory.
        # self.set_log_file("/Users/apple/Desktop/SAIL/SIC_Development/sic_applications/demos/nao/logs")

        with open("config/gestures.json", "r") as f:
            gestures_raw = json.load(f)
        self.sitting = gestures_raw["sitting"]
        
        self.setup()
    
    def setup(self):
        """Initialize and configure the NAO robot."""
        self.logger.info("Starting NAO Tracker Demo...")
        
        # Connect to NAO
        self.nao = Nao(ip=self.nao_ip)
    
    def run(self):
        try:
            
            # Make NAO Stand before starting
            self.logger.info("Putting NAO into Stand posture...")
            self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
            time.sleep(1)

            self.logger.info("===== Starting Standing Gesture Test =====")

            for category, gesture_list in self.standing.items():
                self.logger.info(f"--- Category: {category} ---")
                print(f"\n=== CATEGORY: {category} ===\n")

                for gesture in gesture_list:
                    print(f"Testing gesture: {gesture}")
                    self.logger.info(f"[TEST] Running gesture: {gesture}")

                    try:
                        self.nao.motion.request(NaoqiAnimationRequest(gesture))
                    except Exception as e:
                        self.logger.error(f"Error playing gesture {gesture}: {e}")

                    time.sleep(2)  # small delay before next gesture

            self.logger.info("===== Finished Standing Gesture Test =====")

            # self.logger.info("Stopping all tracking...")
            # self.nao.tracker.request(StopAllTrackRequest())

            # self.shutdown()
            # light = self.nao.leds.request(NaoFadeRGBRequest("ChestLeds", 0, 1, 0, 0))
            # target_name = "Face"

            # self.logger.info("Enabling head stiffness and starting face tracking...")
            # self.nao.stiffness.request(Stiffness(stiffness=1.0, joints=["Head"]))

            # desired_distance = 0.5  # meters
            # move_rel_position = [-0.3, 0.0, 0.0, 0.1, 0.1, 0.1]

            # self.nao.tracker.request(
            #     StartTrackRequest(
            #         target_name=target_name,
            #         size=0.1,
            #         mode="Move",
            #         effector="None",
            #         move_rel_position=move_rel_position,
            #     )
            # )

            # stop tracking
            self.logger.info("Stopping all tracking...")
            self.nao.tracker.request(StopAllTrackRequest())

            self.nao.autonomous.request(NaoRestRequest())

            self.logger.info("Tracker demo completed successfully")
        except Exception as e:
            self.logger.error("Error in tracker demo: {}".format(e=e))
        finally:
            self.shutdown()


if __name__ == "__main__":
    # Create and run the demo
    demo = NaoTrackerDemo()
    demo.run()
