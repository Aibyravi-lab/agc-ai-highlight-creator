from app.services.whisper_service import WhisperService

result = WhisperService.transcribe_video(
    "storage/uploads/0616(1).mp4"
)

print(result["text"][:500])