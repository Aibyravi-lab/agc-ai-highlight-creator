import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from app.services.game_profiles.profile_registry import ProfileRegistry
from app.services.pipeline_service import PipelineService

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_RESULTS_DIR = _PROJECT_ROOT / "benchmark" / "results"


class EvaluationService:

    DEFAULT_TOLERANCE: int = 5

    @classmethod
    def evaluate(
        cls,
        benchmark_path: str,
        tolerance: int = DEFAULT_TOLERANCE
    ) -> dict:
        benchmark_file = Path(benchmark_path).resolve()

        with open(benchmark_file, "r") as f:
            benchmark = json.load(f)

        video_path = benchmark["video"]
        expected_timestamps: list[int] = benchmark["expected"]

        if not Path(video_path).is_absolute():
            video_path = str(
                benchmark_file.parent / video_path
            )

        game_profile = ProfileRegistry.detect_profile(video_path).game_name

        pipeline_start = time.time()
        result = PipelineService.process_video(video_path)
        processing_time = round(time.time() - pipeline_start, 2)

        all_highlights: list[dict] = result.get(
            "all_highlights", []
        )

        detected_timestamps = [
            int(h["timestamp"]) for h in all_highlights
        ]

        avg_score = 0.0
        avg_confidence = 0.0
        if all_highlights:
            avg_score = round(
                sum(h["score"] for h in all_highlights)
                / len(all_highlights),
                4
            )
            avg_confidence = round(
                sum(
                    h.get("weighted_score", h["score"])
                    for h in all_highlights
                )
                / len(all_highlights),
                4
            )

        true_positives, false_positives, false_negatives = (
            cls._match_timestamps(
                expected=expected_timestamps,
                detected=detected_timestamps,
                tolerance=tolerance
            )
        )

        tp = len(true_positives)
        fp = len(false_positives)
        fn = len(false_negatives)

        precision = (
            round(tp / (tp + fp), 4)
            if (tp + fp) > 0
            else 0.0
        )

        recall = (
            round(tp / (tp + fn), 4)
            if (tp + fn) > 0
            else 0.0
        )

        f1 = (
            round(
                2 * precision * recall / (precision + recall),
                4
            )
            if (precision + recall) > 0
            else 0.0
        )

        stats = result.get("stats", {})
        frames_analyzed: int = stats.get("frames_analyzed", 0)

        # fine_scan_frames and adaptive_threshold are not yet
        # exposed by the pipeline; accepted as None when absent.
        fine_scan_frames: int | None = result.get("fine_scan_frames")
        adaptive_threshold: float | None = result.get("adaptive_threshold")

        fine_scan_pct: float | None = (
            round(fine_scan_frames / frames_analyzed * 100, 2)
            if fine_scan_frames is not None and frames_analyzed > 0
            else None
        )

        report: dict = {
            "benchmark": benchmark_file.name,
            "video": video_path,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "tolerance_seconds": tolerance,
            "expected_timestamps": expected_timestamps,
            "detected_timestamps": detected_timestamps,
            "matches": {
                "true_positives": true_positives,
                "false_positives": false_positives,
                "false_negatives": false_negatives,
            },
            "metrics": {
                "detected_highlights": len(detected_timestamps),
                "expected_highlights": len(expected_timestamps),
                "true_positives_count": tp,
                "false_positives_count": fp,
                "false_negatives_count": fn,
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "average_highlight_score": avg_score,
                "average_confidence": avg_confidence,
                "processing_time_seconds": processing_time,
                "frames_analyzed": frames_analyzed,
                "fine_scan_frames": fine_scan_frames,
                "fine_scan_pct": fine_scan_pct,
                "adaptive_threshold": adaptive_threshold,
                "game_profile": game_profile,
            },
        }

        _RESULTS_DIR.mkdir(parents=True, exist_ok=True)

        report_path = _RESULTS_DIR / "evaluation_report.json"
        summary_path = _RESULTS_DIR / "evaluation_summary.txt"
        comparison_path = _RESULTS_DIR / "benchmark_comparison.md"
        csv_path = _RESULTS_DIR / "evaluation_metrics.csv"

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(cls._build_summary(report))

        with open(comparison_path, "w", encoding="utf-8") as f:
            f.write(cls._build_markdown_report(report))

        cls._append_csv(report, csv_path)

        print(f"Report saved: {report_path}")
        print(f"Summary saved: {summary_path}")
        print(f"Markdown saved: {comparison_path}")
        print(f"CSV updated: {csv_path}")

        return report

    @staticmethod
    def _match_timestamps(
        expected: list[int],
        detected: list[int],
        tolerance: int
    ) -> tuple[list[dict], list[int], list[int]]:
        unmatched = list(detected)
        true_positives: list[dict] = []
        false_negatives: list[int] = []

        for exp in expected:
            best_det = None
            best_diff = float("inf")

            for det in unmatched:
                diff = abs(det - exp)
                if diff <= tolerance and diff < best_diff:
                    best_diff = diff
                    best_det = det

            if best_det is not None:
                true_positives.append({
                    "expected": exp,
                    "detected": best_det,
                    "offset_seconds": best_det - exp,
                })
                unmatched.remove(best_det)
            else:
                false_negatives.append(exp)

        return true_positives, unmatched, false_negatives

    @staticmethod
    def _fmt_optional(val: object) -> str:
        """Format a value that may be None for display."""
        if val is None:
            return "N/A"
        if isinstance(val, float):
            return f"{val:.4f}"
        return str(val)

    @classmethod
    def _build_summary(cls, report: dict) -> str:
        m = report["metrics"]
        matches = report["matches"]

        tp = matches["true_positives"]
        fp = matches["false_positives"]
        fn = matches["false_negatives"]

        fine_scan_pct_str = (
            f"{m['fine_scan_pct']:.2f}%"
            if m.get("fine_scan_pct") is not None
            else "N/A"
        )

        lines = [
            "AGC Highlight Quality Evaluation",
            "=" * 44,
            f"Benchmark      : {report['benchmark']}",
            f"Video          : {report['video']}",
            f"Evaluated at   : {report['evaluated_at']}",
            f"Tolerance      : ±{report['tolerance_seconds']} seconds",
            f"Game Profile   : {m.get('game_profile', 'N/A')}",
            "",
            "Timestamps",
            "-" * 44,
            f"Expected       : {report['expected_timestamps']}",
            f"Detected       : {report['detected_timestamps']}",
            "",
            "Highlight Counts",
            "-" * 44,
            f"Expected Highlights : {m['expected_highlights']}",
            f"Detected Highlights : {m['detected_highlights']}",
            f"True Positives      : {m['true_positives_count']}",
            f"False Positives     : {m['false_positives_count']}",
            f"False Negatives     : {m['false_negatives_count']}",
            "",
            "Metrics",
            "-" * 44,
            f"Precision         : {m['precision']:.4f}",
            f"Recall            : {m['recall']:.4f}",
            f"F1 Score          : {m['f1_score']:.4f}",
            f"Avg Score         : {m['average_highlight_score']:.4f}",
            f"Avg Confidence    : {m['average_confidence']:.4f}",
            f"Processing Time   : {m['processing_time_seconds']}s",
            "",
            "Pipeline Stats",
            "-" * 44,
            f"Frames Analyzed   : {m['frames_analyzed']}",
            f"Fine Scan Frames  : {cls._fmt_optional(m.get('fine_scan_frames'))}",
            f"Fine Scan %       : {fine_scan_pct_str}",
            f"Adaptive Threshold: {cls._fmt_optional(m.get('adaptive_threshold'))}",
        ]

        if tp:
            lines += [
                "",
                "True Positive Detail",
                "-" * 44,
            ]
            for match in tp:
                offset = match["offset_seconds"]
                sign = "+" if offset >= 0 else ""
                lines.append(
                    f"  Expected {match['expected']:>5}s"
                    f" → Detected {match['detected']:>5}s"
                    f"  (offset: {sign}{offset}s)"
                )

        if fn:
            lines += [
                "",
                "Missed Highlights (False Negatives)",
                "-" * 44,
            ]
            for ts in fn:
                lines.append(f"  {ts}s — not detected within tolerance")

        if fp:
            lines += [
                "",
                "Unexpected Detections (False Positives)",
                "-" * 44,
            ]
            for ts in fp:
                lines.append(f"  {ts}s — not in expected list")

        lines.append("")
        return "\n".join(lines)

    @classmethod
    def _build_markdown_report(cls, report: dict) -> str:
        m = report["metrics"]
        matches = report["matches"]

        tp = len(matches["true_positives"])
        fp = len(matches["false_positives"])
        fn = len(matches["false_negatives"])

        fine_scan_pct_str = (
            f"{m['fine_scan_pct']:.2f}%"
            if m.get("fine_scan_pct") is not None
            else "N/A"
        )

        rows: list[tuple[str, str]] = [
            ("Detected Highlights", str(m["detected_highlights"])),
            ("Expected Highlights", str(m["expected_highlights"])),
            ("True Positives", str(tp)),
            ("False Positives", str(fp)),
            ("False Negatives", str(fn)),
            ("Precision", f"{m['precision']:.4f}"),
            ("Recall", f"{m['recall']:.4f}"),
            ("F1 Score", f"{m['f1_score']:.4f}"),
            ("Average Highlight Score", f"{m['average_highlight_score']:.4f}"),
            ("Average Confidence", f"{m['average_confidence']:.4f}"),
            ("Processing Time (s)", str(m["processing_time_seconds"])),
            ("Frames Analyzed", str(m["frames_analyzed"])),
            ("Fine Scan Frames", cls._fmt_optional(m.get("fine_scan_frames"))),
            ("Fine Scan %", fine_scan_pct_str),
            ("Adaptive Threshold", cls._fmt_optional(m.get("adaptive_threshold"))),
            ("Game Profile Detected", cls._fmt_optional(m.get("game_profile"))),
        ]

        table_lines = ["| Metric | Value |", "|--------|-------|"]
        for label, value in rows:
            table_lines.append(f"| {label} | {value} |")

        strengths, weaknesses, recommendations = (
            cls._generate_analysis(m)
        )

        def _bullets(items: list[str]) -> str:
            return "\n".join(f"- {item}" for item in items)

        profile_str = cls._fmt_optional(m.get("game_profile"))

        lines = [
            "# AGC Benchmark Report",
            "",
            f"**Benchmark:** {report['benchmark']}",
            f"**Date:** {report['evaluated_at']}",
            f"**Video:** {report['video']}",
            f"**Profile:** {profile_str}",
            "",
            "## Metrics",
            "",
        ]
        lines.extend(table_lines)
        lines += [
            "",
            "## Summary",
            "",
            "### Strengths",
            "",
            _bullets(strengths),
            "",
            "### Weaknesses",
            "",
            _bullets(weaknesses),
            "",
            "### Recommendations",
            "",
            _bullets(recommendations),
            "",
        ]

        return "\n".join(lines)

    @staticmethod
    def _generate_analysis(
        m: dict
    ) -> tuple[list[str], list[str], list[str]]:
        precision = m["precision"]
        recall = m["recall"]
        f1 = m["f1_score"]
        avg_score = m["average_highlight_score"]
        avg_conf = m["average_confidence"]

        strengths: list[str] = []
        weaknesses: list[str] = []
        recommendations: list[str] = []

        if precision >= 0.8:
            strengths.append(
                "High precision — detected highlights are accurate"
            )
        if recall >= 0.8:
            strengths.append(
                "High recall — most expected highlights were found"
            )
        if f1 >= 0.8:
            strengths.append(
                "Strong F1 score — good overall detection balance"
            )
        if avg_score >= 0.6:
            strengths.append(
                "High average highlight score — confident detections"
            )
        if avg_conf >= 0.6:
            strengths.append(
                "High average confidence — strong weighted scoring"
            )

        if precision < 0.5:
            weaknesses.append(
                "Low precision — many false positives detected"
            )
            recommendations.append(
                "Raise the detection threshold to reduce false positives"
            )
        elif precision < 0.8:
            weaknesses.append(
                "Moderate precision — some false positives present"
            )
            recommendations.append(
                "Fine-tune threshold to improve precision"
            )

        if recall < 0.5:
            weaknesses.append(
                "Low recall — many expected highlights were missed"
            )
            recommendations.append(
                "Lower the detection threshold to catch more highlights"
            )
        elif recall < 0.8:
            weaknesses.append(
                "Moderate recall — some highlights are being missed"
            )
            recommendations.append(
                "Review scoring weights to improve recall"
            )

        if f1 < 0.5:
            weaknesses.append(
                "Low F1 score — detection quality needs improvement"
            )
            recommendations.append(
                "Re-evaluate scoring pipeline against ground truth"
            )

        if avg_score < 0.4:
            weaknesses.append(
                "Low average highlight score — detections lack confidence"
            )
            recommendations.append(
                "Review scoring weights for this game profile"
            )

        if not strengths:
            strengths.append(
                "No clear strengths identified — further tuning required"
            )
        if not weaknesses:
            weaknesses.append("No significant weaknesses detected")
        if not recommendations:
            recommendations.append(
                "Continue monitoring with additional video samples"
            )

        return strengths, weaknesses, recommendations

    @staticmethod
    def _append_csv(report: dict, csv_path: Path) -> None:
        m = report["metrics"]

        row: dict = {
            "benchmark": report["benchmark"],
            "video": report["video"],
            "profile": m.get("game_profile", ""),
            "precision": m["precision"],
            "recall": m["recall"],
            "f1": m["f1_score"],
            "avg_score": m["average_highlight_score"],
            "avg_confidence": m["average_confidence"],
            "processing_time": m["processing_time_seconds"],
            "frames_analyzed": m["frames_analyzed"],
            "fine_scan_frames": (
                m["fine_scan_frames"]
                if m.get("fine_scan_frames") is not None
                else ""
            ),
            "adaptive_threshold": (
                m["adaptive_threshold"]
                if m.get("adaptive_threshold") is not None
                else ""
            ),
            "detected_highlights": m["detected_highlights"],
        }

        fieldnames = list(row.keys())
        write_header = (
            not csv_path.exists() or csv_path.stat().st_size == 0
        )

        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow(row)
