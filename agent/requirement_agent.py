"""Requirement analysis agent."""

from __future__ import annotations

from agent.phase_contracts import RequirementAnalysisContract


class RequirementAgent:
    def __init__(self):
        pass

    def analyse(self, prompt: str, story_id: str = "", repo_analysis=None) -> RequirementAnalysisContract:
        return RequirementAnalysisContract(
            functional_requirements=[f"Implement: {prompt}"],
            acceptance_criteria=["Feature works as requested"],
            story_id=story_id,
        )


class RequirementAnalysisAgent:
    """Backward-compatible async wrapper."""

    def __init__(self, config: dict = None):  # noqa: B006
        self._agent = RequirementAgent()

    async def analyze(self, story_data: dict) -> RequirementAnalysisContract:
        parts = [story_data.get("title", "")]
        parts.extend(story_data.get("requirements", []))
        prompt = " ".join(p for p in parts if p)
        return self._agent.analyse(prompt, story_id=story_data.get("story_id", ""))
