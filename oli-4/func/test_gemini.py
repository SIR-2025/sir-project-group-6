import google.generativeai as genai

genai.configure(api_key="AIzaSyAQ340KnDzQrlFR-ylxs4dPuKqDRVneHio")

model = genai.GenerativeModel("gemini-2.5-flash")

response = model.generate_content("You are a horse that can talk. You are ordering a beer in a bar, but a monkey is the barman and he does not speak the same language as you.")
print(response.text)
