import subprocess

import pytest
from fastapi import HTTPException

from app.services import audio_service


def make_wav(path: str, duration: float = 2.0) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"sine=frequency=440:duration={duration}",
            "-acodec", "pcm_s16le", path,
        ],
        capture_output=True,
        check=True,
    )


def probe_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return float(out)


def test_validate_audio_rejects_large_file():
    with pytest.raises(HTTPException) as exc:
        audio_service.validate_audio("audio/wav", audio_service.AUDIO_MAX_SIZE + 1)
    assert exc.value.status_code == 413


def test_validate_audio_rejects_bad_format():
    with pytest.raises(HTTPException) as exc:
        audio_service.validate_audio("application/pdf", 1024)
    assert exc.value.status_code == 400


def test_crop(tmp_path):
    src = str(tmp_path / "src.wav")
    make_wav(src)
    out = str(tmp_path / "out.wav")
    audio_service.crop_audio(src, 0.2, 1.2, out)
    assert 0.9 < probe_duration(out) < 1.1


def test_crop_invalid_range_raises(tmp_path):
    src = str(tmp_path / "src.wav")
    make_wav(src)
    with pytest.raises(HTTPException) as exc:
        audio_service.crop_audio(src, 1.0, 0.5, str(tmp_path / "x.wav"))
    assert exc.value.status_code == 400


def test_convert_wav_to_mp3(tmp_path):
    src = str(tmp_path / "src.wav")
    make_wav(src)
    out = str(tmp_path / "out.mp3")
    audio_service.convert_audio(src, "mp3", out)
    assert out.endswith(".mp3")


def test_adjust_volume(tmp_path):
    src = str(tmp_path / "src.wav")
    make_wav(src)
    out = str(tmp_path / "out.wav")
    audio_service.adjust_volume(src, 1.5, out)
    assert 1.5 < probe_duration(out) < 2.5


def test_concat(tmp_path):
    a = str(tmp_path / "a.wav")
    b = str(tmp_path / "b.wav")
    make_wav(a, 1.0)
    make_wav(b, 1.0)
    out = str(tmp_path / "out.mp3")
    audio_service.concat_audio([a, b], out, "mp3")
    assert 1.5 < probe_duration(out) < 2.5


def test_process_audio_crop_and_convert(tmp_path):
    src = str(tmp_path / "src.wav")
    make_wav(src)
    with open(src, "rb") as f:
        data = f.read()
    out, fmt = audio_service.process_audio(
        data, {"crop": {"start": 0.2, "end": 1.2}, "output_format": "mp3"}, "wav", str(tmp_path)
    )
    assert fmt == "mp3"
    assert 0.9 < probe_duration(out) < 1.1


def test_process_audio_unknown_format_raises(tmp_path):
    src = str(tmp_path / "src.wav")
    make_wav(src)
    with open(src, "rb") as f:
        data = f.read()
    with pytest.raises(HTTPException) as exc:
        audio_service.process_audio(data, {"output_format": "ape"}, "wav", str(tmp_path))
    assert exc.value.status_code == 400
