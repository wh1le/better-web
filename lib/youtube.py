"""YouTube transcript extraction: captions first, whisper fallback."""
import os
import re
import tempfile

from lib.logging import info, warn, done


def is_youtube_url(url: str) -> bool:
    return bool(re.match(r'https?://(www\.)?(youtube\.com|youtu\.be)/', url))


def extract_video_id(url: str) -> str | None:
    m = re.search(r'(?:v=|youtu\.be/)([\w-]{11})', url)
    return m.group(1) if m else None


def get_transcript(url: str) -> str | None:
    """Try captions API first, fall back to yt-dlp + faster-whisper."""
    vid = extract_video_id(url)
    if not vid:
        return None

    info(f"[dim]YouTube[/dim] {vid}")

    text = _try_captions(vid)
    if text:
        done(f"  captions OK ({len(text.split())} words)")
        return text

    warn("  no captions, trying whisper...")
    text = _try_whisper(vid)
    if text:
        done(f"  whisper OK ({len(text.split())} words)")
    else:
        warn("  whisper failed — no transcript")
    return text


def _try_captions(video_id: str) -> str | None:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        entries = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join(e["text"] for e in entries)
    except Exception:
        return None


def _try_whisper(video_id: str) -> str | None:
    try:
        import yt_dlp
        from faster_whisper import WhisperModel
    except ImportError as e:
        warn(f"Whisper fallback unavailable: {e}")
        return None

    url = f"https://www.youtube.com/watch?v={video_id}"
    tmpdir = tempfile.mkdtemp(prefix="bw-yt-")
    audio_path = os.path.join(tmpdir, "audio.mp3")

    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": audio_path,
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # find the actual file (yt-dlp may add extension)
        actual = audio_path
        if not os.path.exists(actual):
            for f in os.listdir(tmpdir):
                if f.startswith("audio"):
                    actual = os.path.join(tmpdir, f)
                    break

        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(actual)
        text = " ".join(s.text.strip() for s in segments)
        return text if text else None
    except Exception as e:
        warn(f"Whisper transcription failed: {e}")
        return None
    finally:
        for f in os.listdir(tmpdir):
            os.remove(os.path.join(tmpdir, f))
        os.rmdir(tmpdir)
