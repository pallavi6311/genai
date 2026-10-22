"""Text-to-speech helpers.

Tries gTTS (needs internet, supports English, Hindi, Tamil, and Japanese) first, and falls
back to the offline pyttsx3 engine (English only, but works with no network).
"""

from typing import Optional

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


def _speak_with_gtts(text: str, lang_code: str, out_path: str, tld: str = "com") -> Optional[str]:
    if gTTS is None or not text.strip():
        return None
    try:
        tts = gTTS(text=text, lang=lang_code, tld=tld)
        tts.save(out_path)
        return out_path
    except Exception:
        return None


def _speak_with_pyttsx3(text: str, out_path: str, rate: int = 150) -> Optional[str]:
    if pyttsx3 is None or not text.strip():
        return None
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", rate)
        engine.save_to_file(text, out_path)
        engine.runAndWait()
        return out_path
    except Exception:
        return None


def speak_and_return_path(
    text: str,
    lang_code: str = "en",
    prefer_gtts: bool = True,
    out_path: str = "generated_audio.mp3",
    rate: int = 150,
    tld: str = "com",
) -> Optional[str]:
    """Generate speech audio for `text` and return the file path, or None."""
    if not text or not text.strip():
        return None

    if prefer_gtts:
        result = _speak_with_gtts(text, lang_code, out_path, tld)
        if result:
            return result
        # pyttsx3 only writes .wav reliably; adjust extension if falling back
        wav_path = out_path.rsplit(".", 1)[0] + ".wav"
        return _speak_with_pyttsx3(text, wav_path, rate)

    wav_path = out_path.rsplit(".", 1)[0] + ".wav"
    result = _speak_with_pyttsx3(text, wav_path, rate)
    if result:
        return result
    return _speak_with_gtts(text, lang_code, out_path, tld)
