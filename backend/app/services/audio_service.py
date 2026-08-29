import os
import subprocess
import uuid

from fastapi import HTTPException

from app.config import AUDIO_ALLOWED_FORMATS, AUDIO_MAX_SIZE

OUTPUT_FORMATS = {"mp3", "wav", "ogg", "aac", "flac", "m4a"}
CODEC_MAP = {
    "mp3": "libmp3lame",
    "wav": "pcm_s16le",
    "ogg": "libvorbis",
    "aac": "aac",
    "flac": "flac",
    "m4a": "aac",
}
FFMPEG_TIMEOUT = 300


EXT_ALLOWED = {
    "mp3",
    "wav",
    "ogg",
    "flac",
    "aac",
    "m4a",
    "webm",
    "amr",
    "mp4",
}


def validate_audio(content_type: str, size: int, source_ext: str = "") -> None:
    if size > AUDIO_MAX_SIZE:
        raise HTTPException(status_code=413, detail="file too large")
    if content_type in AUDIO_ALLOWED_FORMATS:
        return
    if source_ext and source_ext.lower() in EXT_ALLOWED:
        return
    raise HTTPException(status_code=400, detail="invalid file format")


def run_ffmpeg(args: list[str]) -> None:
    try:
        proc = subprocess.run(
            ["ffmpeg", "-y", *args],
            capture_output=True,
            text=True,
            timeout=FFMPEG_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="audio processing timeout")
    if proc.returncode != 0:
        detail = proc.stderr.strip()[-500:]
        raise HTTPException(status_code=500, detail=f"ffmpeg failed: {detail}")


def crop_audio(input_path: str, start: float, end: float, output_path: str) -> None:
    if end <= start:
        raise HTTPException(status_code=400, detail="invalid time range")
    run_ffmpeg(["-i", input_path, "-ss", str(start), "-to", str(end), "-c", "copy", output_path])


def concat_audio(input_paths: list[str], output_path: str, output_format: str) -> None:
    if len(input_paths) < 2:
        raise HTTPException(status_code=400, detail="at least two segments required")
    args = []
    for path in input_paths:
        args += ["-i", path]
    args += [
        "-filter_complex",
        f"concat=n={len(input_paths)}:v=0:a=1",
        "-c:a",
        CODEC_MAP[output_format],
        output_path,
    ]
    run_ffmpeg(args)


def adjust_volume(input_path: str, gain: float, output_path: str) -> None:
    if gain <= 0:
        raise HTTPException(status_code=400, detail="gain must be positive")
    run_ffmpeg(["-i", input_path, "-filter:a", f"volume={gain}", "-c:a", "pcm_s16le", output_path])


def denoise_audio(input_path: str, output_path: str) -> None:
    run_ffmpeg(["-i", input_path, "-af", "afftdn=nf=-30", "-c:a", "pcm_s16le", output_path])


def convert_audio(input_path: str, output_format: str, output_path: str) -> None:
    if output_format not in OUTPUT_FORMATS:
        raise HTTPException(status_code=400, detail=f"unsupported output format: {output_format}")
    run_ffmpeg(["-i", input_path, "-codec:a", CODEC_MAP[output_format], output_path])


def process_audio(data: bytes, params: dict, source_ext: str, save_dir: str) -> tuple[str, str]:
    output_format = params.get("output_format", "wav")
    if output_format not in OUTPUT_FORMATS:
        raise HTTPException(status_code=400, detail=f"unsupported output format: {output_format}")

    input_path = os.path.join(save_dir, f"in_{uuid.uuid4().hex}.{source_ext or 'bin'}")
    with open(input_path, "wb") as f:
        f.write(data)

    temp_files = [input_path]
    final_path = None
    try:
        if params.get("concat", {}).get("files"):
            final_path = os.path.join(save_dir, f"out_{uuid.uuid4().hex}.{output_format}")
            concat_audio(params["concat"]["files"], final_path, output_format)
            return final_path, output_format

        current = input_path
        if "crop" in params:
            c = params["crop"]
            tmp = os.path.join(save_dir, f"crop_{uuid.uuid4().hex}.wav")
            crop_audio(current, c["start"], c["end"], tmp)
            temp_files.append(tmp)
            current = tmp
        if "volume" in params:
            tmp = os.path.join(save_dir, f"vol_{uuid.uuid4().hex}.wav")
            adjust_volume(current, params["volume"]["gain"], tmp)
            temp_files.append(tmp)
            current = tmp
        if params.get("denoise"):
            tmp = os.path.join(save_dir, f"den_{uuid.uuid4().hex}.wav")
            denoise_audio(current, tmp)
            temp_files.append(tmp)
            current = tmp
        if output_format != "wav":
            final_path = os.path.join(save_dir, f"out_{uuid.uuid4().hex}.{output_format}")
            convert_audio(current, output_format, final_path)
            return final_path, output_format
        final_path = current
        return final_path, "wav"
    finally:
        for f in temp_files:
            if f != final_path and os.path.exists(f):
                os.remove(f)
