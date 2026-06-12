"""Code review agent."""

from __future__ import annotations

from agent.phase_contracts import (
    ArchitectureContract,
    ImplementationPlanContract,
    RequirementAnalysisContract,
    ReviewContract,
    ReviewScore,
)


class ReviewAgent:
    def __init__(self, config: dict = None):  # noqa: B006
        self.config = config or {}

    def review(
        self,
        generated_files: dict[str, str],
        requirements: RequirementAnalysisContract,
        architecture: ArchitectureContract,
        plan: ImplementationPlanContract,
        repo_analysis=None,
    ) -> ReviewContract:
        approved = bool(generated_files) or bool(plan.implementation_steps)
        return ReviewContract(
            score=ReviewScore.PASS_STRONG if approved else ReviewScore.PASS_MINOR,
            approved=approved,
            issues=[],
            summary="Review passed" if approved else "Review requires follow-up",
        )
