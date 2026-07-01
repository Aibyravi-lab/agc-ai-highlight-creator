"""
AGC Highlight Quality Evaluator

Usage:
    python run_evaluation.py <benchmark.json> [tolerance_seconds]

Examples:
    python run_evaluation.py sample_benchmark.json
    python run_evaluation.py sample_benchmark.json 3
"""

import sys
from pathlib import Path

# Make backend importable without installing as a package
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.evaluation_service import EvaluationService


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    benchmark_arg = sys.argv[1]
    tolerance = (
        int(sys.argv[2])
        if len(sys.argv) > 2
        else EvaluationService.DEFAULT_TOLERANCE
    )

    benchmark_path = Path(benchmark_arg)
    if not benchmark_path.is_absolute():
        benchmark_path = Path(__file__).parent / benchmark_arg

    if not benchmark_path.exists():
        print(f"Error: benchmark file not found: {benchmark_path}")
        sys.exit(1)

    print(f"Benchmark : {benchmark_path.name}")
    print(f"Tolerance : ±{tolerance} seconds")
    print()

    report = EvaluationService.evaluate(
        benchmark_path=str(benchmark_path),
        tolerance=tolerance
    )

    m = report["metrics"]
    print()
    print("Results")
    print("-" * 44)
    print(f"Precision      : {m['precision']:.4f}")
    print(f"Recall         : {m['recall']:.4f}")
    print(f"F1 Score       : {m['f1_score']:.4f}")
    print(f"Avg Score      : {m['average_highlight_score']:.4f}")
    print(f"Processing Time: {m['processing_time_seconds']}s")
    print()


if __name__ == "__main__":
    main()
