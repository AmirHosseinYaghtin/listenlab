"""Audio metadata helpers."""
from __future__ import annotations

from pathlib import Path


class AudioProbeError(Exception):
    """Raised when audio duration/metadata cannot be read."""


def get_duration(path: Path) -> float | None:
    """Return duration in seconds, or None when it cannot be determined."""
    if not path.exists():
        raise AudioProbeError(f"Audio file not found: {path.name}")
    try:
        from mutagen import File as MutagenFile
    except ImportError as exc:  # pragma: no cover
        raise AudioProbeError("Audio probing requires the 'mutagen' package.") from exc
    try:
        audio = MutagenFile(str(path))
        if audio is None or audio.info is None:
            return None
        length = getattr(audio.info, "length", None)
        if length is None:
            return None
        return float(length)
    except AudioProbeError:
        raise
    except Exception:
        # Unknown/odd container — let the browser still attempt playback.
        return None


def probe_audio(path: Path) -> dict:
    duration = get_duration(path)
    if duration is None:
        raise AudioProbeError(
            f"Could not read audio metadata for '{path.name}'. "
            "Make sure it is a valid MP3, WAV, M4A, OGG or FLAC file."
        )
    return {"duration": round(duration, 3)}
