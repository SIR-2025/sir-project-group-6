# Import basic preliminaries
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging

# Import the device(s) we will be using
from sic_framework.devices.desktop import Desktop

import google.generativeai as genai
import speech_recognition as sr

# Import libraries necessary for the demo
from os.path import abspath, join

class GeminiDemo(SICApplication):
    """
    This is a conversational agent using Google's Gemini via the the Nao microphone or desktop microphone.

    IMPORTANT:
    1. You need to obtain your own keyfile from Google AI Studio and place it in a location that the code can load.
       How to get a key? See https://aistudio.google.com/api-keys
       Save the key in config/api_key.txt

    2. The Conversational Agents service needs to be running:
       - pip install google-generativeai
       - pip install SpeechRecognition
       - You may need to turn of your firewall. 
    """
    
    def __init__(self):
        """
            Initialises NAO robot connection, Gemini configuration, microphone and TTS.
        """
        # Call parent constructor (handles singleton initialisation)
        super(GeminiDemo, self).__init__()
        
        # Demo-specific initialisation
        self.desktop = None
        self.desktop_mic = None
        self.gemini_agent = None
        self.gemini_keyfile_path = abspath(join("..", "config", "api_key.txt"))

        self.set_log_level(sic_logging.INFO)
        
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
                                          system_instruction="""You are a comedian in an improv comedy show. You play a specialist that is being interviewed about your specialty.
                                                                You will be given a specialty.
                                                                You are slightly sarcastic and witty, with a dry sense of humor. 
                                                                You talk in easy English, don't use complicated words.
                                                                You will play out the scene with another comedian, who portrays the journalist. 
                                                                Make sure you stay in character as a specialist in your field. Really embrace the specialty you have been given and speak from experience.
                                                                Make your answers funny and engaging.
                                                                Make sure that a nice dialogue can happen between you and the other comedian.
                                                                """)
            response = model.generate_content(text)

            reply = response.text.strip() if hasattr(response, "text") else str(response)
        

        # Handle exceptions
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
        """
            Initialise and configure NAO robot and Gemini.
        """
        self.logger.info("Initialising Desktop microphone")
        
        # Local desktop setup
        self.desktop = Desktop()
        self.desktop_mic = self.desktop.mic
        
        # Initialise laptop microphone recogniser
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

        # Configure Gemini with the key
        genai.configure(api_key=api_key)

        self.logger.info("Gemini configured successfully")

    
    def run(self):
        """
            Run the main application loop.
        """        
        try:
            self.logger.info(" -- Ready -- ")

            while not self.shutdown_event.is_set():
                self.logger.info(" ----- Your turn to talk!")

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
                        user_text = None
                    except sr.UnknownValueError:
                        self.logger.info("Could not understand audio from laptop mic.")
                        user_text = None
                    except Exception as e:
                        self.logger.warning("Laptop mic ASR error: {}".format(e))
                        user_text = None

                # If no speech recognised, fallback to text input
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
                gemini_reply = self.ask_gemini(user_text)

                # Write the Gemini reply
                if gemini_reply:
                    self.logger.info("Gemini: {}".format(gemini_reply))
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
    demo = GeminiDemo()
    demo.run()

