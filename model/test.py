import os
from openai import OpenAI

print("API_KEY =", os.getenv("OPENAI_API_KEY"))
print("BASE_URL =", os.getenv("OPENAI_API_BASE_URL"))

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE_URL"),
)

resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "ping"}
    ]
)

print("RESPONSE =", resp.choices[0].message.content)
