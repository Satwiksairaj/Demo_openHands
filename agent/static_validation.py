"""Static validation agent for pre-test code quality gates."""

from __future__ import annotations

import subprocess

from agent.phase_contracts import StaticValidationContract


class StaticValidationAgent:
    """Runs py_compile, ruff, and mypy before test execution."""

    def __init__(self, config: dict = None):  # noqa: B006
        self.config = config or {}

    async def run(self, workspace: str) -> StaticValidationContract:
        checks = [
            ["python", "-m", "compileall", "."],
            ["ruff", "check", "."],
            ["mypy", "."],
        ]
        outputs: list[str] = []
        issues: list[str] = []

        for cmd in checks:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                outputs.append(f"$ {' '.join(cmd)}\\n{result.stdout}{result.stderr}")
                if result.returncode != 0:
                    text = (result.stdout + "\\n" + result.stderr).lower()
                    if "syntaxerror" in text:
                        issues.append("SyntaxError")
                    if "indentationerror" in text:
                        issues.append("IndentationError")
                    if "importerror" in text or "modulenotfounderror" in text:
                        issues.append("ImportError")
                    if "typeerror" in text:
                        issues.append("TypeError")
            except FileNotFoundError:
                outputs.append(f"$ {' '.join(cmd)}\\ncommand not found")
            except Exception as exc:
                outputs.append(f"$ {' '.join(cmd)}\\n{exc}")

        return StaticValidationContract(
            passed=len(issues) == 0,
            issues=list(dict.fromkeys(issues)),
            output="\\n\\n".join(outputs),
        )
