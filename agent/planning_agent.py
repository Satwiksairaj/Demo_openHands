"""Implementation planning agent."""

from __future__ import annotations

from agent.phase_contracts import (
    ArchitectureContract,
    ImpactAnalysisContract,
    ImplementationPlanContract,
    ImplementationStep,
    RequirementAnalysisContract,
)


class PlanningAgent:
    def __init__(self, config: dict = None):  # noqa: B006
        self.config = config or {}

    def plan(
        self,
        requirements: RequirementAnalysisContract,
        architecture: ArchitectureContract,
        impact: ImpactAnalysisContract,
        repo_analysis=None,
    ) -> ImplementationPlanContract:
        files = impact.files_to_modify + impact.files_to_create
        steps = [
            ImplementationStep(
                order=i + 1,
                description=f"Update {path}",
                file_path=path,
                change_type="modify" if path in impact.files_to_modify else "create",
            )
            for i, path in enumerate(files)
        ]
        if not steps:
            steps = [
                ImplementationStep(order=1, description="Implement requested feature", file_path="", change_type="modify")
            ]
        return ImplementationPlanContract(
            implementation_steps=steps,
            test_strategy=["Add/adjust tests for acceptance criteria"],
            approach_summary=f"Implement using {architecture.architecture_style} approach",
        )
