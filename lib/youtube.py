"""YouTube transcript extraction: captions first, whisper fallback."""
import os
import re
import tempfile

from lib.logging import done, info, warn
from lib.settings import settings


def is_youtube_url(url: str) -> bool:
    return bool(re.match(r'https?://(www\.)?(youtube\.com|youtu\.be)/', url))


def extract_video_id(url: str) -> str | None:
    match = re.search(r'(?:v=|youtu\.be/)([\w-]{11})', url)
    return match.group(1) if match else None


def get_transcript(url: str) -> str | None:
    """Try captions API first, fall back to yt-dlp + faster-whisper."""
    video_id = extract_video_id(url)
    if not video_id:
        return None

    info(f"[dim]YouTube[/dim] {video_id}")

    text = _try_captions(video_id)
    if text:
        done(f"  captions OK ({len(text.split())} words)")
        return text

    warn("  no captions, trying whisper...")
    text = _try_whisper(video_id)
    if text:
        done(f"  whisper OK ({len(text.split())} words)")
    else:
        warn("  whisper failed — no transcript")
    return text


def _try_captions(video_id: str) -> str | None:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        entries = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join(entry["text"] for entry in entries)
    except Exception:
        return None


def _try_whisper(video_id: str) -> str | None:
    try:
        import yt_dlp
        from faster_whisper import WhisperModel
    except ImportError as err:
        warn(f"Whisper fallback unavailable: {err}")
        return None

    youtube_settings = settings.models
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    tmpdir = tempfile.mkdtemp(prefix="bw-yt-")
    audio_path = os.path.join(tmpdir, "audio.mp3")

    try:
        ydl_opts = {
            "format": youtube_settings.whisper_audio_format,
            "outtmpl": audio_path,
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # find the actual file (yt-dlp may add extension)
        actual = audio_path
        if not os.path.exists(actual):
            for filename in os.listdir(tmpdir):
                if filename.startswith("audio"):
                    actual = os.path.join(tmpdir, filename)
                    break

        model = WhisperModel(
            youtube_settings.whisper,
            device=youtube_settings.whisper_device,
            compute_type=youtube_settings.whisper_compute_type,
        )
        segments, _ = model.transcribe(actual)
        text = " ".join(segment.text.strip() for segment in segments)
        return text if text else None
    except Exception as err:
        warn(f"Whisper transcription failed: {err}")
        return None
    finally:
        for filename in os.listdir(tmpdir):
            os.remove(os.path.join(tmpdir, filename))
        os.rmdir(tmpdir)
