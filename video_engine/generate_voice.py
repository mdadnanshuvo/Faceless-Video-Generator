import uuid
import asyncio
import subprocess
import os
import re
import soundfile as sf
import numpy as np
from kokoro_onnx import Kokoro

WORKDIR = "work"
os.makedirs(WORKDIR, exist_ok=True)

VOICE = "am_adam"
SPEED = 0.9

KOKORO_MODEL = "kokoro-v1.0.onnx"
KOKORO_VOICES = "voices-v1.0.bin"

PAUSE_BETWEEN_SENTENCES = 0.35

print("🔄 Loading Kokoro TTS model...")
_kokoro = Kokoro(KOKORO_MODEL, KOKORO_VOICES)
print("✅ Kokoro TTS model loaded")


def clean_text_for_tts(text):
    text = re.sub(r'\*{1,2}(.*?)\*{1,2}', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\-\*\•]\s+', '', text, flags=re.MULTILINE)
    text = text.replace('\u2019', "'").replace('\u2018', "'")
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2013', ',').replace('\u2014', ',')
    text = text.replace('\u2026', '.')
    text = re.sub(r'[^\w\s.,!?\'\"()\-:;]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def clean_chunk_for_tts(chunk):
    chunk = chunk.strip()
    if chunk and chunk[-1] not in '.!?,;:':
        chunk += '.'
    return chunk


def make_silence(duration_sec, sample_rate=24000):
    samples = int(duration_sec * sample_rate)
    return np.zeros(samples, dtype=np.float32)


def chunk_text(text):
    text = clean_text_for_tts(text)
    # ✅ Keep each sentence whole — no mid-sentence splitting
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s.strip()]


def fmt(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:02}:{m:02}:{s:06.3f}".replace(".", ",")


def get_duration(filepath):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        filepath
    ]).decode().strip())


def tts_chunk_sync(text, output_path):
    cleaned = clean_chunk_for_tts(text)
    samples, sample_rate = _kokoro.create(
        cleaned,
        voice=VOICE,
        speed=SPEED,
        lang="en-us"
    )
    silence = make_silence(PAUSE_BETWEEN_SENTENCES, sample_rate)
    samples_with_pause = np.concatenate([samples, silence])
    sf.write(output_path, samples_with_pause, sample_rate)


async def tts_from_script(text):
    chunks = chunk_text(text)
    chunk_files = []
    srt_lines = []
    time = 0.0

    loop = asyncio.get_event_loop()

    for i, chunk in enumerate(chunks, 1):
        tmp = os.path.join(WORKDIR, f"{uuid.uuid4().hex}.wav")
        print(f"  Generating chunk {i}/{len(chunks)}: {chunk[:60]}...")

        await loop.run_in_executor(None, tts_chunk_sync, chunk, tmp)

        dur = get_duration(tmp)
        speech_dur = dur - PAUSE_BETWEEN_SENTENCES
        start, end = time, time + max(speech_dur, 0.1)
        srt_lines.append(f"{i}\n{fmt(start)} --> {fmt(end)}\n{chunk}\n")
        time += dur

        chunk_files.append(tmp)

    list_file = os.path.join(WORKDIR, f"{uuid.uuid4().hex}_list.txt")
    audio_master = os.path.join(WORKDIR, f"{uuid.uuid4().hex}.wav")
    srt_file = os.path.join(WORKDIR, f"{uuid.uuid4().hex}.srt")

    with open(list_file, "w") as f:
        lines = []
        for cf in chunk_files:
            abs_path = os.path.abspath(cf).replace("\\", "/")
            lines.append(f"file '{abs_path}'")
        f.write("\n".join(lines))

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_file, "-c", "copy", audio_master
    ], check=True, capture_output=True)

    with open(srt_file, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    for cf in chunk_files:
        os.remove(cf)
    os.remove(list_file)

    return audio_master, srt_file