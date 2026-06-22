from app.services.audio_service import AudioService

video_path = "storage/uploads/Snow Runner __ Hill driving Adventure __ Heavy driver __ Edition 2023.mp4"

result = AudioService.build_audio_map(
    video_path=video_path
)

print("Silent:", result["is_silent"])

print(
    "Audio Points:",
    len(result["audio_map"])
)

for key, value in list(
    result["audio_map"].items()
)[:10]:

    print(key, value)