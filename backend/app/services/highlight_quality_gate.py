from __future__ import annotations

from pathlib import Path

from app.config.config import settings
from app.services.thumbnail.orchestrator import ThumbnailOrchestrator


class HighlightQualityGate:
    """VED-P1-007: deterministic pre-acceptance evidence check.

    Evaluated on raw per-frame signals BEFORE category/synergy
    amplification is applied, so "high weighted score" can no longer mean
    "automatically valid highlight" — a candidate must clear a semantic
    relevance floor (CLIP) and produce at least one independent piece of
    action evidence (motion, or audio when the video is not silent) before
    it is even eligible for multiplier stacking. scene_score deliberately
    never counts as evidence on its own: a scene cut/camera change is not
    proof of actual gameplay action.
    """

    @staticmethod
    def _visual_sanity(frame_path: str | None) -> float | None:
        """Best-effort technical image-quality score (brightness/contrast/
        sharpness/blur/composition), reused from ThumbnailOrchestrator on
        the already-extracted frame — no FFmpeg clip is generated for this.
        Additive/informational only (folded into quality_score); never
        gates pass/fail and never raises.
        """
        if not frame_path:
            return None
        try:
            if not Path(frame_path).is_file():
                return None
            return ThumbnailOrchestrator.score(frame_path)
        except Exception:
            return None

    @staticmethod
    def _quality_score(
        clip_score: float,
        motion_score: float,
        scene_score: float,
        audio_score: float,
        is_silent: bool,
        visual_quality: float | None,
    ) -> float:
        """Explainability-only composite — never used for pass/fail.

        Blends semantic relevance (clip) with the strongest action signal
        and a smaller scene contribution, so scene informs the reported
        score without being able to single-handedly pass the gate.
        """
        best_action = motion_score if is_silent else max(motion_score, audio_score)
        score = clip_score * 0.45 + best_action * 0.35 + scene_score * 0.20
        if visual_quality is not None:
            score = score * 0.85 + visual_quality * 0.15
        return round(min(max(score, 0.0), 1.0), 4)

    @classmethod
    def evaluate(
        cls,
        clip_score: float,
        motion_score: float,
        scene_score: float,
        audio_score: float,
        is_silent: bool,
        frame_path: str | None = None,
    ) -> dict:
        if not settings.HIGHLIGHT_QUALITY_GATE_ENABLED:
            return {
                "passed": True,
                "reason": "Quality gate disabled",
                "evidence_count": 0,
                "quality_score": round(clip_score, 4),
            }

        visual_quality = cls._visual_sanity(frame_path)
        quality_score = cls._quality_score(
            clip_score, motion_score, scene_score, audio_score,
            is_silent, visual_quality
        )

        # Principle A — CLIP must clear a minimum semantic-relevance floor
        # regardless of any other signal.
        if clip_score < settings.HIGHLIGHT_MIN_CLIP_SCORE:
            return {
                "passed": False,
                "reason": "Quality gate rejected: insufficient semantic relevance",
                "evidence_count": 0,
                "quality_score": quality_score,
            }

        # Principles B/C/D — independent action evidence. scene_score is
        # excluded from this count on purpose; audio is excluded entirely
        # (neither counted for nor against) when the video is silent.
        motion_evidence = motion_score >= settings.HIGHLIGHT_MIN_MOTION_SCORE
        audio_evidence = (
            not is_silent
            and audio_score >= settings.HIGHLIGHT_MIN_AUDIO_SCORE
        )
        evidence_count = int(motion_evidence) + int(audio_evidence)

        if evidence_count < settings.HIGHLIGHT_MIN_EVIDENCE_COUNT:
            return {
                "passed": False,
                "reason": "Quality gate rejected: insufficient independent action evidence",
                "evidence_count": evidence_count,
                "quality_score": quality_score,
            }

        return {
            "passed": True,
            "reason": "Quality gate passed",
            "evidence_count": evidence_count,
            "quality_score": quality_score,
        }
