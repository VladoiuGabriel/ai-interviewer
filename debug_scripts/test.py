import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client()
resp = client.models.generate_content(
    model=os.environ["GEMINI_MODEL"],
    contents="Say hi in 5 words.",
)
print(resp.text)