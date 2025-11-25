import time
import json
import speech_recognition as sr
import google.generativeai as genai
import pyttsx3
import os

# Gesture functions
from func.gesture import classify_gesture_api, select_gesture

# SIC framework
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging

from os.path import abspath, join

class Oli4v3DesktopDemo(SICApplication):
    def __init__(self):
        super(Oli4v3DesktopDemo, self).__init__()

        self.set_log_level(sic_logging.INFO)

        # No NAO Robot
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
        self.data_log_path = os.path.join(logs_folder, f"interaction_log_desktop{int(time.time())}.jsonl")

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

    # Desktop TTS
    def speak(self, text):
        if not text:
            return
        print(f"TTS: {text}")
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"TTS error: {e}")

    def setup(self):
        self.logger.info("Initializing Desktop version...")

        # Mic
        try:
            self.recognizer = sr.Recognizer()
            with sr.Microphone() as mic:
                self.recognizer.adjust_for_ambient_noise(mic, duration=0.5)
            self.logger.info("Microphone initialized.")
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

        # Start a NEW conversation for this scene
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
                self.logger.info("[START][INPUT]")
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

                self.logger.info("[END][INPUT]")

                # Add USER message to conversation
                history.append({"role": "user", "content": user_text})

                # ---------------------
                # LLM RESPONSE
                # ---------------------
                self.logger.info("[START][LLM]")
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

                # ---------------------
                # GESTURE CLASSIFICATION
                # ---------------------
                t0_class = time.perf_counter()
                self.logger.info("[START][CLASSIFIER] STARTED classification")

                category = classify_gesture_api(reply, labels)
                gesture = select_gesture(gestures, category)

                t1_class = time.perf_counter()

                classifier_time = t1_class - t0_class
                self.logger.info(f"[CLASSIFIER] FINISHED in {classifier_time:.3f}s")
                self.logger.info(f"[CLASSIFIER] Category={category} | Gesture={gesture}")
                self.logger.info("[DONE][CLASSIFIER]")

                # ---------------------
                # EXECUTE ACTION
                # ---------------------
                self.logger.info(f"[GESTURE] (Simulated) Would trigger: {gesture}")
                self.logger.info("[START][SPEAK]")
                self.speak(reply)
                self.logger.info("[END][SPEAK]")

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

                self.logger.info("--------------------------------------------------------------------------\n")

            except KeyboardInterrupt:
                raise

    def run(self):
        try:
            self.logger.info("Desktop demo started (no NAO robot).")

            # SCENE: Start
            self.logger.info("Scene: Start")
            self.run_scene("sc_start", self.gesture_standing)

            # SCENE 1
            self.logger.info("Scene: 1, Sarcastic")
            self.run_scene("sc_sarcastic", self.gesture_standing)

            # BREAK 1
            self.logger.info("Scene: Break 1")
            self.run_scene("sc_break", self.gesture_standing)

            # SCENE 2
            self.logger.info("Scene 2: Caring (sitting gestures)")
            self.run_scene("sc_kind", self.gesture_sitting)

            # BREAK 2
            self.logger.info("Scene: Break 2")
            self.run_scene("sc_break", self.gesture_standing)

            # SCENE 3
            self.logger.info("Scene 3: Short-tempered")
            self.run_scene("sc_shorttemper", self.gesture_standing)

            # END
            self.logger.info("Scene: End Idle")
            self.run_scene("sc_break", self.gesture_standing)

            self.speak("That's all I got for today, thank you for your attention!")

        except KeyboardInterrupt:
            self.logger.info("Interrupted by user.")
        finally:
            self.logger.info("Shutting down desktop demo.")
            self.shutdown()


if __name__ == "__main__":
    demo = Oli4v3DesktopDemo()
    demo.run()
