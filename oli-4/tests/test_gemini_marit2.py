import google.generativeai as genai
from naoqi import ALProxy
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.api_key_marit import api_key

# REPLACE WITH ACTUAL IP ADDRESS
nao_ip = "XXX"
nao_port = 9559

# Configure the Gemini API
genai.configure(api_key=api_key)

# Initiate the Gemini model
model = genai.GenerativeModel("gemini-2.5-flash")

try:
    tts = ALProxy("ALTextToSpeech", nao_ip, nao_port)
    tts.setLanguage("English")
    tts.say("Hello world!")
except Exception as e:
    print(f"Could not connect to Nao because {e} :(")
    tts = None

def say(text):
    print("Nao:", text)
    if tts:
        try:
            tts.say(text)
        except Exception as e:
            print(f"Nope, you get this error: {e}")

def generate_response(prompt: str):
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini error: {e}")
        return "WTF you saying?"
    
def main():
    say("Let's do thisssss")

    user_input = input("Your turn to talk: ")
    response = generate_response(user_input)
    say(response)


if __name__ == "__main__":
    main()
