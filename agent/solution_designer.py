"""Solution design agent that plans architecture before coding."""

from __future__ import annotations

from agent.phase_contracts import (
    ArchitectureContract,
    RequirementAnalysisContract,
    SolutionDesignContract,
    
)
from app.services.project_context_manager import ProjectContext


class SolutionDesignerAgent:
    """Designs a concrete implementation approach from requirements and context."""

    def __init__(self, config: dict):
        self.config = config

    async def design(
        self,
        requirements: RequirementAnalysisContract,
        architecture: ArchitectureContract,
        repository_analysis: dict,
        project_context: ProjectContext,
    ) -> SolutionDesignContract:
        entry_points = repository_analysis.get("entry_points", [])
        routes = repository_analysis.get("routes", [])
        models = repository_analysis.get("models", [])
        tests = repository_analysis.get("tests", [])

        files_to_modify = [f for f in entry_points + routes + models if f][:8]
        files_to_create = []
        if not tests:
            files_to_create.append("test_app.py")

        implementation_steps = []
        for module in architecture.modules:
            implementation_steps.append(
                f"Implement module: {module}"
            )
        
        for point in architecture.integration_points:
            implementation_steps.append(
                f"Integrate with {point}"
            )
        
        implementation_steps.extend([
            "Review existing architecture and integration points",
            "Apply minimal scope code changes in impacted files",
            "Add or update tests for changed behavior",
            "Run static validation and test suite",
        ])

        return SolutionDesignContract(
            files_to_modify=files_to_modify,
            files_to_create=files_to_create,
            architecture_changes=[
                f"Architecture style: {architecture.architecture_style}",
                *[
                    f"Module required: {m}"
                    for m in architecture.modules
                ],
            ],
                
            implementation_steps=implementation_steps,
            test_plan=requirements.acceptance_criteria,
            risks=requirements.risks,
        )
