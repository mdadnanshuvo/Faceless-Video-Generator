import os
import uuid
import subprocess
import random
import datetime

WORKDIR = "work"
RAW_VID_FOLDER = "raw_videos"

os.makedirs(WORKDIR, exist_ok=True)


def get_audio_duration(audio_file):
    """Return duration of audio file in seconds."""
    result = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_file
    ])
    return float(result.decode().strip())


def get_video_duration(video_file):
    """Return duration of video file in seconds."""
    result = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_file
    ])
    return float(result.decode().strip())


def adjust_subtitle_timing(srt_file, offset_ms=-300):
    """
    Adjust subtitle timing to appear earlier (negative offset) or later (positive offset).
    Default: -300ms (subtitles appear 300ms before audio)
    """
    try:
        with open(srt_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        adjusted_lines = []
        for line in lines:
            # Check if line contains timestamp (format: 00:00:00,000 --> 00:00:05,000)
            if '-->' in line:
                parts = line.strip().split(' --> ')
                if len(parts) == 2:
                    start_time = parts[0]
                    end_time = parts[1]
                    
                    # Adjust both start and end times
                    adjusted_start = adjust_timestamp(start_time, offset_ms)
                    adjusted_end = adjust_timestamp(end_time, offset_ms)
                    
                    adjusted_lines.append(f"{adjusted_start} --> {adjusted_end}\n")
                else:
                    adjusted_lines.append(line)
            else:
                adjusted_lines.append(line)
        
        # Write adjusted subtitles
        adjusted_srt = os.path.join(WORKDIR, f"{uuid.uuid4().hex}_adjusted.srt")
        with open(adjusted_srt, 'w', encoding='utf-8') as f:
            f.writelines(adjusted_lines)
        
        return adjusted_srt
    except Exception as e:
        print(f"Warning: Could not adjust subtitle timing: {e}")
        return srt_file


def adjust_timestamp(timestamp, offset_ms):
    """
    Adjust a single timestamp by offset_ms milliseconds.
    Format: HH:MM:SS,mmm
    """
    try:
        # Parse timestamp
        time_part, ms_part = timestamp.split(',')
        h, m, s = map(int, time_part.split(':'))
        ms = int(ms_part)
        
        # Convert to total milliseconds
        total_ms = (h * 3600000) + (m * 60000) + (s * 1000) + ms
        
        # Apply offset
        total_ms += offset_ms
        
        # Ensure non-negative
        if total_ms < 0:
            total_ms = 0
        
        # Convert back to timestamp format
        hours = total_ms // 3600000
        remaining = total_ms % 3600000
        minutes = remaining // 60000
        remaining = remaining % 60000
        seconds = remaining // 1000
        milliseconds = remaining % 1000
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    except:
        return timestamp


def fix_srt_encoding(srt_file):
    """Fix SRT file encoding to UTF-8 and handle special characters."""
    try:
        # Try reading with different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'windows-1252']
        content = None
        detected_encoding = None

        for encoding in encodings:
            try:
                with open(srt_file, 'r', encoding=encoding, errors='strict') as f:
                    content = f.read()
                detected_encoding = encoding
                print(f"  ✓ Detected encoding: {encoding}")
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if content is None:
            # Last resort: read with errors='replace'
            with open(srt_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            print(f"  ⚠️ Used fallback encoding with character replacement")

        # Remove BOM if present
        if content.startswith('\ufeff'):
            content = content[1:]
        
        # CRITICAL: Fix Windows-1252 problematic characters
        # 0x92 is the right single quotation mark in Windows-1252
        replacements = {
            '\x91': "'",  # Left single quote (0x91)
            '\x92': "'",  # Right single quote (0x92) - THIS IS YOUR ISSUE
            '\x93': '"',  # Left double quote (0x93)
            '\x94': '"',  # Right double quote (0x94)
            '\x95': '•',  # Bullet (0x95)
            '\x96': '–',  # En dash (0x96)
            '\x97': '—',  # Em dash (0x97)
            '\x85': '...',  # Ellipsis (0x85)
        }
        
        for old_char, new_char in replacements.items():
            if old_char in content:
                content = content.replace(old_char, new_char)
                print(f"  ✓ Replaced problematic character: {repr(old_char)} → {new_char}")
        
        # Also normalize Unicode smart quotes
        content = content.replace(''', "'").replace(''', "'")
        content = content.replace('"', '"').replace('"', '"')
        content = content.replace('–', '-').replace('—', '-')
        content = content.replace('…', '...')

        # Write back as clean UTF-8
        fixed_srt = os.path.join(WORKDIR, f"{uuid.uuid4().hex}_fixed.srt")
        with open(fixed_srt, 'w', encoding='utf-8', newline='') as f:
            f.write(content)

        return fixed_srt
    except Exception as e:
        print(f"Warning: Could not fix SRT encoding: {e}")
        return srt_file


def process_video(audio, srt, topic=None, avg_video_len=10, subtitle_offset_ms=-300):
    """
    Merge multiple raw videos to cover the voiceover duration.
    Resize/crop to 1080x1920, overlay subtitles, and merge audio.
    
    Args:
        subtitle_offset_ms: Milliseconds to offset subtitles (negative = appear earlier)
                           Default: -300 (subtitles appear 300ms before audio)
    """
    # 1️⃣ List all raw videos
    video_files = [f for f in os.listdir(RAW_VID_FOLDER) 
                   if os.path.isfile(os.path.join(RAW_VID_FOLDER, f)) 
                   and f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm'))]
    if not video_files:
        raise FileNotFoundError("No videos found in 'raw_videos/' folder.")

    # 2️⃣ Get voiceover duration - this is our target
    voice_duration = get_audio_duration(audio)
    print(f"\n🎤 Voiceover duration: {voice_duration:.2f}s")

    # 3️⃣ Select videos until we have ENOUGH duration to cover voiceover
    random.shuffle(video_files)
    selected_videos = []
    accumulated_duration = 0.0

    print(f"\n📹 Selecting videos:")
    for video_file in video_files:
        video_path = os.path.join(RAW_VID_FOLDER, video_file)
        try:
            duration = get_video_duration(video_path)
            print(f"  - {video_file}: {duration:.2f}s")
        except Exception as e:
            duration = avg_video_len
            print(f"  - {video_file}: {duration:.2f}s (estimated, error: {e})")
        
        selected_videos.append(video_file)
        accumulated_duration += duration
        
        # Stop when we have enough footage
        if accumulated_duration >= voice_duration:
            print(f"\n✅ Selected {len(selected_videos)} videos")
            print(f"   Total video duration: {accumulated_duration:.2f}s")
            print(f"   Will be trimmed to: {voice_duration:.2f}s")
            break

    # If we still don't have enough, use all videos and repeat
    if accumulated_duration < voice_duration:
        print(f"\n⚠️ Warning: Not enough video footage!")
        print(f"   Available: {accumulated_duration:.2f}s")
        print(f"   Required: {voice_duration:.2f}s")
        print(f"   Repeating videos to cover gap...")
        original_videos = selected_videos.copy()
        while accumulated_duration < voice_duration:
            for video_file in original_videos:
                if accumulated_duration >= voice_duration:
                    break
                video_path = os.path.join(RAW_VID_FOLDER, video_file)
                try:
                    duration = get_video_duration(video_path)
                except:
                    duration = avg_video_len
                selected_videos.append(video_file)
                accumulated_duration += duration
                print(f"  + Added {video_file} again ({duration:.2f}s)")

    # 4️⃣ Build proper filter_complex with concat filter
    print(f"\n🔄 Processing videos: concat → scale → crop → trim to {voice_duration:.2f}s...")
    
    # Build input list and filter string
    input_args = []
    filter_parts = []
    
    for i, video_file in enumerate(selected_videos):
        video_path = os.path.abspath(os.path.join(RAW_VID_FOLDER, video_file)).replace("\\", "/")
        input_args.extend(["-i", video_path])
        # Scale and prepare each video before concatenating
        filter_parts.append(f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1[v{i}]")
    
    # Concatenate all processed videos
    concat_inputs = "".join([f"[v{i}]" for i in range(len(selected_videos))])
    filter_complex = ";".join(filter_parts) + f";{concat_inputs}concat=n={len(selected_videos)}:v=1:a=0[outv]"
    
    merged_raw = os.path.join(WORKDIR, f"{uuid.uuid4().hex}_merged.mp4")
    
    cmd = [
        "ffmpeg", "-y"
    ] + input_args + [
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-t", str(voice_duration),  # Trim to exact duration
        "-an",
        merged_raw
    ]
    
    subprocess.run(cmd, check=True)

    # Verify the merged video duration
    try:
        merged_duration = get_video_duration(merged_raw)
        print(f"   ✓ Merged video duration: {merged_duration:.2f}s")
        if abs(merged_duration - voice_duration) > 0.5:
            print(f"   ⚠️ Warning: Duration mismatch! Expected {voice_duration:.2f}s, got {merged_duration:.2f}s")
    except:
        pass

    # 5️⃣ Fix SRT encoding FIRST (removes problematic characters)
    print(f"\n🔄 Fixing subtitle encoding and characters...")
    fixed_srt = fix_srt_encoding(srt)
    
    # 6️⃣ Adjust subtitle timing (appear earlier)
    print(f"🔄 Adjusting subtitle timing ({subtitle_offset_ms}ms offset)...")
    adjusted_srt = adjust_subtitle_timing(fixed_srt, subtitle_offset_ms)

    # 7️⃣ Prepare output path
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{topic.replace(' ', '_')}_{timestamp}" if topic else f"final_{uuid.uuid4().hex}"
    out = os.path.join(WORKDIR, f"{name}.mp4")

    # 8️⃣ Get proper paths
    merged_raw_path = os.path.abspath(merged_raw).replace("\\", "/")
    audio_path = os.path.abspath(audio).replace("\\", "/")
    srt_abs = os.path.abspath(adjusted_srt).replace("\\", "/")
    srt_escaped = srt_abs.replace(":", "\\:")

    # 9️⃣ Add subtitles with Arial (most compatible font)
    # Removed Bold=1 to avoid font weight issues
    subtitle_filter = (
        f"subtitles='{srt_escaped}':force_style="
        "'FontName=Arial,Fontsize=16,Outline=2,Shadow=1.5,"
        "MarginV=100,Alignment=2,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,"
        "BorderStyle=1'"
    )

    print(f"🔄 Adding subtitles and audio...")
    cmd = [
        "ffmpeg", "-y",
        "-i", merged_raw_path,
        "-i", audio_path,
        "-vf", subtitle_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        out
    ]

    subprocess.run(cmd, check=True)

    # Verify final video duration
    try:
        final_duration = get_audio_duration(out)
        print(f"\n✅ Final video created: {out}")
        print(f"   Duration: {final_duration:.2f}s")
        print(f"   Subtitle offset: {subtitle_offset_ms}ms (appear {abs(subtitle_offset_ms)}ms before audio)")
        if abs(final_duration - voice_duration) > 0.5:
            print(f"   ⚠️ Warning: Final duration differs from voiceover by {abs(final_duration - voice_duration):.2f}s")
    except:
        print(f"\n✅ Video created: {out}")

    # 🔟 Cleanup
    os.remove(merged_raw)
    if fixed_srt != srt:
        os.remove(fixed_srt)
    if adjusted_srt != srt and adjusted_srt != fixed_srt:
        os.remove(adjusted_srt)

    return out