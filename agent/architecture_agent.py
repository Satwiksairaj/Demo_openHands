from agent.phase_contracts import (
    ArchitectureContract,
    RequirementAnalysisContract,
)

class ArchitectureAgent:

    def __init__(self, config):
        self.config = config
    
    async def analyze(
        self,
        requirements: RequirementAnalysisContract,
        repo_analysis: dict | None = None,
    ) -> ArchitectureContract:

        return await self.design(
            requirements,
            repo_analysis or {},
        )

    async def design(
        self,
        requirements: RequirementAnalysisContract,
        repo_analysis: dict,
    ) -> ArchitectureContract:

        framework = repo_analysis.get("framework", "")

        modules = []

        text = " ".join(requirements.functional_requirements).lower()

        if "auth" in text:
            modules.append("Authentication")

        if "user" in text:
            modules.append("User")

        if "notification" in text:
            modules.append("Notification")

        return ArchitectureContract(
            architecture_style=framework,
            modules=modules,
            integration_points=[
                "API Layer",
                "Service Layer",
                "Database Layer",
            ],
            risks=requirements.risks,
        )
    
