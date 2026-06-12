"""
Code Generation Agent - Delegates all code generation, fixing, and validation
to the OpenHands SDK via OpenHandsDevAgent.
"""

import ast
import logging
from pathlib import Path

# from typing import Optional

from agent.openhands_agent import OpenHandsDevAgent, TaskContext

logger = logging.getLogger(__name__)


class CodeGenerationAgent:
    """
    Code generation powered entirely by OpenHands.

    Wraps OpenHandsDevAgent to match the orchestrator's calling interface.
    """

    def __init__(self, config: dict):
        self.config = config
        self.agent = OpenHandsDevAgent(config)

    def _validate_generated_files(self, files: list[str]):
        """
        Validate generated Python files before returning.
        """

        for file in files:

            if not file.endswith(".py"):
                continue

            path = Path(file)

            if not path.exists():
                continue

            try:
                code = path.read_text(encoding="utf-8-sig", errors="ignore")
                code = code.lstrip("\ufeff")

                ast.parse(code)

            except SyntaxError as exc:
                raise RuntimeError(f"Generated invalid Python file " f"{file}: {exc}")

    async def initialize(self, workspace: str) -> None:
        """Initialize OpenHands runtime for the given workspace."""
        await self.agent.initialize(workspace)

    async def shutdown(self) -> None:
        """Shutdown OpenHands runtime."""
        await self.agent.shutdown()

    async def generate(
        self,
        story: dict,
        repo_analysis: dict,
        workspace: str,
        solution_design: dict | None = None,
        implementation_plan: dict | None = None,
        impact_analysis: dict | None = None,
    ) -> list[str]:
        """
        Generate implementation files for the given requirements.
        """

        await self.agent.initialize(workspace)

        context = TaskContext(
            requirements=story.get("requirements", []),
            acceptance_criteria=story.get("acceptance_criteria", []),
            repo_analysis=repo_analysis,
            technical_hints=story.get("technical_hints", []),
            testing_requirements=story.get("testing_requirements", []),
        )

        task_description = self._build_engineering_task_prompt(
            story=story,
            repo_analysis=repo_analysis,
            solution_design=solution_design or {},
            implementation_plan=implementation_plan or {},
            impact_analysis=impact_analysis or {},
        )

        result = await self.agent.generate_code(task_description, context)

        if not result.success:
            logger.warning(f"OpenHands generation reported issues: " f"{result.errors}")

        modified = result.files_created + result.files_modified

        # NEW VALIDATION STEP
        self._validate_generated_files(modified)

        for f in modified:
            logger.info(f"Written: {f}")

        return modified

    def _build_engineering_task_prompt(
        self,
        story: dict,
        repo_analysis: dict,
        solution_design: dict,
        implementation_plan: dict,
        impact_analysis: dict,
    ) -> str:
        requirements = story.get("requirements", [])
        acceptance = story.get("acceptance_criteria", [])

        files_to_modify = impact_analysis.get("files_to_modify", [])
        files_to_create = impact_analysis.get("files_to_create", [])
        files_to_avoid = impact_analysis.get("files_to_avoid", [])

        steps = implementation_plan.get("implementation_steps", [])
        style = repo_analysis.get("coding_style", {})

        return (
            f"Engineering task: {story.get('title', 'Implementation')}\n\n"
            "Repository understanding:\n"
            f"- Framework: {repo_analysis.get('framework', 'unknown')}\n"
            f"- Architecture: {repo_analysis.get('architecture', 'unknown')}\n"
            f"- Language: {repo_analysis.get('language', 'unknown')}\n"
            f"- Coding style: {style}\n"
            f"- Entry points: {repo_analysis.get('entry_points', [])}\n"
            f"- Services: {repo_analysis.get('services', [])}\n"
            f"- Routes: {repo_analysis.get('routes', [])}\n"
            f"- Models: {repo_analysis.get('models', [])}\n\n"
            "Requirements:\n"
            + "\n".join(f"- {r}" for r in requirements)
            + "\n\nAcceptance Criteria:\n"
            + "\n".join(f"- {a}" for a in acceptance)
            + "\n\nSolution Design:\n"
            + "\n".join(
                f"- {s}" for s in solution_design.get("implementation_steps", [])
            )
            + "\n\nImplementation Plan:\n"
            + "\n".join(f"- {s}" for s in steps)
            + "\n\nImpact Constraints:\n"
            + f"- Files to modify: {files_to_modify}\n"
            + f"- Files to create: {files_to_create}\n"
            + f"- Files to avoid: {files_to_avoid}\n\n"
            "Rules:\n"
            "- Never create random files.\n"
            "- Never rewrite unrelated files.\n"
            "- Follow existing architecture and conventions.\n"
            "- Reuse existing code whenever possible.\n"
            "- Implement only after understanding and design phases are complete.\n"
        )

    async def fix_from_test_output(
        self,
        test_results: dict,
        workspace: str,
        repo_analysis: dict,
    ) -> list[str]:
        """
        Analyze test failures and fix the code via OpenHands.
        """

        logger.info("Delegating fix to OpenHands agent...")

        context = TaskContext(repo_analysis=repo_analysis)

        result = await self.agent.fix_code(
            test_output=test_results.get("output", ""),
            error_message=test_results.get("error", ""),
            context=context,
        )

        self._validate_generated_files(result.files_modified)

        for f in result.files_modified:
            logger.info(f"Fixed: {f}")

        return result.files_modified

    async def validate_acceptance_criteria(
        self,
        story: dict,
        workspace: str,
        test_results: dict,
    ) -> dict:
        """
        Validate implementation against acceptance criteria
        using OpenHands.
        """

        return await self.agent.validate_implementation(
            acceptance_criteria=story.get("acceptance_criteria", []),
            test_results=test_results,
        )
