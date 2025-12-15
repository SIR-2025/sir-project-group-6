# General imports
import time
import json
import threading
import google.generativeai as genai
import os
import pyaudio
from google.cloud import dialogflow_v2 as dialogflow
from google.oauth2 import service_account
from os.path import abspath, join

# Import our own created gesture functions
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
from sic_framework.devices.common_naoqi.naoqi_leds import (
    NaoFadeRGBRequest,
    NaoLEDRequest,
)
from sic_framework.devices.common_naoqi.naoqi_stiffness import Stiffness
from sic_framework.devices.common_naoqi.naoqi_tracker import (
    RemoveTargetRequest,
    StartTrackRequest,
    StopAllTrackRequest,
)

class Oli4v4Demo(SICApplication):
    """
    Oli4v4 Improvisational Comedy Demo for NAO Robot

    This module implements a full interactive improvisational comedy demo using
    a NAO robot. The system integrates:

    - Speech-to-text via Google Dialogflow (streaming STT)
    - Large Language Model responses via Google Gemini
    - Emotion/action classification using deberta-v3
    - Corresponding gesture selection/execution and Eye-LEDs color
    - Chest LED feedback for system state visualization
    - Face tracking and movement behaviors
    - Scene-based interaction structure with break phases
    - Detailed interaction logging for post-analysis
    """

    def __init__(self):
        """
        Initialize configuration, load resources, and prepare the demo.

        Responsibilities:
        - Configure logging
        - Load gesture definitions, scene prompts, and LED color mappings
        - Configure Gemini and Dialogflow credentials
        - Prepare interaction logging
        - Initialize NAO-related configuration
        """

        super(Oli4v4Demo, self).__init__()

        self.set_log_level(sic_logging.INFO)

        # NAO
        self.nao_ip = "192.168.0.231" #TODO: Change IP to Nao's current IP
        self.nao = None

        # Load gesture dictionary
        with open("config/gestures.json", "r") as f:
            gestures_raw = json.load(f)
        self.gesture_sitting = gestures_raw["sitting"]
        self.gesture_standing = gestures_raw["standing"]

        # Load scene configurations
        with open("config/scenes.json", "r") as f:
            self.scene_prompts = json.load(f)

        # Load eyecolor ditionary
        with open("config/eyecolors.json", "r") as f:
            gesture_colors = json.load(f)
        self.gesture_colors_sitting = gesture_colors["sitting"]
        self.gesture_colors_standing = gesture_colors["standing"]

        # Initialize LLM
        self.gemini_model = "gemini-2.5-flash"
        #TODO: Put gemini API key as txt in this location
        self.api_key_path = abspath(join("config", "api_key.txt"))

        # Setup logging to file for analysis
        logs_folder = abspath("logs")
        os.makedirs(logs_folder, exist_ok=True)
        self.data_log_path = os.path.join(logs_folder, f"interaction_log_nao{int(time.time())}.jsonl")
        self.logger.info(f"Data log will be saved to: {self.data_log_path}")

        # Initialize Dialogflow for speech
        self.google_keyfile = "config/google-key.json" #TODO: put your dialogflow keyfile at this location
        self.language_code = "en-US"
        self.sample_rate = 16000
        self.chunk = int(self.sample_rate / 10)
        #TODO: Change following values if you use your own dialogflow setup
        self.project_id = "oli-4-ee9p"
        self.location = "global"
        self.agent_id = "a7442d7b-fef8-4837-a27d-d29a1b4c8c27"
        self.session_id = "nao-session"
        self.environment = "draft"
        self.user_id = "nao-user"

        self.setup()

    def setup(self):
        """
        Perform runtime setup

        This includes:
        - Connecting to the NAO robot
        - Configuring the Gemini API
        - Initializing Dialogflow credentials and session
        """
        # Initializing connection with Nao
        self.logger.info("Initializing NAO...")
        try:
            self.nao = Nao(ip=self.nao_ip)
        except Exception as e:
            self.logger.warning(f"NAO connection failed: {e}")
            self.nao = None

        # Setup Gemini API
        with open(self.api_key_path) as f:
            key = f.read().strip()
        genai.configure(api_key=key)

        # Setup Dialogflow credentials
        self.df_credentials = service_account.Credentials.from_service_account_file(
            self.google_keyfile
        )

        self.df_session_path = (
            f"projects/{self.project_id}/locations/{self.location}/agent/"
            f"environments/{self.environment}/users/{self.user_id}/sessions/{self.session_id}"
        )

        self.df_client = dialogflow.SessionsClient(credentials=self.df_credentials)

    def df_mic_stream(self):
        """
        Generator yielding raw audio chunks from the local microphone.
        Audio format: 16-bit linear PCM Mono with 16 kHz sample rate
        Used as input for Dialogflow streaming speech-to-text.
        """
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            input_device_index=1,
            frames_per_buffer=self.chunk
        )

        print("Speak now...")

        try:
            while True:
                yield stream.read(self.chunk)
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

    def ask_gemini(self, messages):
        """
        Query the Gemini LLM with the current conversation history.

        Args:
            messages (list[dict]):
                Conversation history in the format:
                [{"role": "user"|"model", "content": str}, ...]

        Returns:
            str:
                Generated text response from Gemini, or ``None`` if an error occurs.
        """
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
        
    def streaming_stt(self):
        """
        Perform a single-turn streaming speech-to-text interaction.

        Uses Dialogflow streaming recognition to:
        - Print interim transcription results
        - Return the final recognized text once speech ends

        Returns:
            str:
                Final recognized user utterance, or None if failed.
        """

        # Build audio config request
        query_input = dialogflow.QueryInput(
            audio_config=dialogflow.InputAudioConfig(
                audio_encoding=dialogflow.AudioEncoding.AUDIO_ENCODING_LINEAR_16,
                sample_rate_hertz=self.sample_rate,
                language_code=self.language_code,
            )
        )

        # First request is config
        def request_generator():
            yield dialogflow.StreamingDetectIntentRequest(
                session=self.df_session_path,
                query_input=query_input,
            )

            # Subsequent ones: audio
            for chunk in self.df_mic_stream():
                yield dialogflow.StreamingDetectIntentRequest(input_audio=chunk)

        # Start streaming
        responses = self.df_client.streaming_detect_intent(
            requests=request_generator()
        )

        final_text = None
        last_print = ""

        for response in responses:
            if response.recognition_result:
                result = response.recognition_result
                txt = result.transcript

                # Handle interim + clear old lines
                if not result.is_final:
                    print("\r" + " " * len(last_print), end="\r")
                    text_out = f"[Interim] {txt}"
                    print(text_out, end="", flush=True)
                    last_print = text_out

                else:
                    # Clear interim line
                    print("\r" + " " * len(last_print), end="\r")
                    print(f"[Final] {txt}\n")
                    final_text = txt
                    break

        return final_text
    
    # Speak
    def speak(self, text):
        """
        Speak text using NAO's text-to-speech system. Falls back to printing text if NAO TTS fails.

        Args:
            text (str): Text to be spoken.
        """
        if not text:
            return
        try:
            self.nao.tts.request(NaoqiTextToSpeechRequest(text))
        except Exception:
            print("NAO TTS failed -> printing instead:")
            print(text)

    def log_interaction(self, scene_id, user_text, reply, gemini_time, classifier_time, category, gesture):
        """
        Log a single interaction turn to a JSONL file.

        Stored fields include:
        - Timestamps
        - Scene identifier
        - User input
        - LLM output
        - Timing metrics
        - Gesture classification results
        """
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
    
    def run_scene(self, scene_id, gestures, gesture_colors):
        """
        Run a conversational improvisation scene.

        Scene behavior:
        - Continuous loop of:
            - User speech input
            - LLM response generation
            - Gesture classification
            - Concurrent speech + animation execution
        - Face tracking is enabled (head only)
        - Scene ends when a predefined stopword is detected (set in scene config)

        Args:
            scene_id (str): Scene identifier key from scenes.json
            gestures (dict): Available gestures for this scene posture (stand or sit)
            gesture_colors (dict): LED colors mapped to gesture categories
        """
        # Initialize scene, conversation history and tracking
        system_prompt = self.scene_prompts[scene_id]["prompt"]
        stopword = self.scene_prompts[scene_id]["stopword"]
        labels = list(gestures.keys())

        history = [
            {"role": "model", "content": system_prompt}
        ]

        target_name = "Face"
        
        self.logger.info("Enabling head stiffness and starting face tracking...")
        # Enable stiffness so the head joint can be actuated
        self.nao.stiffness.request(Stiffness(stiffness=1.0, joints=["Head"]))
        self.nao.tracker.request(
            StartTrackRequest(target_name=target_name, size=0.2, mode="Head", effector="None")
        )

        self.logger.info(f"--- Starting Scene {scene_id} ---")
        self.speak("Starting next part...")

        while not self.shutdown_event.is_set():
            try:
                # ---------------------
                # USER INPUT
                # ---------------------
                self.logger.info("[START][INPUT]Setting LED to blue")
                light = self.nao.leds.request(NaoFadeRGBRequest("ChestLeds", 0, 0, 1, 0))
                user_text = None
                user_text = self.streaming_stt()

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
                light = self.nao.leds.request(NaoFadeRGBRequest("ChestLeds", 1, 0, 0, 0))
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
                light = self.nao.leds.request(NaoFadeRGBRequest("ChestLeds", 1, 1, 0, 0))
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
                light = self.nao.leds.request(NaoFadeRGBRequest("ChestLeds", 0, 1, 0, 0))
                if gesture and self.nao:
                    def gesture_thread():
                        self.logger.info(f"[GESTURE] Gesturing: {gesture}")
                        self.nao.motion.request(NaoqiAnimationRequest(gesture))

                    g_thread = threading.Thread(target=gesture_thread)
                    g_thread.start()
                    eye_color = gesture_colors[category]
                    light = self.nao.leds.request(NaoFadeRGBRequest("FaceLeds", eye_color[0], eye_color[1], eye_color[2], eye_color[3]))
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

                # END SCENE when stopword is said
                if stopword in user_text.lower():
                    self.speak("Okay, moving on.")
                    break

            except KeyboardInterrupt:
                raise  # handled by outer run()

    def run_break_scene(self, scene_id):
        """
        Run a non-verbal 'break' scene.

        Break scene behavior:
        - No LLM interaction
        - NAO performs face tracking with movement (walking)
        - System continuously listens for a stopword
        - Scene ends once stopword is detected

        Args:
            scene_id (str): Scene identifier key from scenes.json (purely used to retrieve stopword)
        """

        stopword = self.scene_prompts[scene_id]["stopword"].lower()

        self.logger.info(f"--- Starting BREAK Scene {scene_id} ---")
        self.speak("Let's take a short break.")

        # -----------------------
        # 1. Start tracking + walking
        # -----------------------
        try:
            self.logger.info("Starting Move tracking during break")

            move_rel_position = [-0.3, 0.0, 0.0, 0.1, 0.1, 0.1]

            self.nao.stiffness.request(Stiffness(stiffness=1.0, joints=["Head"]))
            self.nao.tracker.request(
                StartTrackRequest(
                    target_name="Face",
                    size=0.1,
                    mode="Move",        # walking behavior
                    effector="None",
                    move_rel_position=move_rel_position
                )
            )
        except Exception as e:
            self.logger.error(f"Could not start break tracking: {e}")

        # -----------------------
        # 2. Loop until stopword
        # -----------------------
        while not self.shutdown_event.is_set():

            # LISTEN
            self.logger.info("[BREAK] Listening for stopword…")
            
            light = self.nao.leds.request(NaoFadeRGBRequest("ChestLeds", 0, 0, 1, 0))
            user_text = None
            user_text = self.streaming_stt()

            if not user_text:
                user_text = input("Type here: ").strip()

            if not user_text:
                continue

            self.logger.info(f"[BREAK] Heard: {user_text}")

            # STOPWORD detected, end break
            if stopword in user_text.lower():
                self.nao.leds.request(NaoFadeRGBRequest("ChestLeds", 0, 1, 0, 0))
                self.speak("Okay, let's continue.")
                break

        # -----------------------
        # 3. Stop tracking when break ends
        # -----------------------
        try:
            self.logger.info("Ending break: stopping Move tracking")
            self.nao.tracker.request(StopAllTrackRequest())
            self.nao.tracker.request(RemoveTargetRequest("Face"))
        except Exception:
            pass

    def run(self):
        """
        Main execution of the demo.

        Sequence:
        - Initialize NAO posture and LEDs
        - Start with a break scene (waiting for start cue)
        - Run multiple improvisational scenes with breaks in between
        - End with a closing speech and bow animation

        Handles:
        - Shutdown on KeyboardInterrupt
        - Cleanup of tracking, LEDs, posture, and autonomy state
        """
        try:
            # Initial NAO setup
            if self.nao:
                self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
                time.sleep(1)

                self.logger.info("Requesting Eye LEDs to turn on")
                light = self.nao.leds.request(NaoLEDRequest("FaceLeds", True))
                light = self.nao.leds.request(NaoLEDRequest("ChestLeds", True))
                time.sleep(1)
                target_name = "Face"

            # --------------------
            # START (Break)
            # --------------------
            # NAO waits for actor to say start word to start with first scene
            self.logger.info("Scene: Start")
            if self.nao:
                self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
            self.run_break_scene("sc_break")

            # --------------------
            # SCENE 1: Specialist, Standing
            # --------------------
            self.logger.info("Scene: 1, Specialist")
            if self.nao:
                self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
            self.run_scene("sc_specialist", self.gesture_standing, self.gesture_colors_standing)

            # --------------------
            # BREAK 1
            # --------------------
            self.logger.info("Scene: Break 1")
            if self.nao:
                self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
            self.run_break_scene("sc_break")

            # --------------------
            # SCENE 2: Relationship, Standing
            # --------------------
            self.logger.info("Scene 2: Relation")
            if self.nao:
                self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
            self.run_scene("sc_relation", self.gesture_standing, self.gesture_colors_standing)

            # --------------------
            # BREAK 2
            # --------------------
            self.logger.info("Scene: Break 2")
            if self.nao:
                self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
            self.run_break_scene("sc_break")

            # --------------------
            # SCENE 3: Therapist, Sitting
            # --------------------
            self.logger.info("Scene 3: therapist")
            if self.nao:
                self.nao.motion.request(NaoPostureRequest("Sit", 0.5))
            self.run_scene("sc_therapist", self.gesture_sitting, self.gesture_colors_sitting)

            # --------------------
            # END: Finish
            # --------------------
            # Oli4 stands up and bows immediately afterwards
            self.logger.info("Scene: End Idle")

            if self.nao:
                self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
            time.sleep(1)

            self.speak("That's all I got for today, thank you for your attention!")
            self.nao.motion.request(NaoqiAnimationRequest("animations/Stand/Gestures/BowShort_1"))

        except KeyboardInterrupt:
            self.logger.info("Interrupted")
            # Unregister target face
            self.logger.info("Stopping face tracking...")
            self.nao.tracker.request(RemoveTargetRequest(target_name))
            
            # Stop tracking everything
            self.logger.info("Stopping all tracking...")
            self.nao.tracker.request(StopAllTrackRequest())

            self.nao.leds.request(NaoLEDRequest("ChestLeds", True))

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

                self.nao.leds.request(NaoLEDRequest("ChestLeds", True))

                self.nao.motion.request(NaoPostureRequest("Stand", 0.5))

                self.nao.autonomous.request(NaoRestRequest())
            self.shutdown()

if __name__ == "__main__":
    demo = Oli4v4Demo()
    demo.run()