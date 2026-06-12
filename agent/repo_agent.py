"""
Repository Agent - Clones repositories and analyzes their structure,
frameworks, conventions, and relevant files.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

REPO_ANALYSIS_PROMPT = """You are an expert software architect analyzing a codebase.

Repository structure:
{tree}

Key files content:
{file_contents}

Development task requirements:
{requirements}

Analyze this codebase and return a JSON object:
{{
  "framework": "<detected framework, e.g. Express, Django, Spring Boot>",
  "language": "<primary language>",
  "architecture": "<mvc|layered|microservice|monolith|etc>",
  "package_manager": "<npm|pip|maven|cargo|etc>",
  "test_framework": "<jest|pytest|junit|etc>",
  "entry_points": ["<main files>"],
  "relevant_files": ["<files that need modification>"],
  "new_files_needed": ["<files that need to be created>"],
  "coding_style": {{
    "indentation": "<2 spaces|4 spaces|tabs>",
    "quotes": "<single|double>",
    "semicolons": "<yes|no>",
    "naming_convention": "<camelCase|snake_case|PascalCase>"
  }},
  "existing_patterns": ["<pattern 1>", "<pattern 2>"],
  "dependencies_to_add": ["<package@version>"],
  "implementation_notes": ["<important note 1>", "<note 2>"]
}}"""


class RepositoryAgent:
    """
    Handles repository cloning, branch creation, and deep
    structural analysis of the codebase.
    """

    def __init__(self, config: dict):
        self.config = config
        self.github_config = config.get("github", {})
        self.client = AsyncOpenAI(api_key=config.get("openai_api_key"))
        self.workspace_base = config.get(
            "workspace_base", str(Path.home() / "agent-workspaces")
        )
        os.makedirs(self.workspace_base, exist_ok=True)

    async def clone_and_branch(self, repo_url: str, branch_name: str) -> str:
        """Clone the repository and create a feature branch."""
        # Inject GitHub token into URL
        token = self.github_config.get("token", "")
        if token and "github.com" in repo_url:
            repo_url = repo_url.replace(
                "https://github.com", f"https://{token}@github.com"
            )

        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        # Use forward slashes — git clone requires POSIX-style paths on Windows too
        workspace = Path(self.workspace_base) / repo_name

        if (workspace / ".git").exists():
            logger.info("Reusing existing workspace: %s", workspace)
            workspace_str = workspace.as_posix()
            self._reuse_existing_workspace(workspace_str, repo_url, branch_name)
            return workspace_str

        # Remove existing workspace; if locked, fall back to a unique workspace path.
        if workspace.exists():
            def _force_remove(func, path, _):
                """Error handler that clears read-only flag, then retries."""
                try:
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                except OSError:
                    # Let outer handler decide fallback for locked files.
                    raise

            try:
                shutil.rmtree(workspace, onerror=_force_remove)
            except OSError as exc:
                logger.warning(
                    "Could not clean workspace '%s' (%s). Falling back to unique workspace.",
                    workspace,
                    exc,
                )
                workspace = self._build_unique_workspace(repo_name)

        workspace_str = workspace.as_posix()

        Path(self.workspace_base).mkdir(parents=True, exist_ok=True)

        logger.info("Cloning repository...")
        self._run(["git", "clone", repo_url, workspace_str])

        logger.info(f"Creating branch: {branch_name}")
        self._run(["git", "checkout", "-b", branch_name], cwd=workspace_str)

        # Configure git identity for commits
        self._run(
            ["git", "config", "user.email", "ai-agent@autonomous.dev"],
            cwd=workspace_str,
        )
        self._run(["git", "config", "user.name", "AI Dev Agent"], cwd=workspace_str)

        return workspace_str

    def _reuse_existing_workspace(
        self, workspace: str, repo_url: str, branch_name: str
    ) -> None:
        """Prepare an existing cloned repository for a new run without creating a new folder."""
        self._run(["git", "remote", "set-url", "origin", repo_url], cwd=workspace)
        self._run(["git", "fetch", "origin"], cwd=workspace, check=False)
        self._run(["git", "checkout", "-B", branch_name], cwd=workspace)
        self._run(
            ["git", "config", "user.email", "ai-agent@autonomous.dev"],
            cwd=workspace,
        )
        self._run(["git", "config", "user.name", "AI Dev Agent"], cwd=workspace)

    def _build_unique_workspace(self, repo_name: str) -> Path:
        """Create a unique workspace path to avoid collisions with locked directories."""
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        candidate = Path(self.workspace_base) / f"{repo_name}_{stamp}"
        suffix = 1
        while candidate.exists():
            candidate = Path(self.workspace_base) / f"{repo_name}_{stamp}_{suffix}"
            suffix += 1
        return candidate

    async def analyze(self, workspace: str, story_data: dict) -> dict:
        """Perform deep analysis of the repository structure."""
        tree = self._get_tree(workspace, max_depth=2)  # shallow — big repos
        key_files = self._read_key_files(workspace)

        # Keep total prompt size manageable
        tree_snippet = tree[:4000]
        files_snippet = key_files[:6000]
        reqs_snippet = json.dumps(story_data, indent=2)[:2000]

        user_message = REPO_ANALYSIS_PROMPT.format(
            tree=tree_snippet,
            file_contents=files_snippet,
            requirements=reqs_snippet,
        )
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": user_message}],
            temperature=0,
        )

        raw_content = response.choices[0].message.content
        content = (raw_content or "").strip()
        content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("`")

        try:
            analysis = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            logger.warning(
                "Repo analysis: LLM returned non-JSON, using static fallback"
            )
            analysis = self._static_analysis(workspace)

        # Augment with static analysis
        analysis["workspace"] = workspace
        analysis["detected_configs"] = self._detect_config_files(workspace)
        analysis["has_docker"] = os.path.exists(os.path.join(workspace, "Dockerfile"))
        analysis["has_ci"] = self._detect_ci(workspace)
        analysis.update(self._repository_understanding(workspace))

        return analysis

    def _repository_understanding(self, workspace: str) -> dict:
        """Repository understanding output used by design/planning phases."""
        ws = Path(workspace)

        def relpaths(patterns: tuple[str, ...]) -> list[str]:
            out: list[str] = []
            for p in ws.rglob("*"):
                if not p.is_file():
                    continue
                low = p.name.lower()
                if any(tok in low for tok in patterns):
                    out.append(str(p.relative_to(ws)).replace("\\", "/"))
            return sorted(set(out))

        entry_points = []
        for name in ["app.py", "main.py", "server.py", "src/main.py", "src/index.js", "index.js"]:
            p = ws / name
            if p.exists():
                entry_points.append(name)

        return {
            "models": relpaths(("model", "entity", "schema")),
            "routes": relpaths(("route", "controller", "endpoint", "api")),
            "services": relpaths(("service", "usecase")),
            "repositories": relpaths(("repo", "repository")),
            "tests": relpaths(("test", "spec", "conftest")),
            "middleware": relpaths(("middleware", "interceptor", "guard")),
            "database_layer": relpaths(("db", "database", "migration")),
            "entry_points": sorted(set(entry_points)),
            "folder_structure": self._get_tree(workspace, max_depth=3),
        }

    def _static_analysis(self, workspace: str) -> dict:
        """Fallback: derive key repo facts without an LLM call."""
        ws = Path(workspace)
        language = "unknown"
        framework = "unknown"
        pkg_manager = "unknown"
        test_framework = "unknown"

        if (ws / "package.json").exists():
            language, pkg_manager = "javascript", "npm"
            framework = "express" if any(ws.rglob("express")) else "node.js"
            test_framework = "jest"
        elif (ws / "pyproject.toml").exists() or (ws / "requirements.txt").exists():
            language, pkg_manager = "python", "pip"
            framework = "fastapi" if any(ws.rglob("fastapi")) else "python"
            test_framework = "pytest"
        elif (ws / "go.mod").exists():
            language, pkg_manager = "go", "go modules"
            test_framework = "go test"
        elif (ws / "Cargo.toml").exists():
            language, pkg_manager = "rust", "cargo"
            test_framework = "cargo test"
        elif (ws / "pom.xml").exists():
            language, pkg_manager = "java", "maven"
            test_framework = "junit"

        return {
            "framework": framework,
            "language": language,
            "architecture": "unknown",
            "package_manager": pkg_manager,
            "test_framework": test_framework,
            "entry_points": [],
            "relevant_files": [],
            "new_files_needed": [],
            "coding_style": {},
            "existing_patterns": [],
            "dependencies_to_add": [],
            "implementation_notes": [],
        }

    def _get_tree(self, workspace: str, max_depth: int = 4) -> str:
        """Get directory tree, excluding noise directories."""
        exclude = {
            "node_modules",
            ".git",
            "__pycache__",
            ".pytest_cache",
            "dist",
            "build",
            ".next",
            "venv",
            ".venv",
            "coverage",
        }
        lines = []
        workspace_path = Path(workspace)

        def walk(path: Path, prefix: str = "", depth: int = 0):
            if depth > max_depth:
                return
            try:
                entries = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
            except PermissionError:
                return
            for entry in entries:
                if entry.name in exclude or entry.name.startswith("."):
                    continue
                connector = "├── " if entry != entries[-1] else "└── "
                lines.append(f"{prefix}{connector}{entry.name}")
                if entry.is_dir():
                    extension = "│   " if entry != entries[-1] else "    "
                    walk(entry, prefix + extension, depth + 1)

        lines.append(workspace_path.name + "/")
        walk(workspace_path)
        return "\n".join(lines)

    def _read_key_files(self, workspace: str) -> str:
        """Read the most important files for understanding the project."""
        priority_files = [
            "package.json",
            "pyproject.toml",
            "requirements.txt",
            "setup.py",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "README.md",
            "README.rst",
            "src/app.js",
            "src/index.js",
            "app.js",
            "index.js",
            "src/main.py",
            "main.py",
            "app.py",
            "src/app.ts",
            "src/index.ts",
        ]

        contents = []
        for rel_path in priority_files:
            full_path = os.path.join(workspace, rel_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(3000)
                    contents.append(f"=== {rel_path} ===\n{content}\n")
                except Exception:
                    pass

        # Also read source files in common directories
        for src_dir in ["src", "lib", "app", "api"]:
            src_path = os.path.join(workspace, src_dir)
            if os.path.isdir(src_path):
                for root, _, files in os.walk(src_path):
                    for fname in files[:5]:
                        if fname.endswith((".js", ".ts", ".py", ".go", ".java", ".rs")):
                            fpath = os.path.join(root, fname)
                            try:
                                with open(
                                    fpath, "r", encoding="utf-8", errors="ignore"
                                ) as f:
                                    content = f.read(2000)
                                rel = os.path.relpath(fpath, workspace)
                                contents.append(f"=== {rel} ===\n{content}\n")
                            except Exception:
                                pass
                    break  # Only top level of src

        return "\n".join(contents)

    def _detect_config_files(self, workspace: str) -> list:
        """Detect configuration and build files."""
        configs = []
        for name in os.listdir(workspace):
            if name in {
                ".eslintrc",
                ".eslintrc.js",
                ".eslintrc.json",
                ".prettierrc",
                "tsconfig.json",
                ".babelrc",
                "jest.config.js",
                "jest.config.ts",
                "pytest.ini",
                "setup.cfg",
                "mypy.ini",
                "Makefile",
                "docker-compose.yml",
            }:
                configs.append(name)
        return configs

    def _detect_ci(self, workspace: str) -> bool:
        """Detect CI/CD configuration."""
        ci_paths = [
            ".github/workflows",
            ".gitlab-ci.yml",
            "Jenkinsfile",
            ".circleci/config.yml",
        ]
        return any(os.path.exists(os.path.join(workspace, p)) for p in ci_paths)
    
    def _run_git(self, cmd: list[str], cwd: Optional[str] = None):
        """Run a git command and return output."""
        result = subprocess.run(
            ["git"] + cmd, cwd=cwd, capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Git command failed: {' '.join(cmd)}\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}"
            )
        return result.stdout

    def _run(self, cmd: list[str], cwd: Optional[str] = None, check: bool = True) -> str:
        """Run a shell command and return output."""
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
        if result.returncode != 0 and check:
            raise RuntimeError(
                f"Command failed: {' '.join(cmd)}\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}"
            )
        return result.stdout
