import subprocess
import json
from pathlib import Path


def get_video_metadata(file_path: str):
    """
    Extract and clean video metadata using ffprobe
    """

    file = Path(file_path)

    if not file.exists():
        raise FileNotFoundError("Video file does not exist")

    command = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(file)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    data = json.loads(result.stdout)

    # Find video stream
    video_stream = next(
        (
            stream
            for stream in data["streams"]
            if stream.get("codec_type") == "video"
        ),
        {}
    )

    # Calculate FPS
    fps_value = video_stream.get("r_frame_rate", "0/1")
    numerator, denominator = fps_value.split("/")

    fps = (
        round(int(numerator) / int(denominator), 2)
        if int(denominator) != 0
        else 0
    )

    # Convert size bytes to MB
    size_mb = round(
        int(data["format"]["size"]) / (1024 * 1024),
        2
    )

    metadata = {
        "filename": file.name,
        "duration_seconds": round(
            float(data["format"]["duration"]),
            2
        ),
        "resolution": (
            f'{video_stream.get("width")}x'
            f'{video_stream.get("height")}'
        ),
        "fps": fps,
        "codec": video_stream.get("codec_name"),
        "file_size_mb": size_mb
    }

    return metadata