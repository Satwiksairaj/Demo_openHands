"""Implementation planning agent that creates executable engineering steps."""

from __future__ import annotations

from agent.phase_contracts import (
    ImpactAnalysisContract,
    ImplementationPlanContract,
    SolutionDesignContract,
)


class PlanningAgent:
    """Builds a deterministic implementation roadmap from design and impact."""

    def __init__(self, config: dict):
        self.config = config

    async def plan(
        self,
        solution_design: SolutionDesignContract,
        impact_analysis: ImpactAnalysisContract,
    ) -> ImplementationPlanContract:
        steps: list[str] = []

        for file_path in impact_analysis.files_to_modify:
            steps.append(f"Modify {file_path}")
        for file_path in impact_analysis.files_to_create:
            steps.append(f"Create {file_path}")

        for design_step in solution_design.implementation_steps:
            steps.append(design_step)

        steps.extend(
            [
                "Run static validation",
                "Run targeted tests",
                "Run full test suite",
            ]
        )

        return ImplementationPlanContract(implementation_steps=steps)
