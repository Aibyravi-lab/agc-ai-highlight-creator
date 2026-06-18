from app.services.caption_service import CaptionService

result = CaptionService.add_captions(
    video_path="storage/highlights/final_highlight_reel.mp4",
    caption_text="AGC TEST CAPTION"
)

print(result)