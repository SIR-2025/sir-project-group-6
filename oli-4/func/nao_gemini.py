# Import basic preliminaries
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging

# Import the device(s) we will be using
from sic_framework.devices import Nao
from sic_framework.devices.nao import NaoqiTextToSpeechRequest

import google.generativeai as genai
import speech_recognition as sr

# Import libraries necessary for the demo
from os.path import abspath, join

class NaoGeminiDemo(SICApplication):
    """
    NAO Dialogflow CX demo application.
    
    Demonstrates NAO robot picking up your intent and replying according to your 
    trained Dialogflow CX agent.

    IMPORTANT:
    1. You need to obtain your own keyfile.json from Google Cloud and place it in conf/google/
       How to get a key? See https://social-ai-vu.github.io/social-interaction-cloud/external_apis/google_cloud.html
       Save the key in conf/google/google-key.json

    2. The Conversational Agents service needs to be running:
       - pip install google-generativeai
       - pip install SpeechRecognition
       - You may need to turn of your firewall. 
    """
    
    def __init__(self):
        """
            Initialises NAO robot connection, Gemini configuration, microphone and TTS.
        """
        # Call parent constructor (handles singleton initialization)
        super(NaoGeminiDemo, self).__init__()
        
        # Nao initialization
        self.nao_ip = "10.0.0.242"  # TODO: Replace with your NAO's IP address
        self.gemini_keyfile_path = abspath(join("..", "config", "api_key.txt"))
        self.nao = None
        self.gemini = None

        self.set_log_level(sic_logging.INFO)
        
        # Test-specific initialization
        self.recognizer = None
        self.tts_engine = None
        self.setup()

    def ask_gemini(self, message):
        """
            Takes the input text, sends it to gemini and gives a reply.
        """
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
        
        # Handle exceptions
        except Exception as e:
            self.logger.error(f"[Gemini Error] {e}")
            reply = None
        
        return reply

    def speak(self, text):
        """
            Route speech output to NAO if connected, otherwise laptop TTS.        
        """
        if not text:
            return
        
        # Try to make NAO speak first
        if self.nao:
            try:
                self.logger.info("NAO speaking: {}".format(text))
                self.nao.tts.request(NaoqiTextToSpeechRequest(text))
                return
            except Exception as e:
                self.logger.warning("NAO TTS failed: {}".format(e))
        
    def setup(self):
        """
            Initialise and configure NAO robot and Gemini.
        """

        self.logger.info("Initialising NAO robot...")
       
        # Try to initialise NAO
        try:
            self.nao = Nao(ip=self.nao_ip)
            self.logger.info("NAO device initialised at {}".format(self.nao_ip))
        except Exception as e:
            self.logger.warning("Could not initialise NAO device (continuing without robot): {}".format(e))
            self.nao = None

        # Initialise laptop microphone recogniser if NAO microphone fails
        try:
            self.recognizer = sr.Recognizer()
            with sr.Microphone() as mic:
                self.recognizer.adjust_for_ambient_noise(mic, duration=0.5)
            self.logger.info("Laptop microphone (SpeechRecognition) initialised.")
        except Exception as e:
            self.logger.warning("Could not initialise laptop microphone: {}".format(e))
            self.recognizer = None

        self.logger.info("Initialising Gemini...")
        
        with open(self.gemini_keyfile_path) as f:
            api_key = f.read().strip()

        self.logger.info("API key loaded")

        # Configure Gemini with the key
        genai.configure(api_key=api_key)
        
        self.logger.info("Gemini configured successfully")
    
    def run(self):
        """
            Run the main application loop.
        """
        try:
            # Speak a startup message
            self.speak("Ready whenever you are!")
            self.logger.info(" -- Ready -- ")
            
            while not self.shutdown_event.is_set():
                self.logger.info(" ----- Your turn to talk!")
                user_text = None
                
                # Listen for user input
                if self.recognizer:
                    try:
                        with sr.Microphone() as mic:
                            self.logger.info("Listening...")
                            audio = self.recognizer.listen(mic, timeout=8, phrase_time_limit=10)
                        user_text = self.recognizer.recognize_google(audio)
                        self.logger.info("User: {}".format(user_text))
                    # Raise exceptions for timeout and unrecognised speech
                    except sr.WaitTimeoutError:
                        self.logger.info("Listening timed out, no speech detected.")
                    except sr.UnknownValueError:
                        self.logger.info("Could not understand audio from laptop mic.")
                    except Exception as e:
                        self.logger.warning("Laptop mic error: {}".format(e))

                # If no speech recognised, fallback to text input
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
                gemini_reply = self.ask_gemini(user_text)

                # Speak the Gemini reply
                if gemini_reply:
                    self.logger.info("Gemini: {}".format(gemini_reply))
                    self.speak(gemini_reply)
                else:
                    self.logger.warning("Gemini returned no reply")

        # Stop on keyboard interrupt
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