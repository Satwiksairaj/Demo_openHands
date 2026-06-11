"""
OpenHands Agent Wrapper - Uses OpenHands SDK v1.x (LocalConversation) for
autonomous code generation, fixing, and validation.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from agent.openhands_runtime import OpenHandsConfig, OpenHandsRuntime

logger = logging.getLogger(__name__)


@dataclass
class TaskContext:
    """Context information for a development task."""

    requirements: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    repo_analysis: dict = field(default_factory=dict)
    existing_files: dict = field(default_factory=dict)
    technical_hints: list[str] = field(default_factory=list)
    testing_requirements: list[str] = field(default_factory=list)


@dataclass
class TaskResult:
    """Result of an OpenHands development task."""

    success: bool
    files_created: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    test_output: str = ""
    tests_passed: bool = False
    iterations_used: int = 0
    agent_summary: str = ""
    errors: list[str] = field(default_factory=list)


class OpenHandsDevAgent:
    """
    High-level OpenHands agent for autonomous software development.
    Uses OpenHands SDK v1.x LocalConversation API.
    """

    def __init__(self, config: dict):
        self.oh_config = self._build_config(config)
        self.runtime = OpenHandsRuntime(self.oh_config)
        self._workspace_path: Optional[str] = None

    def _build_config(self, config: dict) -> OpenHandsConfig:
        return OpenHandsConfig(
            llm_model=config.get("llm_model", "openai/gpt-4o"),
            llm_api_key=config.get("openai_api_key", os.getenv("OPENAI_API_KEY", "")),
            llm_base_url=config.get("llm_base_url", "https://api.openai.com/v1"),
            agent_name=config.get("agent_name", "CodeActAgent"),
            sandbox_image=config.get(
                "sandbox_image",
                "docker.all-hands.dev/all-hands-ai/runtime:0.30-nikolaik",
            ),
            max_iterations=config.get("max_iterations", 50),
            workspace_base=config.get("workspace_base", "/tmp/agent-workspaces"),
            confirmation_mode=config.get("confirmation_mode", False),
        )

    async def initialize(self, workspace_path: str) -> None:
        self._workspace_path = workspace_path
        await self.runtime.initialize(workspace_path)
        logger.info(f"OpenHands agent ready at: {workspace_path}")

    async def shutdown(self) -> None:
        await self.runtime.shutdown()
        self._workspace_path = None

    async def generate_code(
        self, task_description: str, context: TaskContext
    ) -> TaskResult:
        prompt = self._build_generation_prompt(task_description, context)
        logger.info(f"Generating code: {task_description[:80]}...")
        result = await self.runtime.run_task(prompt, workspace=self._workspace_path)
        return TaskResult(
            success=result.success,
            files_modified=result.files_modified,
            agent_summary=result.output[:2000],
            errors=[result.error] if result.error else [],
        )

    async def fix_code(
        self, test_output: str, error_message: str, context: TaskContext
    ) -> TaskResult:
        prompt = (
            "Tests are failing. Fix the code so ALL tests pass.\n\n"
            f"## Test Output\n```\n{test_output[:4000]}\n```\n\n"
            "## Fix Instructions\n"
            "1. Read the error message carefully — identify the exact file and line.\n"
            "2. If the error is a SyntaxError or IndentationError: REWRITE the entire file from scratch with correct Python indentation (4 spaces, no tabs).\n"
            "3. If the error is an ImportError or ModuleNotFoundError: install the missing package with pip install <package>.\n"
            "4. If the error is a logic/assertion failure: fix only the specific function that is wrong.\n"
            "5. After fixing, run: pytest test_*.py -v --tb=short\n"
            "6. Once all tests pass, stop — do NOT make any more changes.\n"
            "7. NEVER attempt the same str_replace more than once — if a replacement fails, rewrite the whole file with file_editor create."
        )
        logger.info("Delegating fix to OpenHands agent...")
        result = await self.runtime.run_task(prompt, workspace=self._workspace_path)
        return TaskResult(
            success=result.success,
            files_modified=result.files_modified,
            agent_summary=result.output[:2000],
            errors=[result.error] if result.error else [],
        )

    async def validate_implementation(
        self, acceptance_criteria: list[str], test_results: dict
    ) -> dict:
        """Validate acceptance criteria against test results using direct OpenAI call."""
        from openai import AsyncOpenAI

        api_key = self.oh_config.llm_api_key
        client = AsyncOpenAI(api_key=api_key)

        criteria_text = "\n".join(f"- {c}" for c in acceptance_criteria)
        test_output = test_results.get("output", "")[:3000]
        passed = test_results.get("passed", False)

        prompt = f"""Evaluate whether this implementation meets its acceptance criteria.

