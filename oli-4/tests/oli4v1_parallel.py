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

    # Gemini LLM call
    def ask_gemini(self, text):
        if not text:
            return None

        try:
            model = genai.GenerativeModel(
                self.gemini_model,
                system_instruction="""
                You are a sarcastic, witty comedian with dry humor.
                Keep replies SHORT and punchy.
                """
            )
            response = model.generate_content(text)
            return response.text.strip()

        except Exception as e:
            self.logger.error(f"Gemini error: {e}")
            return None

    # Speak
    def speak(self, text):
        if not text:
            return
        try:
            self.nao.tts.request(NaoqiTextToSpeechRequest(text))
        except Exception:
            print("NAO TTS failed -> printing instead:")
            print(text)

    def setup(self):
        self.logger.info("Initializing NAO...")
        try:
            self.nao = Nao(ip=self.nao_ip)
        except Exception as e:
            self.logger.warning(f"NAO connection failed: {e}")
            self.nao = None

        # Mic
        try:
            self.recognizer = sr.Recognizer()
            with sr.Microphone() as mic:
                self.recognizer.adjust_for_ambient_noise(mic, duration=0.5)
        except Exception as e:
            self.logger.warning(f"Mic init failed: {e}")
            self.recognizer = None

        # Gemini API
        with open(self.api_key_path) as f:
            key = f.read().strip()
        genai.configure(api_key=key)

    # -------------------------------------------------------
    # RUN LOOP WITH PARALLEL GESTURE & FULL TIMING
    # -------------------------------------------------------
    def run(self):
        try:
            if self.nao:
                self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
                time.sleep(1)

            self.speak("I'm ready whenever you are.")
            self.logger.info("Ready")

            while not self.shutdown_event.is_set():

                # ---------------------------
                # Get input
                # ---------------------------
                user_text = None

                # if self.recognizer:
                #     try:
                #         with sr.Microphone() as mic:
                #             audio = self.recognizer.listen(mic, timeout=8, phrase_time_limit=10)
                #         user_text = self.recognizer.recognize_google(audio)
                #     except Exception:
                #         pass

                if not user_text:
                    user_text = input("Type here: ").strip()

                if not user_text:
                    continue

                # ----------------------------------------------------
                # GEMINI RESPONSE + TIMING
                # ----------------------------------------------------
                t0_gemini = time.perf_counter()
                reply = self.ask_gemini(user_text)
                t1_gemini = time.perf_counter()
                self.logger.info(f"[TIMING] Gemini response took {t1_gemini - t0_gemini:.3f}s")

                if not reply:
                    continue

                # ----------------------------------------------------
                # CLASSIFICATION + GESTURE THREAD (combined)
                # ----------------------------------------------------
                gesture_result = {"gesture": None, "t_class_end": None}
                speech_times = {"t1_speak": None}  # shared timing

                def classifier_and_gesture_thread():
                    # --- CLASSIFICATION ---
                    t0_class = time.perf_counter()
                    self.logger.info("[CLASSIFIER] STARTED classification")

                    category = classify_gesture_api(reply, self.labels)
                    gesture = select_gesture(self.gesture_dict, category)

                    t_class_end = time.perf_counter()
                    gesture_result["gesture"] = gesture
                    gesture_result["t_class_end"] = t_class_end

                    self.logger.info(f"[CLASSIFIER] FINISHED in {t_class_end - t0_class:.3f}s")
                    self.logger.info(f"[CLASSIFIER] → Gesture={gesture}")

                    # --- GESTURE EXECUTION (immediate, even mid-speech!) ---
                    if gesture and self.nao:

                        # If speech hasn't ended yet, this will be negative (good!)
                        t1_speak_val = speech_times["t1_speak"]
                        if t1_speak_val is None:
                            pause = float('-inf')  # gesture before speech end
                        else:
                            pause = t_class_end - t1_speak_val

                        self.logger.info(f"[TIMING] Delay speech end → gesture start: {pause:.3f}s")

                        self.logger.info(f"[GESTURE] Executing gesture: {gesture}")
                        self.nao.motion.request(NaoqiAnimationRequest(gesture))

                classifier = threading.Thread(target=classifier_and_gesture_thread)
                classifier.start()

                # ----------------------------------------------------
                # SPEECH (runs in parallel)
                # ----------------------------------------------------
                t0_speak = time.perf_counter()
                self.logger.info("[SPEAK] STARTED speaking")
                self.logger.info(f"Nao: {reply}")
                self.speak(reply)
                t1_speak = time.perf_counter()
                speech_times["t1_speak"] = t1_speak  # <-- store it here
                self.logger.info(f"[SPEAK] FINISHED in {t1_speak - t0_speak:.3f}s")

                # Wait for classifier (gesture runs inside it)
                classifier.join()

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
