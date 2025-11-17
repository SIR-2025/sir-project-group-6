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

tts = ALProxy("ALTextToSpeech", nao_ip, nao_port)
tts.setLanguage("English")
tts.say("Hello world!")

def say(text):
    print("Nao:", text)
    if tts:
        tts.say(text)

def generate_response(prompt: str):
    
    response = model.generate_content(prompt)
    return response.text.strip()
    
def main():
    say("Let's do thisssss")

    user_input = input("Your turn to talk: ")
    response = generate_response(user_input)
    say(response)


if __name__ == "__main__":
    main()
