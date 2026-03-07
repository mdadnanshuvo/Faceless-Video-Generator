# 🎬 Faceless Video Generator

> Automatically generate short-form faceless educational videos — complete with AI-written scripts, realistic voiceover, synced subtitles, and B-roll footage — from a single topic input.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-orange?logo=google)](https://ai.google.dev/)
[![Kokoro](https://img.shields.io/badge/TTS-Kokoro%20ONNX-green)](https://github.com/thewh1teagle/kokoro-onnx)
[![FFmpeg](https://img.shields.io/badge/Video-FFmpeg-red?logo=ffmpeg)](https://ffmpeg.org/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

**GitHub Repository:** [https://github.com/mdadnanshuvo/Faceless-Video-Generator](https://github.com/mdadnanshuvo/Faceless-Video-Generator)

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Project Skeleton](#-project-skeleton)
- [Technology Stack](#-technology-stack)
- [How It Works — Full Pipeline](#-how-it-works--full-pipeline)
- [Audio Generation & Encoding](#-audio-generation--encoding)
- [Video Processing & Encoding](#-video-processing--encoding)
- [Installation & Setup](#-installation--setup)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Output](#-output)
- [Customization Guide](#-customization-guide)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## 🧠 Overview

**Faceless Video Generator** is a fully automated Python pipeline that turns a topic string into a publish-ready short-form video (portrait 1080×1920, ideal for YouTube Shorts, Instagram Reels, TikTok).

Given a topic like `"How to focus better"`, the system:

1. **Writes** a punchy 90–140 word educational script using Google Gemini 2.5 Flash
2. **Narrates** it with a local offline TTS engine (Kokoro ONNX)
3. **Generates** sentence-level synchronized `.srt` subtitles automatically
4. **Assembles** random B-roll footage from your local video pool
5. **Burns** subtitles onto the video and merges the voiceover audio
6. **Exports** a final `.mp4` trimmed to exactly the voiceover length

No manual editing. No cloud TTS API costs. No timeline scrubbing.

---

## 📁 Project Skeleton

```
FACELESS_VIDEO_GENERATOR/
│
├── video_engine/                  # Core pipeline modules
│   ├── __init__.py
│   ├── generate_script.py         # AI script generation (Gemini 2.5 Flash)
│   ├── generate_voice.py          # TTS + subtitle generation (Kokoro ONNX)
│   └── video_processor.py         # Video assembly & encoding (FFmpeg)
│
├── raw_videos/                    # 📂 Drop your B-roll footage here or API key to select random videos from Pixabay or Unsplash
│   └── (your .mp4 / .mov clips)
│
├── work/                          # 🔧 Auto-created temp directory
│   └── (intermediate files — auto-cleaned after each run)
│
├── kokoro-v1.0.onnx               # Kokoro TTS model weights (download separately)
├── voices-v1.0.bin                # Kokoro voice embeddings (download separately)
│
├── main.py                        # 🚀 Entry point — orchestrates the full pipeline
├── requirements.txt               # Python dependencies
├── .env                           # API keys (not committed to git)
├── .gitignore
└── README.md
```

### Key Directory Roles

| Path | Role |
|---|---|
| `video_engine/` | All business logic — one module per pipeline stage |
| `raw_videos/` | Your personal B-roll pool — add any number of clips or add API key for video from Paxabay, Unsplash ... |
| `work/` | Temporary scratch space for intermediate `.wav`, `.srt`, `.mp4` files |
| `kokoro-v1.0.onnx` | Neural TTS model — runs fully offline on CPU/GPU |
| `voices-v1.0.bin` | Pre-trained voice embeddings for the Kokoro engine |
| `.env` | Secrets file — stores `GEMINI_API_KEY` |

---

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Script Writing | Google Gemini 2.5 Flash (`google-genai`) | AI-powered educational script generation |
| Text-to-Speech | Kokoro ONNX (`kokoro-onnx`) | Local, offline neural TTS — zero API cost |
| Audio I/O | `soundfile` + `numpy` | PCM sample manipulation and WAV writing |
| Subtitle Generation | Custom Python logic | Sentence-level `.srt` file with precise timestamps |
| Video Assembly | `ffmpeg` (subprocess) | Decode, filter, concat, encode, burn subtitles |
| Async Orchestration | Python `asyncio` | Non-blocking TTS chunk generation |
| Environment Config | `python-dotenv` | Secure API key loading from `.env` |

---

## 🔄 How It Works — Full Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                              │
│                    (asyncio pipeline)                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              STAGE 1 — Script Generation                    │
│              generate_script.py                             │
│                                                             │
│  Input : topic string  (e.g. "How to focus better")        │
│  Engine: Google Gemini 2.5 Flash API                       │
│  Output: 90–140 word subtitle-friendly script (plain text) │
└──────────────────────────┬──────────────────────────────────┘
                           │  script text
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              STAGE 2 — Voice + Subtitle Generation          │
│              generate_voice.py                              │
│                                                             │
│  Input : script text                                        │
│  Engine: Kokoro ONNX (local, offline)                      │
│  Process:                                                   │
│    1. Split script into sentences                           │
│    2. TTS each sentence → PCM float32 samples              │
│    3. Append 0.35s silence after each sentence             │
│    4. Write each chunk as .wav                              │
│    5. Concat all chunks → audio_master.wav (ffmpeg copy)   │
│    6. Build .srt with per-sentence timestamps               │
│  Output: audio_master.wav  +  subtitles.srt                │
└──────────────────────────┬──────────────────────────────────┘
                           │  .wav + .srt
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              STAGE 3 — Video Processing                     │
│              video_processor.py                             │
│                                                             │
│  Input : audio_master.wav, subtitles.srt                   │
│  Engine: FFmpeg                                             │
│  Process:                                                   │
│    1. Measure voiceover duration                            │
│    2. Randomly pick B-roll clips from raw_videos/           │
│       until total duration ≥ voiceover length              │
│    3. Decode + scale + crop all clips to 1080×1920, 30fps  │
│    4. Concat clips → merged.mp4 trimmed to exact duration  │
│    5. Fix .srt encoding (smart quotes, BOM, special chars)  │
│    6. Offset subtitle timing by -300ms                      │
│    7. Burn subtitles onto video + mix in voiceover audio    │
│  Output: {topic}_{timestamp}.mp4 (1080×1920 H.264+AAC)    │
└─────────────────────────────────────────────────────────────┘
```

### Pipeline Data Flow

```
topic (string)
  └─► [Gemini 2.5 Flash]
        └─► script (string)
              └─► [Kokoro ONNX] ──────────────────► audio_master.wav
              └─► [Timestamp logic] ──────────────► subtitles.srt
                                                          │
raw_videos/*.mp4 ──► [FFmpeg decode+filter+concat] ──────┘
                                                     ▼
                                           [FFmpeg subtitle burn
                                            + audio mux + encode]
                                                     ▼
                                         {topic}_{timestamp}.mp4 ✅
```

---

## 🔊 Audio Generation & Encoding

### Step 1 — Neural TTS Inference (Text → Raw PCM)

The Kokoro ONNX model runs locally. It takes a cleaned sentence and returns raw audio samples:

```python
samples, sample_rate = _kokoro.create(
    cleaned_text,
    voice="am_adam",   # Male English voice
    speed=0.9,         # Slightly slower for clarity
    lang="en-us"
)
# samples → numpy float32 array (raw PCM waveform)
# sample_rate → 24000 Hz
```

- **No internet required** — inference runs entirely on your CPU/GPU via ONNX Runtime
- Output is an in-memory **PCM float32 waveform** at **24,000 Hz**

### Step 2 — Silence Padding (NumPy)

After each sentence, 0.35 seconds of silence is appended to create natural breathing room:

```python
silence = np.zeros(int(0.35 * 24000), dtype=np.float32)
samples_with_pause = np.concatenate([samples, silence])
```

### Step 3 — Write WAV Chunks (Lossless)

Each sentence chunk is written as an uncompressed WAV file:

```python
sf.write(output_path, samples_with_pause, sample_rate)
# Format: PCM 32-bit float, 24 kHz, mono — fully lossless
```

### Step 4 — Concatenate Chunks → Master WAV (FFmpeg stream copy)

```bash
ffmpeg -f concat -safe 0 -i list.txt -c copy audio_master.wav
```

- `-c copy` = **zero re-encoding** — raw byte streams are joined directly
- No quality loss, near-instant execution

### Step 5 — Final AAC Encoding (inside the video)

```bash
ffmpeg -c:a aac -b:a 192k ...
```

- The WAV master is encoded to **AAC at 192 kbps** — the standard compressed audio format for MP4 containers
- This is the **only lossy step** in the entire audio chain

### Audio Encoding Summary

```
Text
  → Kokoro ONNX        → float32 PCM (in memory, 24kHz)
  → soundfile.write()  → .wav chunk (PCM, lossless)
  → ffmpeg -c copy     → audio_master.wav (PCM, lossless, concatenated)
  → ffmpeg aac 192k    → final AAC stream inside .mp4 (lossy, ~192kbps)
```

---

## 🎬 Video Processing & Encoding

### Step 1 — Duration Measurement

Before selecting any footage, the voiceover duration is measured:

```bash
ffprobe -show_entries format=duration audio_master.wav
# → e.g. 47.23 seconds
```

This becomes the **target duration** for all subsequent video operations.

### Step 2 — Random B-Roll Selection

Clips from `raw_videos/` are shuffled and selected greedily until accumulated duration ≥ voiceover length:

```python
random.shuffle(video_files)
for video_file in video_files:
    accumulated_duration += get_video_duration(video_file)
    selected_videos.append(video_file)
    if accumulated_duration >= voice_duration:
        break
```

If total footage is still insufficient, clips are repeated in a loop.

### Step 3 — Decode → Filter → Re-encode (Pass 1)

Each source clip is decoded from its native codec (H.264, H.265, VP9, etc.) into raw YUV frames, processed through a filter chain, and re-encoded:

```
ffmpeg filter_complex pipeline per clip:

[raw frames]
  → scale=1080:1920:force_original_aspect_ratio=increase
      (upscale so smallest dimension fills 1080×1920)
  → crop=1080:1920
      (center-crop — removes letterbox/pillarbox bars)
  → fps=30
      (normalize all clips to 30fps — drops or duplicates frames)
  → setsar=1
      (enforce square pixel aspect ratio)
  → concat (all clips joined into one continuous stream)
  → libx264 CRF 23, preset medium
      (H.264 re-encode, visually transparent quality)
  → -t {voice_duration}
      (hard trim to exact voiceover length)
```

**Codec settings explained:**

| Setting | Value | Meaning |
|---|---|---|
| `-c:v` | `libx264` | H.264 codec — maximum compatibility |
| `-preset` | `medium` | Balanced speed vs compression ratio |
| `-crf` | `23` | Constant Rate Factor — lower = better quality. 23 is default "visually lossless" |
| `-t` | `{voice_duration}` | Output trimmed to exact audio length |
| `-an` | — | No audio in this intermediate file |

### Step 4 — Subtitle Preprocessing

Before burning, the `.srt` file undergoes two fixes:

**a) Encoding repair** — handles Windows-1252 smart quotes, BOM markers, and special characters that would crash `libass`:

```python
replacements = {
    '\x92': "'",   # Windows right single quote → plain apostrophe
    '\x93': '"',   # Windows left double quote
    '\x94': '"',   # Windows right double quote
    '\u2019': "'", # Unicode right single quote
    '\u2013': '-', # En dash
    ...
}
```

**b) Timing offset (-300ms)** — shifts all subtitle timestamps 300ms earlier so text appears *before* the word is spoken, matching human visual perception:

```
Original:  00:00:02,500 --> 00:00:04,200
Adjusted:  00:00:02,200 --> 00:00:03,900
```

### Step 5 — Subtitle Burn-in + Audio Mux (Pass 2, Final)

The final FFmpeg command decodes `merged.mp4`, burns subtitles using `libass`, mixes in the voiceover, and re-encodes everything:

```bash
ffmpeg \
  -i merged.mp4 \
  -i audio_master.wav \
  -vf "subtitles='subtitles.srt':force_style='
        FontName=Arial,
        Fontsize=16,
        Outline=2,
        Shadow=1.5,
        MarginV=100,
        Alignment=2,
        PrimaryColour=&H00FFFFFF,
        OutlineColour=&H00000000'" \
  -c:v libx264 -preset medium -crf 23 \
  -c:a aac -b:a 192k \
  -shortest \
  final_output.mp4
```

**Subtitle style settings:**

| Style Property | Value | Effect |
|---|---|---|
| `FontName=Arial` | Arial | Maximum cross-platform compatibility |
| `Fontsize=16` | 16pt | Readable on mobile screens |
| `Outline=2` | 2px | Black outline for contrast on any background |
| `Shadow=1.5` | 1.5px | Drop shadow for depth |
| `Alignment=2` | Bottom-center | Standard subtitle position |
| `MarginV=100` | 100px | Lifts subtitles above the bottom edge |
| `PrimaryColour` | White | High-visibility text color |

### Video Encoding Summary

```
B-roll .mp4 files (any codec)
  → ffmpeg decode          → raw YUV frames (in memory)
  → scale + crop + fps     → 1080×1920 @ 30fps YUV frames
  → libx264 CRF23          → merged.mp4 (H.264, Pass 1)
  → ffmpeg decode again    → raw YUV frames
  → libass subtitle filter → frames with burned-in text pixels
  → libx264 CRF23          → final .mp4 video stream (H.264, Pass 2)
  + aac 192k               → final .mp4 audio stream (AAC, lossy)
  = {topic}_{timestamp}.mp4 ✅
```

---

## ⚙️ Installation & Setup

### Prerequisites

- Python 3.10 or higher
- `ffmpeg` installed and available in system PATH
- A Google Gemini API key (free tier available)

### 1. Clone the Repository

```bash
git clone https://github.com/mdadnanshuvo/Faceless-Video-Generator.git
cd Faceless-Video-Generator
```

### 2. Create a Virtual Environment

```bash
python -m venv env

# Windows
env\Scripts\activate

# macOS / Linux
source env/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install FFmpeg

**Windows:**
```bash
winget install ffmpeg
# or download from https://ffmpeg.org/download.html and add to PATH
```

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg
```

### 5. Download Kokoro TTS Model Files

Download and place these two files in the **project root** (same level as `main.py`):

| File | Download |
|---|---|
| `kokoro-v1.0.onnx` | [Hugging Face — kokoro-onnx releases](https://github.com/thewh1teagle/kokoro-onnx/releases) |
| `voices-v1.0.bin` | [Hugging Face — kokoro-onnx releases](https://github.com/thewh1teagle/kokoro-onnx/releases) |

Your project root should look like:
```
FACELESS_VIDEO_GENERATOR/
├── kokoro-v1.0.onnx   ← here
├── voices-v1.0.bin    ← here
├── main.py
└── ...
```

### 6. Add Your B-Roll Footage

Place any `.mp4`, `.mov`, `.avi`, `.mkv`, or `.webm` clips into the `raw_videos/` folder:

```bash
mkdir raw_videos
# copy your video clips into raw_videos/
```

> **Tip:** More clips = more variety per run. Aim for 5–20 clips of 5–30 seconds each.

---

## 🔐 Configuration

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your free Gemini API key from [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).

> ⚠️ **Never commit `.env` to git.** It is already included in `.gitignore`.

### Optional Customization (in `generate_voice.py`)

```python
VOICE = "am_adam"             # Change voice (see Kokoro docs for options)
SPEED = 0.9                   # 1.0 = normal speed, 0.8 = slower, 1.2 = faster
PAUSE_BETWEEN_SENTENCES = 0.35  # Seconds of silence between sentences
```

### Optional Customization (in `video_processor.py`)

```python
subtitle_offset_ms = -300   # Negative = subtitles appear before audio (recommended)
```

---

## 🚀 Usage

```bash
python main.py
```

You will be prompted:

```
Enter the video topic:
```

Type any educational topic, for example:

```
How to build a morning routine
```

The terminal will show real-time progress through all three stages:

```
📝 Generating script...
✅ Script generated:

  [script text displayed here]

🎤 Generating voice + subtitles...
  Generating chunk 1/14: How to build a morning routine...
  Generating chunk 2/14: Most people start their day wrong...
  ...
✅ Voice + subtitles ready

🎬 Processing video with random background...
  🎤 Voiceover duration: 52.34s
  📹 Selecting videos:
    - clip_001.mp4: 15.00s
    - clip_002.mp4: 22.00s
    - clip_003.mp4: 18.00s
  ✅ Selected 3 videos
  ...
✅ Final video generated: work/How_to_build_a_morning_routine_20260307_142300.mp4
```

---

## 📤 Output

The final video is saved to the `work/` directory:

```
work/
└── {topic_with_underscores}_{YYYYMMDD_HHMMSS}.mp4
```

**Output specs:**

| Property | Value |
|---|---|
| Resolution | 1080 × 1920 (portrait, 9:16) |
| Frame Rate | 30 fps |
| Video Codec | H.264 (libx264), CRF 23 |
| Audio Codec | AAC, 192 kbps |
| Subtitles | Burned-in (libass), bottom-center, white with outline |
| Duration | Exactly matches voiceover length |

Ready to upload directly to YouTube Shorts, Instagram Reels, or TikTok.

---

## 🎛️ Customization Guide

### Change the AI Voice

Edit `video_engine/generate_voice.py`:

```python
VOICE = "am_adam"     # Male US English (default)
# Other options: "af_bella", "am_michael", "bf_emma", "bm_george"
# See full list: https://github.com/thewh1teagle/kokoro-onnx
```

### Change the Script Style

Edit the prompt in `video_engine/generate_script.py` to adjust:
- Word count (currently 90–140)
- Tone (currently motivational/educational)
- Structure (e.g. add bullet points, change CTA)
- Target audience

### Adjust Video Quality

In `video_engine/video_processor.py`, find the two FFmpeg encode commands and adjust:

```python
# Lower CRF = better quality, larger file
"-crf", "18"   # high quality
"-crf", "23"   # default (visually lossless)
"-crf", "28"   # smaller file, some quality loss

# Faster preset = faster encoding, larger file
"-preset", "fast"    # faster
"-preset", "medium"  # balanced (default)
"-preset", "slow"    # smaller file, slower
```

### Change Subtitle Style

In `video_processor.py`, edit the `force_style` string:

```python
subtitle_filter = (
    f"subtitles='{srt_escaped}':force_style="
    "'FontName=Arial,"      # ← change font
    "Fontsize=18,"          # ← change size
    "PrimaryColour=&H0000FFFF,"  # ← yellow text (BBGGRR format)
    "MarginV=150,...'"      # ← lift subtitles higher
)
```

---

## 🐛 Troubleshooting

### `GEMINI_API_KEY not found`
- Make sure `.env` exists in the project root with `GEMINI_API_KEY=your_key`
- Ensure the virtual environment is activated before running

### `No videos found in 'raw_videos/' folder`
- Create the `raw_videos/` directory if it doesn't exist
- Add at least one `.mp4` or `.mov` clip to it

### `FileNotFoundError: kokoro-v1.0.onnx`
- Download the model files from the Kokoro ONNX releases page
- Place them in the **project root** (not inside `video_engine/`)

### `ffmpeg: command not found`
- Install FFmpeg and ensure it's on your system PATH
- Verify with: `ffmpeg -version`

### Subtitle encoding errors / garbled text
- The `fix_srt_encoding()` function handles most cases automatically
- If issues persist, ensure your script doesn't contain unusual Unicode characters

### Video and audio out of sync
- Adjust `subtitle_offset_ms` in `video_processor.py` (try values between `-100` and `-500`)
- Check that `ffprobe` is working: `ffprobe -version`

---

## 🤝 Contributing

Contributions are welcome!

```bash
# Fork the repo, then:
git clone https://github.com/mdadnanshuvo/Faceless-Video-Generator.git
cd Faceless-Video-Generator
git checkout -b feature/your-feature-name

# Make your changes, then:
git add .
git commit -m "feat: describe your change"
git push origin feature/your-feature-name
# Open a Pull Request on GitHub
```

**Ideas for contributions:**
- Add support for background music mixing
- Add multi-language TTS support
- Build a web UI with FastAPI (the dependency is already in `requirements.txt`!)
- Add automatic upload to YouTube/TikTok via API
- Optimize to single-pass FFmpeg encoding (avoid double H.264 encode)

---

