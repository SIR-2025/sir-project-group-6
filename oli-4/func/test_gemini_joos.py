import streamlit as st
import google.generativeai as genai
from api_key_joos import api_key

# Configure the Gemini API
genai.configure(api_key=api_key)

# Create a simple Streamlit app
st.title("LLM-Powered Dialogue with Gemini API")
st.write("Enter a prompt and let the AI generate some text for you.")

# Input for the prompt
prompt = st.text_area("Enter your prompt here:")

# Button to generate text
if st.button("Generate Text"):
    if prompt:
        # Send the prompt to the Gemini API and get a response
        response = genai.chat(prompt)
        st.write("Generated Text:")
        st.write(response['choices'][0]['message']['content'])
    else:
        st.write("Please enter a prompt.")