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

class Oli4v3Demo(SICApplication):
    def __init__(self):
        super(Oli4v3Demo, self).__init__()

        self.set_log_level(sic_logging.INFO)

        # NAO
        self.nao_ip = "10.0.0.211"
        self.nao = None

        # Gesture dictionary
        with open("config/gestures.json", "r") as f:
            gestures_raw = json.load(f)
        self.gesture_sitting = gestures_raw["sitting"]
        self.gesture_standing = gestures_raw["standing"]

        with open("config/scenes.json", "r") as f:
            self.scene_prompts = json.load(f)


        # Speech & LLM
        self.recognizer = None
        self.gemini_model = "gemini-2.5-flash"
        self.api_key_path = abspath(join("config", "api_key.txt"))

        # Setup logging to file for analysis
        logs_folder = abspath("logs")
        os.makedirs(logs_folder, exist_ok=True)
        self.data_log_path = os.path.join(logs_folder, f"interaction_log_nao{int(time.time())}.jsonl")

        self.logger.info(f"Data log will be saved to: {self.data_log_path}")

        self.setup()

    # Gemini LLM call
    def ask_gemini(self, messages):
        try:
            model = genai.GenerativeModel(self.gemini_model)

            # Convert to Gemini-compatible structure
            gemini_msgs = []
            for msg in messages:
                gemini_msgs.append({
                    "role": msg["role"],
                    "parts": [{"text": msg["content"]}]
                })

            response = model.generate_content(gemini_msgs)
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

    def log_interaction(self, scene_id, user_text, reply, gemini_time, classifier_time, category, gesture):
        """Write a single interaction to the JSONL log file."""
        entry = {
            "timestamp": time.time(),
            "scene_id": scene_id,
            "user_text": user_text,
            "gemini_reply": reply,
            "gemini_response_time": gemini_time,
            "classifier_time": classifier_time,
            "gesture_category": category,
            "gesture_selected": gesture
        }
        with open(self.data_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    
    def run_scene(self, scene_id, gestures):
        system_prompt = self.scene_prompts[scene_id]["prompt"]
        stopword = self.scene_prompts[scene_id]["stopword"]
        labels = list(gestures.keys())

        history = [
            {"role": "model", "content": system_prompt}
        ]

        self.logger.info(f"--- Starting Scene {scene_id} ---")
        self.speak("Starting next part...")

        while not self.shutdown_event.is_set():
            try:
                # ---------------------
                # USER INPUT
                # ---------------------
                self.logger.info("[START][INPUT]Setting LED to blue")
                light = self.nao.leds.request(NaoFadeRGBRequest("FaceLeds", 0, 0, 1, 0))
                time.sleep(1)
                user_text = None
                if self.recognizer:
                    try:
                        with sr.Microphone() as mic:
                            audio = self.recognizer.listen(mic, timeout=8, phrase_time_limit=10)
                        user_text = self.recognizer.recognize_google(audio)
                        self.logger.info(f"You said: {user_text}")
                    except Exception:
                        pass

                if not user_text:
                    user_text = input("Type here: ").strip()

                if not user_text:
                    continue

                # Add USER message to conversation
                history.append({"role": "user", "content": user_text})

                self.logger.info("[DONE][INPUT]")

                # ---------------------
                # LLM RESPONSE
                # ---------------------
                self.logger.info("[START][LLM] Setting LED to red")
                light = self.nao.leds.request(NaoFadeRGBRequest("FaceLeds", 1, 0, 0, 0))
                t0_gemini = time.perf_counter()
                reply = self.ask_gemini(history)
                t1_gemini = time.perf_counter()
                gemini_time = t1_gemini - t0_gemini

                self.logger.info(f"[TIMING] Gemini response took {gemini_time:.3f}s")

                if not reply:
                    continue

                self.logger.info(f"Gemini reply: {reply}")

                # Add model reply to conversation
                history.append({"role": "model", "content": reply})

                self.logger.info("[DONE][LLM]")

                # ---------------------
                # GESTURE CLASSIFICATION
                # ---------------------
                self.logger.info("[START][CLASSIFIER] Start classifier, Set LED to yellow")
                light = self.nao.leds.request(NaoFadeRGBRequest("FaceLeds", 1, 1, 0, 0))
                t0_class = time.perf_counter()
                self.logger.info("[CLASSIFIER] STARTED classification")

                category = classify_gesture_api(reply, labels)
                gesture = select_gesture(gestures, category)
                t1_class = time.perf_counter()

                classifier_time = t1_class - t0_class
                self.logger.info(f"[CLASSIFIER] FINISHED in {classifier_time:.3f}s")
                self.logger.info(f"[CLASSIFIER] Category={category} | Gesture={gesture}")
                self.logger.info("[DONE][CLASSIFIER] Finished classification")

                # ---------------------
                # EXECUTE ACTION
                # ---------------------
                self.logger.info("[START][SPEAK + GESTURE] Setting LED to green")
                light = self.nao.leds.request(NaoFadeRGBRequest("FaceLeds", 0, 1, 0, 0))
                if gesture and self.nao:
                    def gesture_thread():
                        self.logger.info(f"[GESTURE] Gesturing: {gesture}")
                        self.nao.motion.request(NaoqiAnimationRequest(gesture))

                    g_thread = threading.Thread(target=gesture_thread)
                    g_thread.start()
                    self.speak(reply)
                    self.logger.info(f"[SPEAK] Nao said: {reply}")
                    g_thread.join()
                else:
                    self.speak(reply)
                
                # ---------------------
                # LOG DATA
                # ---------------------
                self.log_interaction(
                    scene_id=scene_id,
                    user_text=user_text,
                    reply=reply,
                    gemini_time=gemini_time,
                    classifier_time=classifier_time,
                    category=category,
                    gesture=gesture
                )

                # END SCENE on keyword
                if stopword in user_text.lower():
                    self.speak("Okay, moving on.")
                    break

            except KeyboardInterrupt:
                raise  # handled by outer run()

    # -------------------------------------------------------
    # RUN LOOP (changed to wait for gesture THEN speak+gesture)
    # -------------------------------------------------------
    def run(self):
        try:
            # Initial NAO setup
            if self.nao:
                self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
                time.sleep(1)

                self.logger.info("Requesting Eye LEDs to turn on")
                light = self.nao.leds.request(NaoLEDRequest("FaceLeds", True))
                time.sleep(1)

                target_name = "Face"
            
                self.logger.info("Enabling head stiffness and starting face tracking...")
                # Enable stiffness so the head joint can be actuated
                self.nao.stiffness.request(Stiffness(stiffness=1.0, joints=["Head"]))
                self.nao.tracker.request(
                    StartTrackRequest(target_name=target_name, size=0.2, mode="Head", effector="None")
                )

            # --------------------
            # START
            # --------------------
            # NAO waits for actor to say start word to start with first scene
            self.logger.info("Scene: Start")
            if self.nao:
                self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
            self.run_scene("sc_start", self.gesture_standing)

            # --------------------
            # SCENE 1 (Standing)
            # --------------------
            self.logger.info("Scene: 1, Sarcastic")
            if self.nao:
                self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
            self.run_scene("sc_sarcastic", self.gesture_standing)

            # --------------------
            # BREAK 1
            # --------------------
            self.logger.info("Scene: Break 1")
            if self.nao:
                self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
            self.run_scene("sc_break", self.gesture_standing)

            # --------------------
            # SCENE 2 (sitting)
            # --------------------
            self.logger.info("Scene 2: Caring")
            if self.nao:
                self.nao.motion.request(NaoPostureRequest("Sit", 0.5))
            self.run_scene("sc_kind", self.gesture_sitting)

            # --------------------
            # BREAK 2
            # --------------------
            self.logger.info("Scene: Break 2")
            if self.nao:
                self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
            self.run_scene("sc_break", self.gesture_standing)

            # --------------------
            # SCENE 3 (standing)
            # --------------------
            self.logger.info("Scene 3: Short-tempered")
            self.run_scene("sc_shorttemper", self.gesture_standing)

            # --------------------
            # END: Idle
            # --------------------
            self.logger.info("Scene: End Idle")
            if self.nao:
                self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
            self.run_scene("sc_break", self.gesture_standing)

            # --------------------
            # END: Finish
            # --------------------
            self.logger.info("Scene: End Idle")

            self.speak("That's all I got for today, thank you for your attention!")
            self.nao.motion.request(NaoqiAnimationRequest("animations/Stand/Gestures/BowShort_1"))

            self.logger.info("Stopping face tracking...")
            self.nao.tracker.request(RemoveTargetRequest(target_name))
            
            # Stop tracking everything
            self.logger.info("Stopping all tracking...")
            self.nao.tracker.request(StopAllTrackRequest())
            
            self.logger.info("Tracker demo completed successfully")

        except KeyboardInterrupt:
            self.logger.info("Interrupted")
            # Unregister target face
            self.logger.info("Stopping face tracking...")
            self.nao.tracker.request(RemoveTargetRequest(target_name))
            
            # Stop tracking everything
            self.logger.info("Stopping all tracking...")
            self.nao.tracker.request(StopAllTrackRequest())

            self.nao.leds.request(NaoLEDRequest("FaceLeds", True))

            self.nao.motion.request(NaoPostureRequest("Stand", 0.5))

            self.nao.autonomous.request(NaoRestRequest())
            self.shutdown()

        finally:
            if self.nao:
                # Unregister target face
                self.logger.info("Stopping face tracking...")
                self.nao.tracker.request(RemoveTargetRequest(target_name))
                
                # Stop tracking everything
                self.logger.info("Stopping all tracking...")
                self.nao.tracker.request(StopAllTrackRequest())

                self.nao.leds.request(NaoLEDRequest("FaceLeds", True))

                self.nao.motion.request(NaoPostureRequest("Stand", 0.5))

                self.nao.autonomous.request(NaoRestRequest())
            self.shutdown()


if __name__ == "__main__":
    demo = Oli4v3Demo()
    demo.run()
