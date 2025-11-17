# Import basic preliminaries
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging

# Import the device(s) we will be using
from sic_framework.devices import Nao
from sic_framework.devices.nao import NaoqiTextToSpeechRequest
from sic_framework.devices.common_naoqi.naoqi_motion import NaoqiAnimationRequest, NaoPostureRequest

import google.generativeai as genai
import speech_recognition as sr
import pyttsx3


# Import libraries necessary for the demo
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
        self.gemini_keyfile_path = abspath(join("..", "config", "api_key.txt"))
        self.nao = None
        self.gemini = None
        self.session_id = np.random.randint(10000)

        self.set_log_level(sic_logging.INFO)
        
        # Log files will only be written if set_log_file is called. Must be a valid full path to a directory.
        # self.set_log_file("/Users/apple/Desktop/SAIL/SIC_Development/sic_applications/demos/nao/logs")
        self.recognizer = None
        self.tts_engine = None
        self.setup()

    def ask_gemini(self, message):
        """Take input text, send it to Gemini, return (and speak) the reply."""
        if not message:
            return None

        # Extract text content safely
        text = message if isinstance(message, str) else getattr(message, "text", "") or getattr(message, "transcript", "") or str(message)
        if not text.strip():
            return None

        try:
            # Use the model configured on the object, or fall back
            model_name = getattr(self, "gemini_model", "gemini-2.5-flash")
            model = genai.GenerativeModel(model_name, 
                                          system_instruction="""You are a sarcastic and witty comedian, with a dry sense of humor. 
                                                                You are doing a sketch with another comedian. Keep your answers SHORT and entertaining, 
                                                                and make sure the other comedian can respond. Be funny and use playful humor.""")
            response = model.generate_content(text)

            reply = response.text.strip() if hasattr(response, "text") else str(response)
        
        except Exception as e:
            self.logger.error(f"[Gemini Error] {e}")
            reply = None
        
        return reply

    def speak(self, text):
        """Route speech output to NAO if connected, otherwise laptop TTS or print."""
        if not text:
            return
        
        if self.nao:
            try:
                self.logger.info("NAO speaking: {}".format(text))
                self.nao.tts.request(NaoqiTextToSpeechRequest(text))
                return
            except Exception as e:
                self.logger.warning("NAO TTS failed: {}".format(e))
        
        if self.tts_engine:
            try:
                self.logger.info("Laptop speaking: {}".format(text))
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                return
            except Exception as e:
                self.logger.warning("Local TTS failed: {}".format(e))

        # Fallback: print to console        
        print("TTS:", text)

    def setup(self):
        """Initialize and configure NAO robot and Dialogflow CX."""
        self.logger.info("Initializing NAO robot...")
       
        # Try to initialize NAO; if it fails continue using laptop mic/tts
        try:
            self.nao = Nao(ip=self.nao_ip)
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
        
        #################### Do we need this??
        """# Initialize laptop TTS (pyttsx3) as fallback
        try:
            self.tts_engine = pyttsx3.init()
            self.logger.info("Laptop TTS (pyttsx3) initialized.")
        except Exception as e:
            self.logger.warning("Could not initialize laptop TTS: {}".format(e))
            self.tts_engine = None"""

        self.logger.info("Initializing Gemini...")
        
        with open(self.gemini_keyfile_path) as f:
            api_key = f.read().strip()

        self.logger.info("API key loaded")

        # Configure Gemini with the key
        genai.configure(api_key=api_key)
        self.gemini_model = "gemini-2.5-flash"
        
        self.logger.info("Gemini configured successfully")
    
    def run(self):
        """Main application loop."""
        try:
            # Demo starts — use speak() so it works with or without NAO
            self.speak("What's up")
            self.logger.info(" -- Ready -- ")
            
            while not self.shutdown_event.is_set():
                self.logger.info(" ----- Your turn to talk!")
                user_text = None
                
                if self.recognizer:
                    try:
                        with sr.Microphone() as mic:
                            self.logger.info("Listening...")
                            audio = self.recognizer.listen(mic, timeout=8, phrase_time_limit=10)
                        user_text = self.recognizer.recognize_google(audio)
                        self.logger.info("User: {}".format(user_text))
                    except sr.WaitTimeoutError:
                        self.logger.info("Listening timed out, no speech detected.")
                    except sr.UnknownValueError:
                        self.logger.info("Could not understand audio from laptop mic.")
                    except Exception as e:
                        self.logger.warning("Laptop mic error: {}".format(e))

                if not user_text:
                    try:
                        user_text = input("Type here: ").strip()
                    except EOFError:
                        self.logger.info("Input stream closed, exiting.")
                        break

                if not user_text:
                    self.logger.info("No input received, continuing...")
                    continue

                # Send to Gemini
                #self.logger.info("Sending to Gemini: {}".format(user_text))
                gemini_reply = self.ask_gemini(user_text)

                # Speak the Gemini reply (NAO if connected, otherwise laptop)
                if gemini_reply:
                    self.logger.info("Gemini: {}".format(gemini_reply))
                    self.speak(gemini_reply)
                else:
                    self.logger.warning("Gemini returned no reply")

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