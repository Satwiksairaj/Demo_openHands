"""Solution design agent that plans architecture before coding."""

from __future__ import annotations

from agent.phase_contracts import (
    ArchitectureContract,
    RequirementAnalysisContract,
    SolutionDesignContract,
)


class SolutionDesignerAgent:
    """Designs a concrete implementation approach from requirements and context."""

    def __init__(self, config: dict = None):  # noqa: B006
        self.config = config or {}

    async def design(
        self,
        requirements: RequirementAnalysisContract,
        architecture: ArchitectureContract,
        repository_analysis: dict,
        project_context: dict = None,
    ) -> SolutionDesignContract:
        """Design the solution approach from requirements and architecture."""
        repo = repository_analysis or {}

        entry_points = repo.get("entry_points", [])
        routes = repo.get("routes", [])
        models = repo.get("models", [])
        tests = repo.get("tests", [])

        files_to_modify = [f for f in entry_points + routes + models if f][:8]
        files_to_create: list[str] = []
        if not tests:
            files_to_create.append("test_app.py")

        implementation_steps: list[str] = []
        for module in getattr(architecture, "modules", []):
            implementation_steps.append(f"Implement module: {module}")

        for point in getattr(architecture, "integration_points", []):
            implementation_steps.append(f"Integrate with {point}")

        implementation_steps.extend(
            [
                "Review existing architecture and integration points",
                "Apply minimal scope code changes in impacted files",
                "Add tests for new functionality",
            ]
        )

        return SolutionDesignContract(
            files_to_modify=files_to_modify,
            files_to_create=files_to_create,
            architecture_changes=[f"Follow {architecture.architecture_style} pattern"],
            implementation_steps=implementation_steps,
            test_plan=["Unit tests for new endpoints", "Integration tests"],
            risks=getattr(architecture, "risks", []),
        )
