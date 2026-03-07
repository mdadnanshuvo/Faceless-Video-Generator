from google import genai
import os
from dotenv import load_dotenv


load_dotenv()
def generate_script(api_key: str, topic: str):
    client = genai.Client(api_key=api_key)

    prompt = f"""
You are an expert scriptwriter for short, faceless educational videos.

Write a powerful, easy-to-understand tutorial script about: {topic}

Requirements: 
1. Start with a **strong headline using the topic** that instantly grabs attention.
2. In the next line, create a **3-second hook** that makes viewers curious.
3. Script length: **90–140 words**.
4. Use **very simple language** so even beginners can understand.
5. Explain the idea **step-by-step like a mentor teaching a student**.
6. Include **1 short relatable example or mini story**.
7. Add **2–3 practical tips viewers can apply immediately**.
8. Use **short punchy lines** (max 10–12 words per line).
9. Make it **fast-paced and cognitive**, suitable for subtitles.
10. Avoid greetings, filler words, and explanations about delivery.
11. Tone: **energetic, confident, motivational mentor voice**.
12. End with a **clear call-to-action** like:
   "Follow for more powerful learning tips."

Formatting rules:
- Each sentence on a **new line**
- Lines must be **short and subtitle-friendly**
- No emojis
- No stage directions
"""


    res = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return res.text.strip()


if __name__ == "__main__":
    topic = input("Enter topic: ")
    api_key = os.getenv("GEMINI_API_KEY")
    script = generate_script(api_key,topic)
    print("\n🎬 Generated Script:\n")
    print(script)
