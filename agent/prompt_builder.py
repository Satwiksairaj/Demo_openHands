"""
Prompt Builder Agent - Converts structured requirements + repository analysis
into precise, context-aware implementation prompts for the code generation agent.
"""

import logging

logger = logging.getLogger(__name__)


class PromptBuilderAgent:
    """
    Builds high-quality, context-aware implementation prompts by combining:
    - Structured story requirements
    - Repository analysis (framework, patterns, conventions)
    - Solution design plan

    This decouples "what to build" from "how to ask the AI to build it",
    allowing prompts to be tailored per language, framework, and task type.
    """

    def build_solution_design_prompt(
        self, story_data: dict, repo_analysis: dict
    ) -> str:
        """Build a prompt that asks the AI to produce an architecture/design plan."""
        story_id = story_data.get("story_id", "")
        title = story_data.get("title", "")
        requirements = story_data.get("requirements", [])
        acceptance_criteria = story_data.get("acceptance_criteria", [])

        framework = repo_analysis.get("framework", "unknown")
        language = repo_analysis.get("language", "unknown")
        architecture = repo_analysis.get("architecture", "unknown")
        test_framework = repo_analysis.get("test_framework", "unknown")
        relevant_files = repo_analysis.get("relevant_files", [])
        existing_patterns = repo_analysis.get("existing_patterns", [])

        req_text = "\n".join(f"- {r}" for r in requirements)
        ac_text = "\n".join(f"- {c}" for c in acceptance_criteria)
        files_text = (
            "\n".join(f"- {f}" for f in relevant_files)
            if relevant_files
            else "- To be determined"
        )
        patterns_text = (
            "\n".join(f"- {p}" for p in existing_patterns)
            if existing_patterns
            else "- None detected"
        )

        return f"""You are a senior software architect. Produce a concise implementation plan.

## Story
ID: {story_id}
Title: {title}

## Requirements
{req_text}

## Acceptance Criteria
{ac_text}

## Repository Context
- Framework: {framework}
- Language: {language}
- Architecture: {architecture}
- Test Framework: {test_framework}
- Relevant Files: 
{files_text}
- Existing Patterns:
{patterns_text}

## Task
Return a JSON implementation plan with this exact structure:
{{
  "files_to_modify": ["path/to/file.py", ...],
  "files_to_create": ["path/to/new_file.py", ...],
  "tests_to_create": ["test_feature.py", ...],
  "implementation_steps": ["Step 1: ...", "Step 2: ...", ...],
  "api_changes": ["GET /endpoint returns ...", ...],
  "database_changes": ["Add column X to table Y", ...],
  "security_considerations": ["Validate input X", ...],
  "dependencies_to_add": ["package==version", ...],
  "risks": ["Risk 1", ...]
}}

Be specific. Every file path must be realistic for a {framework} / {language} project."""

    def build_implementation_prompt(
        self,
        story_data: dict,
        repo_analysis: dict,
        solution_design: dict,
        workspace: str,
        is_new_project: bool = False,
    ) -> str:
        """Build the full implementation prompt for the code generation agent."""
        story_id = story_data.get("story_id", "")
        title = story_data.get("title", "")
        requirements = story_data.get("requirements", [])
        acceptance_criteria = story_data.get("acceptance_criteria", [])
        testing_requirements = story_data.get("testing_requirements", [])

        framework = repo_analysis.get("framework", "unknown")
        language = repo_analysis.get("language", "unknown")
        test_framework = repo_analysis.get("test_framework", "pytest")
        coding_style = repo_analysis.get("coding_style", {})
        pkg_manager = repo_analysis.get("package_manager", "pip")

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
        test_req_text = (
            "\n".join(f"- {t}" for t in testing_requirements)
            if testing_requirements
            else ""
        )

        files_to_modify = solution_design.get("files_to_modify", [])
        files_to_create = solution_design.get("files_to_create", [])
        tests_to_create = solution_design.get("tests_to_create", [])
        steps = solution_design.get("implementation_steps", [])
        deps = solution_design.get("dependencies_to_add", [])

        modify_text = (
            "\n".join(f"- {f}" for f in files_to_modify) if files_to_modify else ""
        )
        create_text = (
            "\n".join(f"- {f}" for f in files_to_create) if files_to_create else ""
        )
        tests_text = (
            "\n".join(f"- {f}" for f in tests_to_create) if tests_to_create else ""
        )
        steps_text = (
            "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps)) if steps else ""
        )
        deps_text = " ".join(deps) if deps else ""

        install_cmd = {
            "npm": "npm install",
            "pip": f"pip install -q {deps_text}" if deps_text else "",
            "maven": "mvn install -q",
            "gradle": "gradle build -q",
            "cargo": "cargo build",
            "go modules": "go mod tidy",
        }.get(pkg_manager, f"pip install -q {deps_text}" if deps_text else "")

        test_cmd = {
            "pytest": "pytest test_*.py -v --tb=short",
            "jest": "npm test",
            "go test": "go test ./... -v",
            "cargo test": "cargo test",
            "junit": "mvn test",
        }.get(test_framework, "pytest test_*.py -v --tb=short")

        framework_rules = self._framework_rules(framework, language)

        # --- NEW PROJECT prompt ---
        if is_new_project:
            prompt = f"""# Build Task: [{story_id}] {title}

Working directory: {workspace}

## What to Build
{req_text}

"""
            if ac_text:
                prompt += f"## Acceptance Criteria\n{ac_text}\n\n"

            if create_text:
                prompt += f"## Files to Create\n{create_text}\n\n"

            if tests_text:
                prompt += f"## Test Files to Create\n{tests_text}\n\n"

            if test_req_text:
                prompt += f"## Testing Requirements\n{test_req_text}\n\n"

            if steps_text:
                prompt += f"## Implementation Plan\n{steps_text}\n\n"

            if framework_rules:
                prompt += f"## Framework Rules (MUST FOLLOW)\n{framework_rules}\n\n"

            prompt += f"""## Execution Instructions
1. Write each file COMPLETELY in a single operation — never create a file then immediately patch it.
2. {f'Run: {install_cmd}' if install_cmd else 'Install any needed packages with pip install -q <package>'}
3. Run tests: {test_cmd}
4. If a test fails: read the FULL error, identify the exact broken line, fix only that.
5. If SyntaxError or IndentationError: rewrite the ENTIRE file from scratch (4-space indentation, no tabs).
6. If the same str_replace fails twice: use file_editor create to overwrite the whole file.
7. Once all tests pass, call finish(). Do NOT make further changes.

## Code Quality Rules
- Language: {language}, Framework: {framework}
- {f'Indentation: {coding_style.get("indentation", "4 spaces")}' if coding_style else 'Use 4 spaces indentation'}
- Add type hints, docstrings, input validation, and error handling.
- Follow SOLID, DRY, KISS principles.
- Code must look like it was written by a senior engineer.
"""
            return prompt

        # --- MODIFY EXISTING PROJECT prompt ---
        prompt = f"""# Implementation Task: [{story_id}] {title}

Working directory: {workspace}

## Requirements
{req_text}

"""
        if ac_text:
            prompt += f"## Acceptance Criteria\n{ac_text}\n\n"

        if modify_text:
            prompt += f"## Files to Modify\n{modify_text}\n\n"

        if create_text:
            prompt += f"## New Files to Create\n{create_text}\n\n"

        if tests_text:
            prompt += f"## Tests to Write\n{tests_text}\n\n"

        if steps_text:
            prompt += f"## Implementation Steps\n{steps_text}\n\n"

        if framework_rules:
            prompt += f"## Framework Rules (MUST FOLLOW)\n{framework_rules}\n\n"

        prompt += f"""## Execution Instructions
1. Read the existing code first — understand the patterns before changing anything.
2. Modify only the listed files; do not touch unrelated code.
3. {f'Run: {install_cmd}' if install_cmd else 'Install any needed packages.'}
4. Run tests: {test_cmd}
5. Fix any failures — if SyntaxError: rewrite the whole file, not just the line.
6. Once all tests pass, call finish().

## Code Quality Rules
- Framework: {framework}, Language: {language}
- Follow existing code style — do not reformat unrelated code.
- Add type hints, docstrings, validation, and error handling to new code only.
"""
        return prompt

    def _framework_rules(self, framework: str, language: str) -> str:
        """Return mandatory structural rules for the detected framework."""
        fw = (framework or "").lower()
        lang = (language or "").lower()

        if "flask" in fw or ("python" in lang and "flask" in fw):
            return """FLASK ARCHITECTURE — MANDATORY:
- NEVER do `from app import db` inside models.py — this causes circular imports.
- ALWAYS put SQLAlchemy db instance in a separate file called extensions.py:
    # extensions.py
    from flask_sqlalchemy import SQLAlchemy
    db = SQLAlchemy()
- In models.py: `from extensions import db`
- In app.py: `from extensions import db` then `db.init_app(app)` AFTER creating the Flask app.
- Import models AFTER `db.init_app(app)` has been called.
- Use `db.create_all()` inside `with app.app_context():` before `app.run()`.
- In test files: import db from extensions, not from app.
- Flask app structure must be:
    extensions.py   ← db = SQLAlchemy()  (no imports from app or models)
    models.py       ← from extensions import db  (no import from app)
    app.py          ← from extensions import db; db.init_app(app); from models import ...
    seed_data.py    ← from extensions import db; from app import app
    test_app.py     ← from app import app; from extensions import db

FLASK FORMS / CSRF — MANDATORY:
- NEVER output `{{ csrf_token() }}` bare inside a form — it only outputs the value string, not an input field.
- ALWAYS use this exact pattern inside every <form method="post">:
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
- Every POST form in every template MUST have this hidden input or Flask-WTF returns 400 Bad Request.
- In tests: always set `app.config['WTF_CSRF_ENABLED'] = False` inside the test fixture."""

        if "django" in fw:
            return """DJANGO ARCHITECTURE — MANDATORY:
- Use Django's built-in ORM — never import models from within models.
- Keep settings in settings.py, never import from views inside models.
- Use `apps.py` for app config, not top-level imports."""

        if (
            "express" in fw
            or "node" in fw
            or "javascript" in lang
            or "typescript" in lang
        ):
            return """EXPRESS/NODE ARCHITECTURE — MANDATORY:
- NEVER require files that create circular dependencies (A requires B, B requires A).
- Put database connection in a separate db.js or database.js file.
- Models import from db.js — they never import from app.js or server.js.
- app.js/server.js imports models AFTER db connection is established.
- Use module.exports at the bottom of each file."""

        if "fastapi" in fw:
            return """FASTAPI ARCHITECTURE — MANDATORY:
- Put SQLAlchemy Base and engine in database.py — never in models.py or main.py.
- Models import Base from database.py only.
- main.py imports from routers, never the other way around.
- Use dependency injection (Depends) for db sessions — never create sessions globally."""

        return ""

    def build_fix_prompt(
        self,
        test_output: str,
        error_classification: dict,
        attempt: int,
        max_attempts: int,
        workspace: str,
    ) -> str:
        """Build a targeted fix prompt based on classified error type."""
        error_type = error_classification.get("type", "unknown")
        root_cause = error_classification.get("root_cause", "")
        fix_strategy = error_classification.get("fix_strategy", "")
        affected_files = error_classification.get("affected_files", [])

        files_text = (
            "\n".join(f"- {f}" for f in affected_files)
            if affected_files
            else "- See test output"
        )

        return f"""# Fix Attempt {attempt}/{max_attempts}

Working directory: {workspace}

## Error Classification
- Type: {error_type}
- Root Cause: {root_cause}
- Affected Files:
{files_text}

## Recommended Fix Strategy
{fix_strategy}

## Full Test Output
```
{test_output[:3000]}
```

## Fix Instructions
{self._fix_instructions_for_type(error_type)}

After fixing, run: pytest test_*.py -v --tb=short
Once all tests pass, call finish(). Do NOT continue editing after tests pass.
"""

    def _fix_instructions_for_type(self, error_type: str) -> str:
        instructions = {
            "SyntaxError": (
                "1. Open the file mentioned in the error.\n"
                "2. Rewrite the ENTIRE file from scratch with correct Python syntax.\n"
                "3. Use exactly 4 spaces for indentation — no tabs.\n"
                "4. Never attempt str_replace on a file with syntax errors."
            ),
            "IndentationError": (
                "1. Rewrite the ENTIRE file from scratch — do not patch individual lines.\n"
                "2. Use 4 spaces per indent level consistently throughout.\n"
                "3. Verify with: python -c \"import ast; ast.parse(open('file.py').read())\""
            ),
            "ImportError": (
                "1. Install the missing package: pip install -q <package_name>\n"
                "2. Check if the import path is correct for the project structure.\n"
                "3. If it's a local module, verify the file exists at the expected path."
            ),
            "ModuleNotFoundError": (
                "1. Install with: pip install -q <package_name>\n"
                "2. If it's a local import, check the file exists and has correct path.\n"
                "3. Add __init__.py if it's a package directory."
            ),
            "AssertionError": (
                "1. Read the assertion that failed — understand what was expected vs actual.\n"
                "2. Fix the implementation logic, not the test.\n"
                "3. Only fix the test if the requirement itself was wrong."
            ),
            "RuntimeError": (
                "1. Read the full stack trace to find the exact failing line.\n"
                "2. Add error handling around the problematic code.\n"
                "3. Check for None values, empty collections, or missing config."
            ),
            "DependencyError": (
                "1. Run: pip install -r requirements.txt (if it exists)\n"
                "2. Or install the specific missing package.\n"
                "3. Check version compatibility if package exists but import fails."
            ),
        }
        return instructions.get(
            error_type,
            "1. Read the error carefully.\n"
            "2. Identify the exact file and line number.\n"
            "3. Fix the root cause — do not suppress the error.\n"
            "4. Re-run tests after each fix attempt.",
        )
