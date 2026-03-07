import os, asyncio
from dotenv import load_dotenv
from video_engine.generate_script import generate_script
from video_engine.generate_voice import tts_from_script
from video_engine.video_processor import process_video

# Load Gemini API key
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found in environment variables!")

async def main():
    topic = input("Enter the video topic: ").strip()
    if not topic:
        print("❌ Topic cannot be empty")
        return

    print("\n📝 Generating script...")
    script = generate_script(GEMINI_KEY, topic)
    print("✅ Script generated:\n")
    print(script)

    print("\n🎤 Generating voice + subtitles...")
    audio, srt = await tts_from_script(script)
    print("✅ Voice + subtitles ready")

    print("\n🎬 Processing video with random background...")
    final_video = process_video(audio, srt, topic)
    print(f"✅ Final video generated: {final_video}\n")

if __name__ == "__main__":
    asyncio.run(main())