ACCEPTANCE CRITERIA:
{criteria_text}

TEST RESULTS:
- Passed: {passed}
- Output: {test_output}

Return ONLY a JSON object:
{{
  "passed": true/false,
  "satisfied_criteria": ["..."],
  "missing_criteria": ["..."],
  "reason": "..."
}}"""

        try:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            raw_content = response.choices[0].message.content
            content = (raw_content or "").strip()
            import re

            content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("`")
            return json.loads(content)
        except Exception as e:
            logger.warning(f"Validation LLM call failed: {e}")
            return {
                "passed": passed,
                "satisfied_criteria": acceptance_criteria if passed else [],
                "missing_criteria": [] if passed else acceptance_criteria,
                "reason": "Validation based on test results",
            }

    def _build_generation_prompt(self, task: str, context: TaskContext) -> str:
        parts = [f"# Task\n{task}"]

        if context.requirements:
            reqs = "\n".join(f"- {r}" for r in context.requirements)
            parts.append(f"\n## Requirements\n{reqs}")

        if context.acceptance_criteria:
            criteria = "\n".join(f"- {c}" for c in context.acceptance_criteria)
            parts.append(f"\n## Acceptance Criteria\n{criteria}")

        if context.repo_analysis:
            a = context.repo_analysis
            parts.append(
                f"\n## Repository Context"
                f"\n- Framework: {a.get('framework', 'unknown')}"
                f"\n- Language: {a.get('language', 'unknown')}"
                f"\n- Test framework: {a.get('test_framework', 'unknown')}"
            )

        if context.technical_hints:
            hints = "\n".join(f"- {h}" for h in context.technical_hints)
            parts.append(f"\n## Technical Hints\n{hints}")

        if context.testing_requirements:
            tests = "\n".join(f"- {t}" for t in context.testing_requirements)
            parts.append(f"\n## Testing Requirements\n{tests}")

        parts.append(
            "\n## Instructions"
            "\n1. Analyse the existing code in the workspace"
            "\n2. Implement the changes following existing patterns"
            "\n3. Write or update tests for your changes"
            "\n4. Run the tests to confirm they pass"
            "\n5. Do not break existing functionality"
        )

        return "\n".join(parts)


class OpenHandsWorkflowIntegration:
    """
    Orchestrator-facing integration layer that wraps OpenHandsDevAgent
    to provide workflow-level methods.
    """

    def __init__(self, config: dict):
        self._agent = OpenHandsDevAgent(config)
        self._initialized = False

    async def setup(self, workspace: str) -> None:
        await self._agent.initialize(workspace)
        self._initialized = True

    async def teardown(self) -> None:
        await self._agent.shutdown()
        self._initialized = False

    async def generate_implementation(
        self, story_data: dict, repo_analysis: dict, workspace: str
    ) -> list[str]:
        import subprocess as _sp

        if not self._initialized:
            await self.setup(workspace)

        context = TaskContext(
            requirements=story_data.get("requirements", []),
            acceptance_criteria=story_data.get("acceptance_criteria", []),
            repo_analysis=repo_analysis,
            technical_hints=story_data.get("technical_hints", []),
            testing_requirements=story_data.get("testing_requirements", []),
        )

        title = story_data.get("title", "Implement feature")
        requirements = story_data.get("requirements", [])
        acceptance_criteria = story_data.get("acceptance_criteria", [])
        testing_requirements = story_data.get("testing_requirements", [])
        req_text = (
            "\n".join(f"- {r}" for r in requirements)
            if requirements
            else "- See acceptance criteria"
        )
        ac_text = (
            "\n".join(f"- {c}" for c in acceptance_criteria)
            if acceptance_criteria
            else ""
        )
        tst_text = (
            "\n".join(f"- {t}" for t in testing_requirements)
            if testing_requirements
            else ""
        )

        # Detect whether this is a brand-new project or a modification of existing code.
        # A workspace with ≤2 tracked files is treated as "new project".
        try:
            _r = _sp.run(
                ["git", "ls-files"],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=10,
            )
            tracked = [f for f in _r.stdout.strip().splitlines() if f]
        except Exception:
            tracked = []

        is_new_project = len(tracked) <= 2

        if is_new_project:
            task = (
                f"# Build: {title}\n\n"
                f"Create a complete new project from scratch inside the directory: {workspace}\n"
                f"The directory may be empty or contain only unrelated files — ignore them.\n\n"
                f"## Requirements\n{req_text}\n\n"
            )
            if ac_text:
                task += f"## Acceptance Criteria\n{ac_text}\n\n"
            if tst_text:
                task += f"## Tests Required\n{tst_text}\n\n"
            task += (
                "## Step-by-step Instructions\n"
                "1. Plan the files you need (e.g. app.py, models.py, templates/index.html, test_app.py).\n"
                "2. Create each file COMPLETELY in one write — do not create a file then immediately patch it.\n"
                "3. Install required packages with: pip install <packages> -q\n"
                "4. Run the tests with: pytest test_*.py -v --tb=short\n"
                "5. If tests fail, READ the full error, then rewrite only the broken section.\n"
                "6. Once all tests pass, call finish(). Do NOT keep editing after tests pass.\n"
                "7. Never make the same edit attempt more than twice — if it fails twice, rewrite the whole file fresh.\n\n"
                "## CRITICAL: Python/Flask Architecture Rules (ALWAYS APPLY)\n"
                "CIRCULAR IMPORT PREVENTION:\n"
                "- NEVER do `from app import db` inside models.py — circular ImportError.\n"
                "- Create extensions.py containing ONLY: `from flask_sqlalchemy import SQLAlchemy; db = SQLAlchemy()`\n"
                "- models.py: `from extensions import db`\n"
                "- app.py: `from extensions import db` then `db.init_app(app)` after app = Flask(__name__)\n"
                "- test files: `from extensions import db`\n\n"
                "FORMS / CSRF:\n"
                "- NEVER use CSRFProtect or flask_wtf. It causes HTTP 400 on every POST form submission.\n"
                "- NEVER add `from flask_wtf.csrf import CSRFProtect` or `csrf = CSRFProtect(app)` anywhere.\n"
                "- NEVER add {{ csrf_token() }} to templates.\n"
                '- Use plain HTML forms: <form method="post"> with no CSRF tokens.\n'
                "- app.py imports: `from flask import Flask, render_template, request, redirect, url_for, flash, jsonify`\n"
                "- Do NOT import flask_wtf anywhere.\n\n"
                "For FastAPI: put engine/Base in database.py, import from there in models.py\n"
                "For Node/Express: put db connection in db.js, import from there in models — never from app.js"
            )
        else:
            phase_requirements = (
                "# Autonomous Feature Enhancement Mode\n\n"
                "You are a Senior Software Engineer, Software Architect, Code Reviewer, QA Engineer, and DevOps Engineer.\n"
                "Primary responsibility is to integrate requested work into the existing repository architecture.\n"
                "Do not rebuild the application unless explicitly required.\n\n"
                "## Global Rules\n"
                "- Analyze before coding\n"
                "- Reuse before creating\n"
                "- Extend before replacing\n"
                "- Modify before regenerating\n"
                "- Review before finishing\n"
                "- Only modify the minimum required files\n"
                "- Never duplicate existing logic\n\n"
                "## Required Phases\n"
                "PHASE 1 Task Classification:\n"
                "- Classify as one of: New Application, Feature Enhancement, Bug Fix, Refactoring, Performance Optimization, Test Generation, Documentation Update, Security Improvement.\n"
                "- If repository exists, default to Feature Enhancement unless clear evidence suggests otherwise.\n"
                "- Output: Task Type, Reason, Confidence.\n\n"
                "PHASE 2 Repository Understanding:\n"
                "- Analyze structure, framework, architecture, dependencies, modules, models, services, APIs, routes, templates, tests.\n"
                "- Output: Framework, Architecture Pattern, Database, Authentication Mechanism, Coding Style, Testing Framework, Important Modules, Existing Features.\n\n"
                "PHASE 3 Impact Analysis:\n"
                "- Identify exact files to modify and minimal new files if required.\n"
                "- Output: Affected Files, New Files Required, Database Changes, API Changes, UI Changes, Test Changes.\n\n"
                "PHASE 4 Reuse Analysis:\n"
                "- Find and reuse existing models, services, utilities, helpers, middleware.\n"
                "- Output: Reusable Components, Files Reused, Logic Reused, Dependencies Reused.\n\n"
                "PHASE 5 Implementation Plan:\n"
                "- Provide an ordered implementation roadmap with concrete file targets.\n"
                "- Do not write code before completing phases 1 to 5.\n\n"
                "PHASE 6 Code Generation:\n"
                "- Implement production-ready changes with type hints, docstrings, validation, logging, error handling.\n"
                "- Follow SOLID, DRY, KISS and existing architecture.\n"
                "- Do not rewrite unrelated files.\n\n"
                "PHASE 7 Test Generation:\n"
                "- Add relevant unit/integration/API/edge tests using existing test style.\n"
                "- Avoid duplicate tests.\n\n"
                "PHASE 8 Validation:\n"
                "- Validate syntax, imports, startup, database behavior, APIs, templates, acceptance criteria.\n"
                "- Output Validation Report with pass/fail summary.\n\n"
                "PHASE 9 Code Review:\n"
                "- Perform self-review for duplication, security, naming, architecture fit, missing validation/tests.\n"
                "- Output Quality Score, Issues Found, Fixes Applied.\n"
                "- If score < 90, refactor before finish.\n\n"
                "PHASE 10 Git Preparation:\n"
                "- Output Branch Name, Commit Message, Modified Files Summary.\n\n"
                "PHASE 11 PR Preparation:\n"
                "- Output PR Title, PR Description, Modified Files, Test Results, Risk Assessment, Deployment Notes.\n"
            )

            task = (
                f"Implement the following feature in the existing codebase at: {workspace}\n\n"
                f"## Feature\n{title}\n\n"
                f"## Requirements\n{req_text}\n\n"
                f"{phase_requirements}\n\n"
                "## Instructions\n"
                "1. Study the existing code structure first.\n"
                "2. Execute phases 1 to 5 as written above before changing code.\n"
                "3. Add the feature to existing files where it belongs; create new files only when necessary.\n"
                "4. Follow existing code patterns, naming conventions, and file structure.\n"
                "5. Reuse existing logic and dependencies whenever possible.\n"
                "6. Write focused tests for your specific changes only.\n"
                "7. Run relevant tests and fix failures without altering unrelated behavior.\n"
                "8. Provide final output sections for phases 8 to 11 before finish."
            )

        result = await self._agent.generate_code(task, context)
        return result.files_modified

    async def run_tests_with_retry(
        self,
        workspace: str,
        project_type: str,
        repo_analysis: dict,
        max_retries: int = 3,
        generated_files: Optional[list[str]] = None,
    ) -> dict:
        if not self._initialized:
            await self.setup(workspace)

        test_commands = {
            "nodejs": "npm test",
            "python": "pytest -v --tb=short -x",
            "go": "go test ./... -v",
            "rust": "cargo test",
            "java-maven": "mvn test",
            "java-gradle": "gradle test",
        }
        base_cmd = test_commands.get(project_type, "pytest -v -x")

        # Scope pytest to only new/modified test files to avoid running entire test suite
        test_cmd = base_cmd
        if project_type in ("python", None):
            explicit_tests = [
                f
                for f in (generated_files or [])
                if f.endswith(".py")
                and ("test" in f.lower() or f.lower().startswith("test"))
            ]
            if not explicit_tests:
                # Auto-discover any test_*.py in the workspace root
                import glob as _glob

                explicit_tests = [
                    os.path.basename(p)
                    for p in _glob.glob(os.path.join(workspace, "test_*.py"))
                ]
            if explicit_tests:
                test_cmd = f"pytest -v --tb=short -x {' '.join(explicit_tests)}"

        for attempt in range(1, max_retries + 1):
            result = await self._agent.runtime.run_command(
                test_cmd, working_dir=workspace
            )
            if result.success:
                return {"passed": True, "output": result.output, "attempts": attempt}

            if attempt < max_retries:
                logger.info(f"Tests failed (attempt {attempt}), asking agent to fix...")
                fix_context = TaskContext(repo_analysis=repo_analysis)
                await self._agent.fix_code(
                    test_output=result.output,
                    error_message=result.error,
                    context=fix_context,
                )

        return {"passed": False, "output": result.output, "attempts": max_retries}

    async def validate_and_verify(
        self, story_data: dict, test_results: dict, workspace: Optional[str] = None
    ) -> dict:
        return await self._agent.validate_implementation(
            acceptance_criteria=story_data.get("acceptance_criteria", []),
            test_results=test_results,
        )
