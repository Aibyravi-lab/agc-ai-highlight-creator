# AGC Private Beta — Tester Guide

**Version:** v0.5.0-beta  
**Beta Type:** Private (10–20 invited testers)  
**Beta Period:** TBD

---

## Beta Scope

This private beta covers the full AGC highlight generation pipeline:

- User registration and login
- Gameplay video upload (MP4, MOV, AVI, MKV, WebM)
- AI-powered highlight detection and clip generation
- Reel and vertical reel export (horizontal and vertical formats)
- Thumbnail generation
- Processing history and project library
- Feedback submission

---

## What We Are Testing

| Area | Goal |
|------|------|
| Upload reliability | Videos of various sizes and formats complete without errors |
| Pipeline accuracy | Detected highlights are relevant and well-timed |
| Export quality | Generated reels play correctly and are suitable for social media |
| Dashboard UX | The interface is clear and easy to navigate |
| Error recovery | Failed jobs display a helpful message and allow retrying |
| Performance | Processing completes in a reasonable time for typical recordings |

---

## Known Limitations

- **Processing time:** AI analysis is CPU-bound. Longer videos (30+ minutes) may take several minutes.
- **Concurrent jobs:** Only one job per user runs at a time. Starting a new upload while a job is running is not yet supported.
- **Vertical reel:** Cropping is automated and may not always frame the action perfectly.
- **Audio detection:** Whisper transcription works best on English speech. Non-English commentary may reduce audio-based highlight scoring.
- **File size:** Maximum upload size depends on server configuration. Very large files (>2 GB) may time out.
- **Clip re-download:** Downloaded clips and reels are tied to the server; files are not yet persisted to cloud storage.
- **Mobile upload:** Uploading directly from a mobile browser is untested and may not work reliably.

---

## Getting Started

1. Open the AGC URL provided to you by the team.
2. Register an account using your email address.
3. Upload a gameplay video using the **Choose Video** button on the dashboard.
4. Click **Generate Highlights** and wait for processing to complete.
5. Review the generated reel in the **Results** section.
6. Download the reel, vertical reel, or thumbnail using the download buttons.
7. Your project is saved automatically in **My Projects**.

---

## How to Report Bugs

Please report bugs using the feedback form linked in your beta invitation email. Include:

1. **What you were doing** — e.g., "I uploaded a 20-minute MOV file."
2. **What happened** — exact error message or unexpected behavior.
3. **What you expected** — what should have happened.
4. **Browser and OS** — e.g., Chrome 125 on Windows 11.
5. **Screenshot** — attach a screenshot if the issue is visual.

**Critical bugs** (login broken, upload fails for all files, crashes): contact the team directly via the beta group chat.

---

## Feedback Process

After each highlight generation, a **feedback card** will appear asking you to rate the result. Please fill this in — even a quick star rating helps calibrate the scoring model.

You can also submit written comments about any aspect of the experience (UI, speed, clip quality, etc.).

Feedback is collected anonymously relative to your video content. Your account information is used only to prevent duplicate submissions.

---

## Supported Browsers

| Browser | Support |
|---------|---------|
| Chrome 115+ | Fully supported |
| Firefox 115+ | Fully supported |
| Edge 115+ | Fully supported |
| Safari 16+ | Supported (some video playback differences possible) |
| Mobile browsers | Not officially supported in this beta |

---

## Privacy

- Uploaded videos are stored on the beta server and are accessible only to your account.
- Videos are not shared with third parties.
- Processing results (clips, reels, thumbnails) are retained for the duration of the beta.
- After the beta ends, all uploaded content will be deleted.

---

## Contact

For questions or urgent issues during the beta, reach out via the channel shared in your invitation.

Thank you for helping test AGC. Your feedback directly shapes the product before public launch.
