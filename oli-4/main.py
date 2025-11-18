import time
import json
import random
import threading
import numpy as np
import speech_recognition as sr
import google.generativeai as genai

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


class Oli4v1Demo(SICApplication):
    """
    Combined demo:
    - Speech input (mic or keyboard)
    - Gemini LLM produces reply
    - NAO speaks the reply
    - Text is classified into gesture category
    - NAO performs matching gesture animation
    TODO: add parallelization after receiving reply
    """

    def __init__(self):
        super(Oli4v1Demo, self).__init__()

        self.set_log_level(sic_logging.INFO)

        # NAO
        self.nao_ip = "10.0.0.242"
        self.nao = None

        # Gesture dictionary
        with open("config/gestures.json", "r") as f:
            self.gesture_dict = json.load(f)
        self.labels = list(self.gesture_dict.keys())

        # Speech & LLM
        self.recognizer = None
        self.gemini_model = "gemini-2.5-flash"
        self.api_key_path = abspath(join("config", "api_key.txt"))

        self.setup()

    # -------------------------------
    # Gemini Response
    # -------------------------------
    def ask_gemini(self, text):
        if not text:
            return None

        try:
            model = genai.GenerativeModel(
                self.gemini_model,
                system_instruction="""
                You are a sarcastic, witty comedian with dry humor.
                Keep replies SHORT, punchy, improv-friendly.
                """
            )
            response = model.generate_content(text)
            reply = response.text.strip()
            return reply
        except Exception as e:
            self.logger.error(f"Gemini error: {e}")
            return None

    # -------------------------------
    # NAO Speak
    # -------------------------------
    def speak(self, text):
        if not text:
            return

        try:
            self.nao.tts.request(NaoqiTextToSpeechRequest(text))
        except Exception:
            print("NAO TTS failed -> printing instead:")
            print(text)

    # -------------------------------
    # Setup
    # -------------------------------
    def setup(self):
        self.logger.info("Initializing NAO...")

        # Connect NAO
        try:
            self.nao = Nao(ip=self.nao_ip)
            self.logger.info(f"Connected to NAO at {self.nao_ip}")
        except Exception as e:
            self.logger.warning(f"Could not connect to NAO: {e}")
            self.nao = None

        # Mic
        try:
            self.recognizer = sr.Recognizer()
            with sr.Microphone() as mic:
                self.recognizer.adjust_for_ambient_noise(mic, duration=0.5)
            self.logger.info("Microphone initialized")
        except Exception as e:
            self.logger.warning(f"Mic init failed: {e}")
            self.recognizer = None

        # Gemini
        with open(self.api_key_path) as f:
            key = f.read().strip()
        genai.configure(api_key=key)
        self.logger.info("Gemini configured")

    # -------------------------------
    # Main Loop
    # -------------------------------
    def run(self):
        try:
            # Put NAO into Stand
            if self.nao:
                self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
                time.sleep(1)

            self.speak("I'm ready whenever you are.")
            self.logger.info("Ready")

            while not self.shutdown_event.is_set():

                # ---------------------------
                # Get user speech or input
                # ---------------------------
                self.logger.info("Listening or type input...")

                user_text = None

                # Use microphone
                if self.recognizer:
                    try:
                        with sr.Microphone() as mic:
                            audio = self.recognizer.listen(mic, timeout=8, phrase_time_limit=10)
                        user_text = self.recognizer.recognize_google(audio)
                        self.logger.info(f"User said: {user_text}")
                    except Exception:
                        pass

                # Keyboard fallback
                if not user_text:
                    user_text = input("Type here: ").strip()

                if not user_text:
                    continue

                # ---------------------------
                # GEMINI RESPONSE
                # ---------------------------
                reply = self.ask_gemini(user_text)

                if not reply:
                    self.logger.warning("Gemini produced no reply.")
                    continue

                # NAO speaks
                self.speak(reply)
                self.logger.info(f"Gemini: {reply}")

                # ---------------------------
                # GESTURE CLASSIFICATION
                # ---------------------------
                category = classify_gesture_api(reply, self.labels)
                gesture = select_gesture(self.gesture_dict, category)

                self.logger.info(f"Gesture category: {category}")
                self.logger.info(f"Selected gesture: {gesture}")

                # Perform gesture
                if self.nao:
                    self.nao.motion.request(NaoqiAnimationRequest(gesture))

        except KeyboardInterrupt:
            self.logger.info("Interrupted")
        finally:
            if self.nao:
                self.nao.leds.request(NaoLEDRequest("FaceLeds", True))
                self.nao.autonomous.request(NaoRestRequest())
            self.shutdown()


if __name__ == "__main__":
    demo = Oli4v1Demo()
    demo.run()
