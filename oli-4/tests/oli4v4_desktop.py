import time
import json
import threading
import google.generativeai as genai
import os
import pyaudio

from google.cloud import dialogflow_v2 as dialogflow
from google.oauth2 import service_account

# Gesture functions
from func.gesture import classify_gesture_api, select_gesture

# SIC framework
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging

from os.path import abspath, join


class Oli4v4DesktopDemo(SICApplication):
    def __init__(self):
        super(Oli4v4DesktopDemo, self).__init__()

        self.set_log_level(sic_logging.INFO)

        # No NAO robot
        self.nao = None

        # Gesture dictionary
        with open("config/gestures.json", "r") as f:
            gestures_raw = json.load(f)
        self.gesture_sitting = gestures_raw["sitting"]
        self.gesture_standing = gestures_raw["standing"]

        with open("config/scenes.json", "r") as f:
            self.scene_prompts = json.load(f)

        # Speech & LLM
        self.gemini_model = "gemini-2.5-flash"
        self.api_key_path = abspath(join("config", "api_key.txt"))

        # === Dialogflow STT ===
        self.google_keyfile = "config/google-key.json"
        self.language_code = "en-US"
        self.sample_rate = 16000
        self.chunk = int(self.sample_rate / 10)
        self.project_id = "oli-4-ee9p"
        self.location = "global"
        self.agent_id = "a7442d7b-fef8-4837-a27d-d29a1b4c8c27"
        self.session_id = "desktop-session"
        self.environment = "draft"
        self.user_id = "desktop-user"

        # Setup logging to file for analysis
        logs_folder = abspath("logs")
        os.makedirs(logs_folder, exist_ok=True)
        self.data_log_path = os.path.join(logs_folder, f"interaction_log_desktop{int(time.time())}.jsonl")

        self.logger.info(f"Data log will be saved to: {self.data_log_path}")

        self.setup()

    # -----------------------------
    # SETUP
    # -----------------------------
    def setup(self):
        self.logger.info("Initializing Desktop version...")

        # Gemini API
        with open(self.api_key_path) as f:
            key = f.read().strip()
        genai.configure(api_key=key)

        # Dialogflow credentials
        self.df_credentials = service_account.Credentials.from_service_account_file(
            self.google_keyfile
        )

        self.df_session_path = (
            f"projects/{self.project_id}/locations/{self.location}/agent/"
            f"environments/{self.environment}/users/{self.user_id}/sessions/{self.session_id}"
        )

        self.df_client = dialogflow.SessionsClient(credentials=self.df_credentials)


    # -----------------------------
    # DIALOGFLOW STREAMING MICROPHONE INPUT
    # -----------------------------
    def df_mic_stream(self):
        """Yields 16000 Hz audio chunks from desktop mic."""
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk,
        )

        print("🎤 Speak now...")

        try:
            while True:
                yield stream.read(self.chunk)
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()


    def streaming_stt(self):
        """
        Returns a single final transcript (same method as NAO version).
        Prints interim results.
        """
        query_input = dialogflow.QueryInput(
            audio_config=dialogflow.InputAudioConfig(
                audio_encoding=dialogflow.AudioEncoding.AUDIO_ENCODING_LINEAR_16,
                sample_rate_hertz=self.sample_rate,
                language_code=self.language_code,
            )
        )

        def request_generator():
            # First send config
            yield dialogflow.StreamingDetectIntentRequest(
                session=self.df_session_path,
                query_input=query_input,
            )

            # Then audio stream
            for chunk in self.df_mic_stream():
                yield dialogflow.StreamingDetectIntentRequest(input_audio=chunk)

        responses = self.df_client.streaming_detect_intent(
            requests=request_generator()
        )

        final_text = None
        last_print = ""

        for response in responses:
            if response.recognition_result:
                result = response.recognition_result
                txt = result.transcript

                # Interim result
                if not result.is_final:
                    print("\r" + " " * len(last_print), end="\r")
                    line = f"[Interim] {txt}"
                    print(line, end="", flush=True)
                    last_print = line

                else:
                    print("\r" + " " * len(last_print), end="\r")
                    print(f"[Final] {txt}\n")
                    final_text = txt
                    break

        return final_text


    # -----------------------------
    # GEMINI LLM
    # -----------------------------
    def ask_gemini(self, messages):
        try:
            model = genai.GenerativeModel(self.gemini_model)

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


    # -----------------------------
    # DESKTOP TTS
    # -----------------------------
    def speak(self, text):
        if not text:
            return
        print(f"\nTTS: {text}\n")


    # -----------------------------
    # LOGGING
    # -----------------------------
    def log_interaction(self, scene_id, user_text, reply, gemini_time, classifier_time, category, gesture):
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


    # -----------------------------
    # SCENE LOOP
    # -----------------------------
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
                # -------------------------
                # USER INPUT
                # -------------------------
                print("\nListening...\n")
                user_text = self.streaming_stt()

                if not user_text:
                    user_text = input("Type here: ").strip()

                if not user_text:
                    continue

                history.append({"role": "user", "content": user_text})

                # -------------------------
                # LLM RESPONSE
                # -------------------------
                t0_gemini = time.perf_counter()
                reply = self.ask_gemini(history)
                t1_gemini = time.perf_counter()

                gemini_time = t1_gemini - t0_gemini

                if not reply:
                    continue

                history.append({"role": "model", "content": reply})

                # -------------------------
                # GESTURE CLASSIFICATION
                # -------------------------
                t0_class = time.perf_counter()
                category = classify_gesture_api(reply, labels)
                gesture = select_gesture(gestures, category)
                classifier_time = time.perf_counter() - t0_class

                # -------------------------
                # SIMULATED ACTION OUTPUT
                # -------------------------
                print(f"[GESTURE] Would play gesture: {gesture}")
                self.speak(reply)

                # -------------------------
                # LOGGING
                # -------------------------
                self.log_interaction(
                    scene_id=scene_id,
                    user_text=user_text,
                    reply=reply,
                    gemini_time=gemini_time,
                    classifier_time=classifier_time,
                    category=category,
                    gesture=gesture
                )

                if stopword in user_text.lower():
                    self.speak("Okay, moving on.")
                    break

            except KeyboardInterrupt:
                raise


    # -----------------------------
    # RUN ALL SCENES
    # -----------------------------
    def run(self):
        try:
            self.logger.info("Desktop demo with Dialogflow STT started.")

            self.run_scene("sc_test", self.gesture_standing)
            self.run_scene("sc_test", self.gesture_sitting)
            self.run_scene("sc_break", self.gesture_standing)

            self.speak("That's all I got for today, thank you for your attention!")

        except KeyboardInterrupt:
            self.logger.info("Interrupted by user.")
        finally:
            self.logger.info("Shutting down desktop demo.")
            self.shutdown()


if __name__ == "__main__":
    demo = Oli4v4DesktopDemo()
    demo.run()
