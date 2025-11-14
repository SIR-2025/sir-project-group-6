# Import basic preliminaries
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging

# Import the device(s) we will be using
from sic_framework.devices import Nao
from sic_framework.devices.nao import NaoqiTextToSpeechRequest
from sic_framework.devices.common_naoqi.naoqi_motion import NaoqiAnimationRequest, NaoPostureRequest

# Import the service(s) we will be using
"""from sic_framework.services.dialogflow_cx.dialogflow_cx import (
    DialogflowCX,
    DialogflowCXConf,
    DetectIntentRequest,
    QueryResult,
    RecognitionResult,
)"""

import google.generativeai as genai

import speech_recognition as sr
import pyttsx3


# Import libraries necessary for the demo
import json
from os.path import abspath, join
import numpy as np


class NaoGeminiDemo(SICApplication):
    """
    NAO Dialogflow CX demo application.
    
    Demonstrates NAO robot picking up your intent and replying according to your 
    trained Dialogflow CX agent.

    IMPORTANT:
    1. You need to obtain your own keyfile.json from Google Cloud and place it in conf/google/
       How to get a key? See https://social-ai-vu.github.io/social-interaction-cloud/external_apis/google_cloud.html
       Save the key in conf/google/google-key.json

    2. You need a trained Dialogflow CX agent:
       - Create an agent at https://dialogflow.cloud.google.com/cx/
       - Add intents with training phrases
       - Train the agent
       - Note the agent ID and location

    3. The Dialogflow CX service needs to be running:
       - pip install social-interaction-cloud[dialogflow-cx]
       - run-dialogflow-cx

    Note: This uses Dialogflow CX (v3), which is different from Dialogflow ES (v2).
    """
    
    def __init__(self):
        # Call parent constructor (handles singleton initialization)
        super(NaoGeminiDemo, self).__init__()
        
        # Demo-specific initialization
        self.nao_ip = "10.0.0.242"  # TODO: Replace with your NAO's IP address
        self.gemini_keyfile_path = abspath(join("..", "config", "api_key_joos.json"))
        self.nao = None
        self.gemini = None
        self.session_id = np.random.randint(10000)

        self.set_log_level(sic_logging.INFO)
        
        # Log files will only be written if set_log_file is called. Must be a valid full path to a directory.
        # self.set_log_file("/Users/apple/Desktop/SAIL/SIC_Development/sic_applications/demos/nao/logs")
        self.recognizer = None
        self.tts_engine = None
        self.setup()

    #--------OLD ASK GEMINI FUNCTION-------------    
    # def ask_gemini(self, message):
    #     """
    #     Callback function for Dialogflow CX recognition results.
        
    #     Args:
    #         message: The Dialogflow CX recognition result message.
        
    #     Returns:
    #         None
    #     """
    #     if message:
    #         #response = genai.generate_text(self.gemini_model, message)
    #         if hasattr(message, 'recognition_results') and message.recognition_results:
    #             rr = message.recognition_result
    #             if hasattr(rr, 'is_final') and rr.is_final:
    #                 if hasattr(rr, 'transcript'):
    #                     self.logger.info("Transcript: {transcript}".format(transcript=rr.transcript))
    #--------------------END OLD--------------------------

    # ---------NEW ASK GEMINI FUNCION---------------
    def ask_gemini(self, message):
        """Accept either a Dialogflow recognition message or a plain transcript string.
        Sends the transcript to Gemini and returns the assistant reply string."""
        # extract transcript from either a string or Dialogflow-style message
        if isinstance(message, str):
            transcript = message.strip()
        else:
            if not message:
                return None
            rr = getattr(message, "recognition_result", None)
            if not rr or not getattr(rr, "is_final", False):
                return None
            transcript = getattr(rr, "transcript", None)

        if not transcript:
            return None

        self.logger.info("Transcript: {}".format(transcript))

        try:
            model_name = getattr(self, "gemini_model", "gemini-2.5-flash")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(transcript)
            reply = getattr(response, "text", str(response))
            self.logger.info("Gemini reply: {}".format(reply))
            return reply
        except Exception as e:
            self.logger.error("Gemini call failed: {}".format(e))
            return None
    #----------END NEW------------

    def speak(self, text):
        """Route speech output to NAO if connected, otherwise laptop TTS or print."""
        if not text:
            return
        if getattr(self, "nao", None):
            try:
                self.nao.tts.request(NaoqiTextToSpeechRequest(text))
                return
            except Exception as e:
                self.logger.warning("NAO TTS failed, falling back to laptop TTS: {}".format(e))
        if getattr(self, "tts_engine", None):
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                return
            except Exception as e:
                self.logger.warning("Local TTS failed: {}".format(e))
        print("TTS:", text)

    def setup(self):
        """Initialize and configure NAO robot and Dialogflow CX."""
        self.logger.info("Initializing NAO robot...")
       
        # Try to initialize NAO; if it fails continue using laptop mic/tts
        nao_mic = None
        try:
            self.nao = Nao(ip=self.nao_ip)
            nao_mic = self.nao.mic
            self.logger.info("NAO device initialized at {}".format(self.nao_ip))
        except Exception as e:
            self.logger.warning("Could not initialize NAO device (continuing without robot): {}".format(e))
            self.nao = None

        # Initialize laptop microphone recognizer
        try:
            self.recognizer = sr.Recognizer()
            # optional: adjust for ambient noise
            with sr.Microphone() as mic:
                self.recognizer.adjust_for_ambient_noise(mic, duration=0.5)
            self.logger.info("Laptop microphone (SpeechRecognition) initialized.")
        except Exception as e:
            self.logger.warning("Could not initialize laptop microphone: {}".format(e))
            self.recognizer = None
        
        # Initialize laptop TTS (pyttsx3) as fallback
        try:
            self.tts_engine = pyttsx3.init()
            self.logger.info("Laptop TTS (pyttsx3) initialized.")
        except Exception as e:
            self.logger.warning("Could not initialize laptop TTS: {}".format(e))
            self.tts_engine = None

        self.logger.info("Initializing Gemini CX...")
        
        # Load the key json file
        with open(self.gemini_keyfile_path) as f:
            keyfile_json = json.load(f)

        # configure gemini API key if present in the json (expects {"api_key": "<KEY>"})
        api_key = keyfile_json.get("api_key") if isinstance(keyfile_json, dict) else None
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.logger.info("Configured Gemini API key from {}".format(self.gemini_keyfile_path))
            except Exception as e:
                self.logger.warning("Failed to configure Gemini API key: {}".format(e))

        self.gemini_model = "gemini-2.5-flash"  
        
        # Agent configuration
        # TODO: Replace with your agent details (use verify_dialogflow_cx_agent.py to find them)
        #agent_id = "XXX"  # Replace with your agent ID
        #location = "XXX"  # Replace with your agent location if different
        
        # Create configuration for Dialogflow CX
        # Note: NAO uses 16000 Hz sample rate (not 44100 like desktop)
        """dialogflow_conf = DialogflowCXConf(
            keyfile_json=keyfile_json,
            agent_id=agent_id,
            location=location,
            sample_rate_hertz=16000,  # NAO's microphone sample rate
            language="en"
        )"""
        
        # Initialize Dialogflow CX with NAO's microphone as input
        #self.gemini_cx = DialogflowCX(conf=dialogflow_conf, input_source=nao_mic)
        
        #self.logger.info("Initialized Dialogflow CX... registering callback function")
        # Register a callback function to handle recognition results
        #self.gemini.register_callback(callback=self.ask_gemini)
    
    def run(self):
        """Main application loop."""
        try:
            # Demo starts — use speak() so it works with or without NAO
            self.speak("What's up")
            self.logger.info(" -- Ready -- ")
            
            while not self.shutdown_event.is_set():
                self.logger.info(" ----- Your turn to talk!")
                
                if self.recognizer:
                    try:
                        with sr.Microphone() as mic:
                            audio = self.recognizer.listen(mic, timeout=8, phrase_time_limit=10)
                        user_text = self.recognizer.recognize_google(audio)
                        self.logger.info("ASR (laptop mic) result: {}".format(user_text))
                    except sr.WaitTimeoutError:
                        self.logger.info("Listening timed out, no speech detected.")
                        user_text = None
                    except sr.UnknownValueError:
                        self.logger.info("Could not understand audio from laptop mic.")
                        user_text = None
                    except Exception as e:
                        self.logger.warning("Laptop mic ASR error: {}".format(e))
                        user_text = None

                if not user_text:
                    try:
                        user_text = input("You: ").strip()
                    except EOFError:
                        self.logger.info("Input stream closed, exiting.")
                        break

                if not user_text:
                    self.logger.info("No input received, continuing...")
                    continue

                # Send to Gemini
                self.logger.info("Sending to Gemini: {}".format(user_text))
                gemini_reply = self.ask_gemini(user_text)
                self.logger.info("Gemini reply: {}".format(gemini_reply))

                # Speak the Gemini reply (NAO if connected, otherwise laptop)
                if gemini_reply is None:
                    self.logger.warning("Gemini returned no reply")
                else:
                    self.speak(gemini_reply)

                """# Request intent detection with the current session
                reply = self.gemini.request(DetectIntentRequest(self.session_id))
                
                # Log the detected intent
                if reply.intent:
                    self.logger.info("The detected intent: {intent} (confidence: {conf})".format(
                        intent=reply.intent,
                        conf=reply.intent_confidence if reply.intent_confidence else "N/A"
                    ))
                    
                    # Perform gestures based on detected intent (non-blocking)
                    if reply.intent == "welcome_intent":
                        self.logger.info("Welcome intent detected - performing wave gesture")
                        # Use send_message for non-blocking gesture execution
                        # This allows the TTS to speak while the gesture is performed
                        self.nao.motion.request(NaoPostureRequest("Stand", 0.5), block=False)
                        self.nao.motion.request(NaoqiAnimationRequest("animations/Stand/Gestures/Hey_1"), block=False)
                else:
                    self.logger.info("No intent detected")
                
                # Log the transcript
                if reply.transcript:
                    self.logger.info("User said: {text}".format(text=reply.transcript))
                
                # Speak the agent's response using NAO's text-to-speech
                if reply.fulfillment_message:
                    text = reply.fulfillment_message
                    self.logger.info("NAO reply: {text}".format(text=text))
                    self.nao.tts.request(NaoqiTextToSpeechRequest(text))
                else:
                    self.logger.info("No fulfillment message")
                
                # Log any parameters
                if reply.parameters:
                    self.logger.info("Parameters: {params}".format(params=reply.parameters))
                """

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
    demo = NaoGeminiDemo()
    demo.run()