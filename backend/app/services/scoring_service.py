from app.services.scoring.orchestrator import CATEGORY_WEIGHTS, ScoringOrchestrator


class ScoringService:

    CATEGORY_WEIGHTS = CATEGORY_WEIGHTS

    @classmethod
    def apply_category_weight(
        cls,
        score: float,
        category: str
    ):
        return ScoringOrchestrator.apply_category_weight(
            score=score,
            category=category
        )

    @classmethod
    def apply_action_weight(
        cls,
        score: float,
        action: str
    ):
        return ScoringOrchestrator.apply_action_weight(
            score=score,
            action=action
        )
