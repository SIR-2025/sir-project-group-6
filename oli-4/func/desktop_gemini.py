# Import basic preliminaries
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging

# Import the device(s) we will be using
from sic_framework.devices.desktop import Desktop
# Import the device(s) we will be using
from sic_framework.devices import Nao
from sic_framework.devices.nao import NaoqiTextToSpeechRequest

import google.generativeai as genai

# Import libraries necessary for the demo
import json
from os.path import abspath, join
import numpy as np

import speech_recognition as sr

class GeminiDemo(SICApplication):
    """
    This is a conversational agent using Google's Gemini via the the Nao microphone or desktop microphone.

    IMPORTANT:
    1. You need to obtain your own keyfile from Google AI Studio and place it in a location that the code can load.
       How to get a key? See https://aistudio.google.com/api-keys
       Save the key in config/api_key.txt

    3. The Conversational Agents service needs to be running:
       - pip install google-generativeai
       - pip install SpeechRecognition
       - You may need to turn of your firewall. 

    Note: This uses the newer Dialogflow CX API (v3), which is different from the older Dialogflow ES (v2).
    """
    
    def __init__(self):
        # Call parent constructor (handles singleton initialization)
        super(GeminiDemo, self).__init__()
        
        # Demo-specific initialization
        self.desktop = None
        self.desktop_mic = None
        self.gemini_agent = None
        self.gemini_keyfile_path = abspath(join("..", "config", "api_key_marit.txt"))


        self.set_log_level(sic_logging.INFO)

        # Random session ID is necessary for Dialogflow CX
        self.session_id = np.random.randint(10000)
        
        # Log files will only be written if set_log_file is called. Must be a valid full path to a directory.
        # self.set_log_file("/Users/apple/Desktop/SAIL/SIC_Development/sic_applications/demos/desktop/logs")
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
            print(f"[Gemini Error] {e}")
            reply = None

        # Make Nao speak (optional)
        if reply and getattr(self, "nao", None):
            try:
                self.nao.tts.say(reply)
            except Exception as e:
                print(f"[Nao Speech Error] {e}")

        return reply


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
        
        with open(self.gemini_keyfile_path) as f:
            api_key = f.read().strip()

        # Configure Gemini with the key
        genai.configure(api_key=api_key)

        self.gemini_model = "gemini-2.5-flash"
        
    
    def run(self):
        """Main application loop."""
        
        try:
            # Demo starts
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
                gemini_reply = self.ask_gemini(user_text)
                self.logger.info("Gemini reply: {}".format(gemini_reply))

                #############3 is dit belangrijk???
                # Speak reply on laptop speaker via pyttsx3
                """if self.tts_engine:
                    try:
                        self.nao.tts.request(NaoqiTextToSpeechRequest(gemini_reply))
                    except Exception as e:
                        self.logger.warning("Local TTS playback failed: {}".format(e))"""

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

