class ClipScorer:

    @staticmethod
    def score(clip_result: dict) -> float:
        return float(clip_result["score"])
