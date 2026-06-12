"""Requirement analysis agent for structured story understanding."""

from __future__ import annotations

from agent.phase_contracts import RequirementAnalysisContract


class RequirementAnalysisAgent:
    """Transforms parsed Jira/prompt story data into engineering requirements."""

    def __init__(self, config: dict):
        self.config = config

    async def analyze(self, story_data: dict) -> RequirementAnalysisContract:
        title = story_data.get("title", "")
        requirements = [r.strip() for r in story_data.get("requirements", []) if r]
        acceptance = [c.strip() for c in story_data.get("acceptance_criteria", []) if c]
        technical_hints = [h.strip() for h in story_data.get("technical_hints", []) if h]

        non_functional: list[str] = []
        for req in requirements:
            low = req.lower()
            if any(k in low for k in ["performance", "secure", "security", "latency", "availability", "scale"]):
                non_functional.append(req)

        risks: list[str] = []
        for hint in technical_hints:
            low = hint.lower()
            if any(k in low for k in ["validate", "auth", "oauth", "jwt", "sql", "migration"]):
                risks.append(f"Implementation risk around: {hint}")

        return RequirementAnalysisContract(
            business_goal=title,
            functional_requirements=requirements,
            non_functional_requirements=non_functional,
            acceptance_criteria=acceptance,
            risks=risks,
            dependencies=technical_hints,
        )
