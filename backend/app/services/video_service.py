import os
import subprocess
import uuid

from fastapi import HTTPException


def image_to_video(image_path: str, duration: int, output_dir: str) -> str:
    filename = f"video_{uuid.uuid4().hex}.mp4"
    out = os.path.join(output_dir, filename)
    duration = max(1, min(int(duration), 120))
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", image_path,
        "-t", str(duration), "-r", "25",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
        "-c:v", "libx264", "-preset", "fast", "-movflags", "+faststart",
        out,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="video generation timeout")
    if proc.returncode != 0:
        detail = proc.stderr.strip()[-500:] or "ffmpeg error"
        raise HTTPException(status_code=500, detail=f"video generation failed: {detail}")
    return filename
