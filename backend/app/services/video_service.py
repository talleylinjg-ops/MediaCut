import os
import subprocess
import uuid

from fastapi import HTTPException

from PIL import Image


def _even(n: int) -> int:
    return n if n % 2 == 0 else n - 1


def image_to_video(image_path: str, duration: int, output_dir: str, motion: str = "zoom") -> str:
    filename = f"video_{uuid.uuid4().hex}.mp4"
    out = os.path.join(output_dir, filename)
    duration = max(1, min(int(duration), 120))
    total_frames = duration * 25

    if motion == "none":
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_path,
            "-t", str(duration), "-r", "25",
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
            "-c:v", "libx264", "-preset", "fast", "-movflags", "+faststart",
            out,
        ]
        return _run(cmd)

    try:
        with Image.open(image_path) as im:
            w, h = im.size
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid image for video: {e}")

    maxside = max(w, h)
    target = min(1024, max(480, maxside))
    ratio = target / maxside
    ow = _even(round(w * ratio)) or 2
    oh = _even(round(h * ratio)) or 2

    tmp_up = os.path.join(output_dir, f"up_{uuid.uuid4().hex}.jpg")
    with Image.open(image_path) as im:
        im.convert("RGB").resize((ow * 4, oh * 4), Image.LANCZOS).save(tmp_up, "JPEG", quality=92)

    if motion == "pan":
        pan_period = max(2, min(duration, 8))
        pan_frames = 25 * pan_period
        vf = (
            "zoompan=z='1.2':x='(iw-iw/1.2)*(0.5-0.5*cos(2*PI*on/"
            f"{pan_frames}))':y='ih/2-(ih/1.2/2)'"
            f":d={total_frames}:s={ow}x{oh}:fps=25,format=yuv420p"
        )
    else:
        zoom_period = max(2, min(duration, 10))
        zoom_frames = 25 * zoom_period
        vf = (
            "zoompan=z='1+0.15-0.15*cos(2*PI*on/"
            f"{zoom_frames})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={total_frames}:s={ow}x{oh}:fps=25,format=yuv420p"
        )
    cmd = [
        "ffmpeg", "-y", "-i", tmp_up,
        "-vf", vf,
        "-frames:v", str(total_frames),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-movflags", "+faststart",
        out,
    ]
    try:
        return _run(cmd, timeout=max(300, min(duration * 6, 900)))
    finally:
        if os.path.exists(tmp_up):
            os.remove(tmp_up)


def _run(cmd: list, timeout: int = 240) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="video generation timeout")
    if proc.returncode != 0:
        detail = proc.stderr.strip()[-500:] or "ffmpeg error"
        raise HTTPException(status_code=500, detail=f"video generation failed: {detail}")
    return os.path.basename(cmd[-1])
