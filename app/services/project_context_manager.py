"""
ProjectContextManager
Location: app/services/project_context_manager.py

Stores and retrieves the active project state so the agent behaves like a real
developer working on the SAME codebase across multiple prompts and Jira stories.

State is persisted to:
    workspace/agent/project_context.json   ← full context
    workspace/agent/.active_project.txt    ← quick name lookup
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths  (match your workspace/agent/ structure exactly)
# ---------------------------------------------------------------------------

WORKSPACE_AGENT_DIR = Path("workspace/agent")
CONTEXT_FILE = WORKSPACE_AGENT_DIR / "project_context.json"
ACTIVE_FILE = WORKSPACE_AGENT_DIR / ".active_project.txt"
PROJECTS_DIR = WORKSPACE_AGENT_DIR / "projects"
RUNS_DIR = WORKSPACE_AGENT_DIR / "runs"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ProjectContext:
    # Identity
    project_name: str
    path: str

    # Tech stack (filled by RepoAgent analysis)
    framework: str = ""
    language: str = ""
    database: str = ""
    auth_pattern: str = ""
    coding_style: str = ""
    architecture_notes: str = ""
    package_manager: str = ""
    test_framework: str = ""

    # Git / GitHub
    github_repo: str = ""
    last_branch: str = ""
    last_pr_url: str = ""
    base_branch: str = "development"

    # Memory
    dependencies: list = field(default_factory=list)
    decisions: list = field(default_factory=list)  # ["Used JWT not sessions", ...]
    rejected_approaches: list = field(default_factory=list)
    story_history: list = field(default_factory=list)  # [{summary, timestamp}, ...]
    key_files: list = field(default_factory=list)  # important files discovered

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class ProjectContextManager:
    """
    Single responsibility: persist + load ProjectContext across agent runs.

    Usage:
        mgr = ProjectContextManager()

        # First story — new project
        mgr.set_active_project("task_manager", "workspace/task_manager", framework="Flask")

        # Later stories — load and continue
        ctx = mgr.get_active_project()
        mgr.add_decision("Use JWT not sessions")
        mgr.add_story("Add JWT Authentication")
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir:
            self._ctx_file = Path(base_dir) / "project_context.json"
            self._active_file = Path(base_dir) / ".active_project.txt"
            self._projects_dir = Path(base_dir) / "projects"
            self._runs_dir = Path(base_dir) / "runs"
        else:
            self._ctx_file = CONTEXT_FILE
            self._active_file = ACTIVE_FILE
            self._projects_dir = PROJECTS_DIR
            self._runs_dir = RUNS_DIR

        # Ensure dirs exist
        for d in [self._ctx_file.parent, self._projects_dir, self._runs_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self._cache: Optional[ProjectContext] = None

    # ------------------------------------------------------------------
    # Core: load / save
    # ------------------------------------------------------------------

    def load_project_context(self) -> Optional[ProjectContext]:
        """Load context from disk.  Returns None if no project has been set."""
        if not self._ctx_file.exists():
            return None
        try:
            data = json.loads(self._ctx_file.read_text(encoding="utf-8"))
            self._cache = ProjectContext(**data)
            return self._cache
        except Exception as e:
            print(f"[context] Could not load context: {e}")
            return None

    def save_project_context(self, ctx: ProjectContext) -> None:
        """Persist context to disk."""
        ctx.updated_at = datetime.utcnow().isoformat()
        self._cache = ctx
        self._ctx_file.write_text(
            json.dumps(asdict(ctx), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        # Also write the quick-lookup file
        self._active_file.write_text(ctx.project_name, encoding="utf-8")

        # Write per-project snapshot in projects/
        snap = self._projects_dir / f"{ctx.project_name}.json"
        snap.write_text(
            json.dumps(asdict(ctx), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_active_project(self) -> Optional[ProjectContext]:
        """Return the cached context, or load from disk."""
        if self._cache:
            return self._cache
        return self.load_project_context()

    def has_active_project(self) -> bool:
        return self.get_active_project() is not None

    def set_active_project(
        self,
        project_name: str,
        path: str,
        framework: str = "",
        language: str = "",
        github_repo: str = "",
        base_branch: str = "development",
    ) -> ProjectContext:
        """Create (or reset) the active project context."""
        ctx = ProjectContext(
            project_name=project_name,
            path=path,
            framework=framework,
            language=language,
            github_repo=github_repo,
            base_branch=base_branch,
        )
        self.save_project_context(ctx)
        print(f"[context] Active project set: {project_name}")
        return ctx

    def update_from_analysis(self, analysis_dict: dict) -> None:
        """Merge RepoAgent analysis results into the stored context."""
        ctx = self.get_active_project()
        if not ctx:
            return
        updatable = {
            "framework",
            "language",
            "database",
            "auth_pattern",
            "coding_style",
            "architecture_notes",
            "package_manager",
            "test_framework",
            "key_files",
        }
        for k, v in analysis_dict.items():
            if k in updatable and v:
                setattr(ctx, k, v)
        self.save_project_context(ctx)

    def update_branch(self, branch: str) -> None:
        ctx = self.get_active_project()
        if ctx:
            ctx.last_branch = branch
            self.save_project_context(ctx)

    def update_pr(self, pr_url: str) -> None:
        ctx = self.get_active_project()
        if ctx:
            ctx.last_pr_url = pr_url
            self.save_project_context(ctx)

    def add_decision(self, decision: str) -> None:
        """Record an architectural decision for future stories."""
        ctx = self.get_active_project()
        if ctx and decision not in ctx.decisions:
            ctx.decisions.append(decision)
            self.save_project_context(ctx)

    def add_story(self, summary: str) -> None:
        """Record a completed story in the history."""
        ctx = self.get_active_project()
        if ctx:
            ctx.story_history.append(
                {
                    "summary": summary,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            self.save_project_context(ctx)

    def add_rejected_approach(self, approach: str) -> None:
        ctx = self.get_active_project()
        if ctx and approach not in ctx.rejected_approaches:
            ctx.rejected_approaches.append(approach)
            self.save_project_context(ctx)

    def clear_context(self) -> None:
        """Remove the active project context."""
        self._cache = None
        for f in [self._ctx_file, self._active_file]:
            if f.exists():
                f.unlink()
        print("[context] Active project context cleared.")

    # ------------------------------------------------------------------
    # Helpers for prompt injection
    # ------------------------------------------------------------------

    def get_memory_summary(self) -> str:
        """Return a compact memory block to inject into LLM prompts."""
        ctx = self.get_active_project()
        if not ctx:
            return ""
        parts = [
            f"Project: {ctx.project_name}",
            f"Path:    {ctx.path}",
            f"Stack:   {ctx.framework} / {ctx.language} / {ctx.database or 'no DB'}",
        ]
        if ctx.auth_pattern:
            parts.append(f"Auth:    {ctx.auth_pattern}")
        if ctx.coding_style:
            parts.append(f"Style:   {ctx.coding_style}")
        if ctx.decisions:
            parts.append("Decisions:")
            for d in ctx.decisions[-5:]:
                parts.append(f"  - {d}")
        if ctx.rejected_approaches:
            parts.append("Rejected:")
            for r in ctx.rejected_approaches[-3:]:
                parts.append(f"  - {r}")
        if ctx.story_history:
            recent = [s["summary"] for s in ctx.story_history[-3:]]
            parts.append("Recent stories: " + " → ".join(recent))
        return "\n".join(parts)

    def get_active_project_name(self) -> Optional[str]:
        """Fast lookup from .active_project.txt."""
        if self._active_file.exists():
            return self._active_file.read_text(encoding="utf-8").strip()
        return None

    # ------------------------------------------------------------------
    # Run logging  (writes to workspace/agent/runs/)
    # ------------------------------------------------------------------

    def log_run(
        self, prompt: str, status: str, files: list[str], pr_url: str = ""
    ) -> None:
        """Save a summary of each agent run."""
        run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        ctx = self.get_active_project()
        record = {
            "run_id": run_id,
            "project": ctx.project_name if ctx else "unknown",
            "prompt": prompt,
            "status": status,
            "files": files,
            "pr_url": pr_url,
            "timestamp": datetime.utcnow().isoformat(),
        }
        run_file = self._runs_dir / f"run_{run_id}.json"
        run_file.write_text(json.dumps(record, indent=2), encoding="utf-8")

    def list_runs(self, limit: int = 10) -> list[dict]:
        """Return recent run records, newest first."""
        runs = sorted(self._runs_dir.glob("run_*.json"), reverse=True)[:limit]
        result = []
        for f in runs:
            try:
                result.append(json.loads(f.read_text()))
            except Exception:
                pass
        return result

    # ------------------------------------------------------------------
    # Project registry (workspace/agent/projects/)
    # ------------------------------------------------------------------

    def list_projects(self) -> list[dict]:
        """Return all known projects from the projects/ directory."""
        projects = []
        for f in sorted(self._projects_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                projects.append(
                    {
                        "name": data.get("project_name", f.stem),
                        "framework": data.get("framework", ""),
                        "language": data.get("language", ""),
                        "path": data.get("path", ""),
                        "stories": len(data.get("story_history", [])),
                        "updated": data.get("updated_at", ""),
                    }
                )
            except Exception:
                pass
        return projects

    def switch_project(self, project_name: str) -> Optional[ProjectContext]:
        """Switch active project to a previously created one."""
        snap = self._projects_dir / f"{project_name}.json"
        if not snap.exists():
            print(f"[context] Project '{project_name}' not found in registry.")
            return None
        try:
            data = json.loads(snap.read_text())
            ctx = ProjectContext(**data)
            self.save_project_context(ctx)
            print(f"[context] Switched to: {project_name}")
            return ctx
        except Exception as e:
            print(f"[context] Failed to switch: {e}")
            return None
