# Import basic preliminaries
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging

# Import the device(s) we will be using
from sic_framework.devices.desktop import Desktop
# Import the device(s) we will be using
from sic_framework.devices import Nao
from sic_framework.devices.nao import NaoqiTextToSpeechRequest

# Import the service(s) we will be using
"""from sic_framework.services.dialogflow_cx.dialogflow_cx import (
    DialogflowCX,
    DialogflowCXConf,
    DetectIntentRequest,
    QueryResult,
    RecognitionResult,
)
"""
import google.generativeai as genai

# Import libraries necessary for the demo
import json
from os.path import abspath, join
import numpy as np

import speech_recognition as sr
import pyttsx3

class GeminiDemo(SICApplication):
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
        super(GeminiDemo, self).__init__()
        
        # Demo-specific initialization
        self.desktop = None
        self.desktop_mic = None
        self.gemini_agent = None
        self.gemini_keyfile_path = abspath(join("..", "config", "api_key_marit.json"))


        self.set_log_level(sic_logging.INFO)

        # Random session ID is necessary for Dialogflow CX
        self.session_id = np.random.randint(10000)
        
        # Log files will only be written if set_log_file is called. Must be a valid full path to a directory.
        # self.set_log_file("/Users/apple/Desktop/SAIL/SIC_Development/sic_applications/demos/desktop/logs")
        self.recognizer = None
        self.tts_engine = None
        self.setup()
    
    def on_recognition(self, message):
        """
        Dialogflow CX recognition callback: when a final transcript is available,
        send it to Gemini, log and return the reply (optionally trigger TTS).
        """
        if not message:
            return None

        # Use the correct attribute provided by your Dialogflow wrapper:
        rr = getattr(message, "recognition_result", None)
        if not rr or not getattr(rr, "is_final", False):
            return None

        transcript = getattr(rr, "transcript", None)
        if not transcript:
            return None

        self.logger.info("Transcript: {}".format(transcript))

        # Send transcript to Gemini and return reply
        try:
            # Create model wrapper (assumes genai.configure was already called)
            model = genai.GenerativeModel(self.gemini_model)
            response = model.generate_content(transcript)
            reply = getattr(response, "text", str(response))
            self.logger.info("Gemini reply: {}".format(reply))

            # Optional if we want to speak the reply with NAO:
            # try:
            #     self.nao.tts.request(NaoqiTextToSpeechRequest(reply))
            # except Exception as e:
            #     self.logger.warning("TTS failed: {}".format(e))

            return reply
        except Exception as e:
            self.logger.error("Gemini call failed: {}".format(e))
            return None
        #----------END NEW------------

    def setup(self):
        """Initialize and configure the desktop microphone and Conversational Agents service."""
        self.logger.info("Initializing Desktop microphone")
        
        # Local desktop setup
        self.desktop = Desktop()
        self.desktop_mic = self.desktop.mic
        
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

        self.logger.info("Initializing Conversational Agents (Gemini)...")
        
        # Load the key json file
        with open(self.gemini_keyfile_path) as f:
            keyfile_json = json.load(f)

        self.gemini_model = "gemini-2.5-flash"
        
        # TODO: Replace with your actual agent ID and location
        # You can find your agent ID in the Dialogflow CX console:
        # 1. Go to https://dialogflow.cloud.google.com/cx/
        # 2. Select your project
        # 3. Click on your agent
        # 4. The agent ID is in the URL: ...agents/YOUR-AGENT-ID/...
        # or in Agent Settings under "Agent ID"
        
        #agent_id = "XXX"  # Replace with your agent ID
        #location = "XXX"  # Replace with your agent location if different
        
        # Create configuration for Conversational Agents
        """ca_conf = DialogflowCXConf(
            keyfile_json=keyfile_json,
            agent_id=agent_id,
            location=location,
            sample_rate_hertz=44100,
            language="en-US"
        )"""
        
        # Initialize the conversational agent with microphone input
        #self.gemini_agent = DialogflowCX(conf=ca_conf, input_source=self.desktop_mic)
        
        #self.logger.info("Initialized Conversational Agents... registering callback function")
        # Register a callback function to handle recognition results
        #self.gemini_agent.register_callback(callback=self.on_recognition)
    
    def run(self):
        """Main application loop."""
        #self.logger.info(" -- Ready -- ")
        
        try:
            # Demo starts
            #self.nao.tts.request(NaoqiTextToSpeechRequest("What's up bitches"))
            self.logger.info(" -- Ready -- ")

            while not self.shutdown_event.is_set():
                self.logger.info(" ----- Conversation turn")

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
                gemini_reply = self.on_recognition(user_text)
                self.logger.info("Gemini reply: {}".format(gemini_reply))

                # Speak reply on laptop speaker via pyttsx3
                if self.tts_engine:
                    try:
                        self.nao.tts.request(NaoqiTextToSpeechRequest(gemini_reply))
                    except Exception as e:
                        self.logger.warning("Local TTS playback failed: {}".format(e))

                """# Request intent detection with the current session
                reply = self.gemini_agent.request(DetectIntentRequest(self.session_id))
                
                # Log the detected intent
                if reply.intent:
                    self.logger.info("The detected intent: {intent} (confidence: {conf})".format(
                        intent=reply.intent,
                        conf=reply.intent_confidence if reply.intent_confidence else "N/A"
                    ))
                else:
                    self.logger.info("No intent detected")
                
                # Log the transcript
                if reply.transcript:
                    self.logger.info("User said: {text}".format(text=reply.transcript))
                
                # Log the agent's response
                if reply.fulfillment_message:
                    self.logger.info("Agent reply: {text}".format(text=reply.fulfillment_message))
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
    demo = GeminiDemo()
    demo.run()

