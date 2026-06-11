"""
Testing Agent - Executes builds, linting, and tests in the sandbox environment.
Supports Node.js, Python, Go, Java, and Rust projects.
"""

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    passed: bool
    output: str
    error: str = ""
    duration: float = 0.0
    test_count: int = 0
    failed_count: int = 0


class TestingAgent:
    """
    Detects the project type and runs appropriate build/test commands.
    Supports multiple language ecosystems.
    """

    def __init__(self, config: dict):
        self.config = config
        self.timeout = config.get("test_timeout", 300)

    async def run_all(self, workspace: str) -> dict:
        """Run the complete test suite: install, lint, build, test."""
        project_type = self._detect_project_type(workspace)
        logger.info(f"Detected project type: {project_type}")

        runner = self._get_runner(project_type)
        results = await runner(workspace)

        return {
            "passed": results.passed,
            "output": results.output,
            "error": results.error,
            "duration": results.duration,
            "test_count": results.test_count,
            "failed_count": results.failed_count,
            "project_type": project_type,
        }

    def _detect_project_type(self, workspace: str) -> str:
        """Detect the project type from configuration files."""
        indicators = {
            "nodejs": ["package.json"],
            "python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
            "go": ["go.mod"],
            "java-maven": ["pom.xml"],
            "java-gradle": ["build.gradle", "build.gradle.kts"],
            "rust": ["Cargo.toml"],
        }
        for project_type, files in indicators.items():
            for fname in files:
                if os.path.exists(os.path.join(workspace, fname)):
                    return project_type
        return "unknown"

    def _get_runner(self, project_type: str):
        """Return the appropriate test runner for the project type."""
        runners = {
            "nodejs": self._run_nodejs,
            "python": self._run_python,
            "go": self._run_go,
            "java-maven": self._run_maven,
            "java-gradle": self._run_gradle,
            "rust": self._run_rust,
        }
        return runners.get(project_type, self._run_generic)

    async def _run_nodejs(self, workspace: str) -> TestResult:
        """Run Node.js project tests."""
        import json

        # Read package.json to understand available scripts
        pkg_path = os.path.join(workspace, "package.json")
        with open(pkg_path) as f:
            pkg = json.load(f)
        scripts = pkg.get("scripts", {})

        output_parts = []

        # Install dependencies
        logger.info("Installing Node.js dependencies...")
        result = self._run_command(
            ["npm", "install", "--legacy-peer-deps"], workspace, timeout=120
        )
        output_parts.append("=== npm install ===\n" + result.stdout + result.stderr)
        if result.returncode != 0:
            return TestResult(
                passed=False, output="\n".join(output_parts), error="npm install failed"
            )

        # Lint
        if "lint" in scripts:
            logger.info("Running linter...")
            result = self._run_command(
                ["npm", "run", "lint", "--", "--max-warnings=0"], workspace
            )
            output_parts.append(
                "=== npm run lint ===\n" + result.stdout + result.stderr
            )

        # Build (if TypeScript or build script exists)
        if "build" in scripts:
            logger.info("Building project...")
            result = self._run_command(["npm", "run", "build"], workspace)
            output_parts.append(
                "=== npm run build ===\n" + result.stdout + result.stderr
            )
            if result.returncode != 0:
                return TestResult(
                    passed=False, output="\n".join(output_parts), error="Build failed"
                )

        # Tests
        if "test" in scripts:
            logger.info("Running tests...")
            env = {**os.environ, "CI": "true", "NODE_ENV": "test"}
            result = self._run_command(
                ["npm", "test", "--", "--watchAll=false", "--passWithNoTests"],
                workspace,
                env=env,
            )
            output_parts.append("=== npm test ===\n" + result.stdout + result.stderr)
            passed = result.returncode == 0
            test_count, failed_count = self._parse_jest_output(
                result.stdout + result.stderr
            )

            return TestResult(
                passed=passed,
                output="\n".join(output_parts),
                test_count=test_count,
                failed_count=failed_count,
                error="" if passed else "Tests failed",
            )

        return TestResult(passed=True, output="\n".join(output_parts))

    async def _run_python(self, workspace: str) -> TestResult:
        """Run Python project tests."""
        output_parts = []
        # Auto-format generated code
        logger.info("Running black...")
        black_result = self._run_command(["black", "."], workspace, check=False)

        output_parts.append(
            "--- black ---\n" + black_result.stdout + black_result.stderr
        )

        # Auto-fix lint issues
        logger.info("Running ruff...")
        ruff_result = self._run_command(
            ["ruff", "check", ".", "--fix"], workspace, check=False
        )

        output_parts.append("--- ruff ---\n" + ruff_result.stdout + ruff_result.stderr)

        # Compile all Python files
        logger.info("Validating Python syntax...")

        for py_file in Path(workspace).rglob("*.py"):

            compile_result = self._run_command(
                ["python", "-m", "py_compile", str(py_file)], workspace, check=False
            )

            if compile_result.returncode != 0:
                return TestResult(
                    passed=False,
                    output=compile_result.stdout,
                    error=compile_result.stderr,
                )
        # Install dependencies
        logger.info("Installing Python dependencies...")
        if os.path.exists(os.path.join(workspace, "pyproject.toml")):
            result = self._run_command(["pip", "install", "-e", ".[dev]"], workspace)
        elif os.path.exists(os.path.join(workspace, "requirements.txt")):
            result = self._run_command(
                ["pip", "install", "-r", "requirements.txt"], workspace
            )
        else:
            result = self._run_command(["pip", "install", "-e", "."], workspace)

        output_parts.append("=== pip install ===\n" + result.stdout + result.stderr)
        # Black format check
        result = self._run_command(["black", "--check", "."], workspace, check=False)

        output_parts.append("=== black ===\n" + result.stdout + result.stderr)

        # Ruff lint
        result = self._run_command(["ruff", "check", "."], workspace, check=False)

        output_parts.append("=== ruff ===\n" + result.stdout + result.stderr)

        # Python syntax validation
        result = self._run_command(
            ["python", "-m", "compileall", "."], workspace, check=False
        )

        output_parts.append("=== compileall ===\n" + result.stdout + result.stderr)

        # Lint with ruff or flake8
        for linter in ["ruff", "flake8"]:
            result = self._run_command([linter, "."], workspace, check=False)
            if result.returncode != 127:  # 127 = not found
                output_parts.append(
                    f"=== {linter} ===\n" + result.stdout + result.stderr
                )
                break

        # Type check
        result = self._run_command(
            [
                "mypy",
                ".",
                "--ignore-missing-imports",
                "--install-types",
                "--non-interactive",
            ],
            workspace,
            check=False,
        )
        if result.returncode != 127:
            output_parts.append("=== mypy ===\n" + result.stdout + result.stderr)

        # Run tests
        logger.info("Running pytest...")
        result = self._run_command(
            ["python", "-m", "pytest", "-v", "--tb=short", "--no-header"], workspace
        )
        output_parts.append("=== pytest ===\n" + result.stdout + result.stderr)

        passed = result.returncode == 0
        test_count, failed_count = self._parse_pytest_output(result.stdout)

        return TestResult(
            passed=passed,
            output="\n".join(output_parts),
            test_count=test_count,
            failed_count=failed_count,
            error="" if passed else "Tests failed",
        )

    async def _run_go(self, workspace: str) -> TestResult:
        """Run Go project tests."""
        output_parts = []

        result = self._run_command(["go", "mod", "tidy"], workspace)
        output_parts.append("=== go mod tidy ===\n" + result.stdout)

        result = self._run_command(["go", "build", "./..."], workspace)
        output_parts.append("=== go build ===\n" + result.stdout + result.stderr)
        if result.returncode != 0:
            return TestResult(
                passed=False, output="\n".join(output_parts), error="Build failed"
            )

        result = self._run_command(["go", "test", "-v", "./..."], workspace)
        output_parts.append("=== go test ===\n" + result.stdout + result.stderr)

        return TestResult(
            passed=result.returncode == 0,
            output="\n".join(output_parts),
            error="" if result.returncode == 0 else "Tests failed",
        )

    async def _run_maven(self, workspace: str) -> TestResult:
        """Run Maven Java project tests."""
        result = self._run_command(
            ["mvn", "test", "-q", "--no-transfer-progress"], workspace, timeout=300
        )
        return TestResult(
            passed=result.returncode == 0,
            output=result.stdout + result.stderr,
            error="" if result.returncode == 0 else "Maven tests failed",
        )

    async def _run_gradle(self, workspace: str) -> TestResult:
        """Run Gradle Java project tests."""
        gradle_cmd = (
            "./gradlew"
            if os.path.exists(os.path.join(workspace, "gradlew"))
            else "gradle"
        )
        result = self._run_command([gradle_cmd, "test"], workspace, timeout=300)
        return TestResult(
            passed=result.returncode == 0,
            output=result.stdout + result.stderr,
            error="" if result.returncode == 0 else "Gradle tests failed",
        )

    async def _run_rust(self, workspace: str) -> TestResult:
        """Run Rust project tests."""
        output_parts = []

        result = self._run_command(["cargo", "build"], workspace, timeout=300)
        output_parts.append("=== cargo build ===\n" + result.stdout + result.stderr)
        if result.returncode != 0:
            return TestResult(
                passed=False, output="\n".join(output_parts), error="Build failed"
            )

        result = self._run_command(["cargo", "test"], workspace, timeout=300)
        output_parts.append("=== cargo test ===\n" + result.stdout + result.stderr)

        return TestResult(
            passed=result.returncode == 0,
            output="\n".join(output_parts),
            error="" if result.returncode == 0 else "Tests failed",
        )

    async def _run_generic(self, workspace: str) -> TestResult:
        """Generic test runner using Makefile if available."""
        if os.path.exists(os.path.join(workspace, "Makefile")):
            result = self._run_command(["make", "test"], workspace, check=False)
            return TestResult(
                passed=result.returncode == 0, output=result.stdout + result.stderr
            )
        return TestResult(
            passed=True, output="No test runner detected - skipping tests"
        )

    def _run_command(
        self,
        cmd: list,
        cwd: str,
        timeout: Optional[int] = None,
        env: Optional[dict] = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess:
        """Run a shell command with timeout."""
        try:
            return subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
                env=env,
                check=check,
            )
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(
                cmd, 1, stdout="", stderr=f"Command timed out after {timeout}s"
            )
        except FileNotFoundError:
            return subprocess.CompletedProcess(
                cmd, 127, stdout="", stderr=f"Command not found: {cmd[0]}"
            )

    def _parse_jest_output(self, output: str) -> tuple[int, int]:
        """Parse Jest test output for counts."""
        import re

        total_match = re.search(r"Tests:\s+.*?(\d+)\s+total", output)
        failed_match = re.search(r"(\d+)\s+failed", output)
        total = int(total_match.group(1)) if total_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0
        return total, failed

    def _parse_pytest_output(self, output: str) -> tuple[int, int]:
        """Parse pytest output for counts."""
        import re

        match = re.search(r"(\d+) passed(?:, (\d+) failed)?", output)
        if match:
            total = int(match.group(1))
            failed = int(match.group(2)) if match.group(2) else 0
            return total + failed, failed
        return 0, 0
