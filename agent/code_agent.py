# """
# Code Generation Agent - Delegates all code generation, fixing, and validation
# to the OpenHands SDK via OpenHandsDevAgent.
# """
# import logging
# from typing import Optional
# import ast
# from pathlib import Path
# from agent.openhands_agent import OpenHandsDevAgent, TaskContext

# logger = logging.getLogger(__name__)

# # This agent is a thin wrapper around OpenHandsDevAgent to fit the orchestrator's expected interface.

# class CodeGenerationAgent:
#     """
#     Code generation powered entirely by OpenHands.
#     Wraps OpenHandsDevAgent to match the orchestrator's calling interface.
#     """

#     def __init__(self, config: dict):
#         self.config = config
#         self.agent = OpenHandsDevAgent(config)
#     def _validate_generated_files(self, files: list[str]):
#      """
#      Validate generated Python files before returning.
#      """

#     for file in files:

#         if not file.endswith(".py"):
#             continue

#         path = Path(file)

#         if not path.exists():
#             continue

#         try:
#             code = path.read_text(
#                 encoding="utf-8",
#                 errors="ignore"
#             )

#             ast.parse(code)

#         except SyntaxError as exc:
#             raise RuntimeError(
#                 f"Generated invalid Python file "
#                 f"{file}: {exc}"
#             )
#     async def initialize(self, workspace: str) -> None:
#         """Initialize OpenHands runtime for the given workspace."""
#         await self.agent.initialize(workspace)

#     async def shutdown(self) -> None:
#         """Shutdown the OpenHands runtime."""
#         await self.agent.shutdown()

#     async def generate(
#         self,
#         story: dict,
#         repo_analysis: dict,
#         workspace: str
#     ) -> list[str]:
#         """Generate implementation files for the given requirements."""
#         await self.agent.initialize(workspace)

#         context = TaskContext(
#             requirements=story.get("requirements", []),
#             acceptance_criteria=story.get("acceptance_criteria", []),
#             repo_analysis=repo_analysis,
#             technical_hints=story.get("technical_hints", []),
#             testing_requirements=story.get("testing_requirements", []),
#         )

#         task_description = (
#             f"Implement the following story: {story.get('title', '')}\n\n"
#             "Requirements:\n" +
#             "\n".join(f"- {r}" for r in story.get("requirements", []))
#         )

#         result = await self.agent.generate_code(task_description, context)

#         if not result.success:
#             logger.warning(f"OpenHands generation reported issues: {result.errors}")

#         modified = result.files_created + result.files_modified
#         self._validate_generated_files(modified)
#         for f in modified:
#             logger.info(f"  Written: {f}")
#         return modified

#     async def fix_from_test_output(
#         self,
#         test_results: dict,
#         workspace: str,
#         repo_analysis: dict
#     ) -> list[str]:
#         """Analyze test failures and fix the code via OpenHands."""
#         logger.info("Delegating fix to OpenHands agent...")

#         context = TaskContext(repo_analysis=repo_analysis)
#         result = await self.agent.fix_code(
#             test_output=test_results.get("output", ""),
#             error_message=test_results.get("error", ""),
#             context=context,
#         )

#         for f in result.files_modified:
#             logger.info(f"  Fixed: {f}")
#         return result.files_modified

#     async def validate_acceptance_criteria(
#         self,
#         story: dict,
#         workspace: str,
#         test_results: dict
#     ) -> dict:
#         """Validate implementation against acceptance criteria via OpenHands."""
#         return await self.agent.validate_implementation(
#             acceptance_criteria=story.get("acceptance_criteria", []),
#             test_results=test_results,
#         )

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
                code = path.read_text(encoding="utf-8", errors="ignore")

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

        task_description = (
            f"Implement the following story: "
            f"{story.get('title', '')}\n\n"
            f"Requirements:\n"
            + "\n".join(f"- {r}" for r in story.get("requirements", []))
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
