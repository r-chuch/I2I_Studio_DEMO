# app/services/agents/base_agent.py

from google import genai
import aisuite as ai
from dotenv import dotenv_values
from dotenv import load_dotenv

# config = dotenv_values('.env')
# GEN_API_KEY = config['GEN_API_KEY']
# GEN_API_KEY2 = config['GEN_API_KEY2']
# GROQ_API_KEY = config['GROQ_API_KEY']

load_dotenv()

# def gen_response(topic_text):
 
#     client = genai.Client(api_key=GEN_API_KEY2)

#     try:
#         response = client.models.generate_content(
#             model='gemini-2.0-flash-lite',   # gemini-2.0-flash-lite gemini-2.5-flash gemini-2.0-flash-lite
#             contents=topic_text
#         )
#         print(response.text)
#         use_flag = (use_flag+1)%2
#         return response.text
#     except Exception as e:
#         print("Unexpected error:", e)
#         return None


def gen_response(prompt,system="請用台灣習慣的中文回覆。",
          provider="groq",
          model="openai/gpt-oss-120b"
          ):

    client = ai.Client()

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt}
    ]


    response = client.chat.completions.create(model=f"{provider}:{model}", messages=messages)
    print(response.choices[0].message.content)
    print('===========================================================')
    return response.choices[0].message.content

