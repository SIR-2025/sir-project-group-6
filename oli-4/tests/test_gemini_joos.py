import streamlit as st
import google.generativeai as genai
import sys
import os

# Add the parent folder (oli-4) to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.api_key_marit import api_key

# Configure the Gemini API
genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.5-flash")

# Create a simple Streamlit app
st.title("LLM-Powered Dialogue with Gemini API")
#st.write("Enter a prompt and let the AI generate some text for you.")

# Input for the prompt
prompt = st.text_area("Enter your prompt here:")

# Button to generate text
if st.button("Generate Text"):
    if prompt:
        # Send the prompt to the Gemini API and get a response
        response = model.generate_content(prompt)
        st.write("Generated Text:")
        #st.write(response['choices'][0]['message']['content'])
        st.write(response.text)
    else:
        st.warning("Please enter a prompt.")