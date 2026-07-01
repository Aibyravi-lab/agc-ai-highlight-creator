import json
import time
from datetime import datetime, timezone
from pathlib import Path

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
        if all_highlights:
            avg_score = round(
                sum(h["score"] for h in all_highlights)
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
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "average_highlight_score": avg_score,
                "processing_time_seconds": processing_time,
            },
        }

        _RESULTS_DIR.mkdir(parents=True, exist_ok=True)

        report_path = _RESULTS_DIR / "evaluation_report.json"
        summary_path = _RESULTS_DIR / "evaluation_summary.txt"

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        with open(summary_path, "w") as f:
            f.write(cls._build_summary(report))

        print(f"Report saved: {report_path}")
        print(f"Summary saved: {summary_path}")

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
    def _build_summary(report: dict) -> str:
        m = report["metrics"]
        matches = report["matches"]

        tp = matches["true_positives"]
        fp = matches["false_positives"]
        fn = matches["false_negatives"]

        lines = [
            "AGC Highlight Quality Evaluation",
            "=" * 44,
            f"Benchmark      : {report['benchmark']}",
            f"Video          : {report['video']}",
            f"Evaluated at   : {report['evaluated_at']}",
            f"Tolerance      : ±{report['tolerance_seconds']} seconds",
            "",
            "Timestamps",
            "-" * 44,
            f"Expected       : {report['expected_timestamps']}",
            f"Detected       : {report['detected_timestamps']}",
            "",
            "Match Counts",
            "-" * 44,
            f"True Positives : {len(tp)}",
            f"False Positives: {len(fp)}",
            f"False Negatives: {len(fn)}",
            "",
            "Metrics",
            "-" * 44,
            f"Precision      : {m['precision']:.4f}",
            f"Recall         : {m['recall']:.4f}",
            f"F1 Score       : {m['f1_score']:.4f}",
            f"Avg Score      : {m['average_highlight_score']:.4f}",
            f"Processing Time: {m['processing_time_seconds']}s",
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
