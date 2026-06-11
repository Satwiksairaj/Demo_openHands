"""
ImpactAnalyzer
Location: agent/impact_analyzer.py

Builds a dependency graph of the codebase and determines, for any given
feature prompt, which files should be:
  - MODIFY  → already exist and need to change
  - CREATE  → new files that should be created
  - SKIP    → unrelated, leave untouched

Combined with RAG results from RepoIndexer for best accuracy.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass
class ImpactReport:
    modify: list[str] = field(default_factory=list)
    create: list[str] = field(default_factory=list)
    skip: list[str] = field(default_factory=list)
    reasoning: dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        lines = []
        if self.modify:
            lines.append(
                f"MODIFY ({len(self.modify)}):\n"
                + "\n".join(
                    f"  - {f}  [{self.reasoning.get(f, '')}]" for f in self.modify
                )
            )
        if self.create:
            lines.append(
                f"CREATE ({len(self.create)}):\n"
                + "\n".join(f"  - {f}" for f in self.create)
            )
        if self.skip:
            lines.append(f"SKIP: {len(self.skip)} file(s) left untouched")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Skip / code rules (mirrors repo_indexer)
# ---------------------------------------------------------------------------

_SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".next",
    ".agent_index",
    "migrations",
    "instance",
    ".agent",
    "coverage",
    ".pytest_cache",
}
_CODE_EXT = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".rb", ".rs"}


# ---------------------------------------------------------------------------
# Dependency graph
# ---------------------------------------------------------------------------


class _DepGraph:
    def __init__(self):
        self._imports: dict[str, set[str]] = {}  # file → files it imports
        self._imported_by: dict[str, set[str]] = {}  # file → files that import it

    def add_edge(self, src: str, dst: str):
        self._imports.setdefault(src, set()).add(dst)
        self._imported_by.setdefault(dst, set()).add(src)

    def dependents(self, fp: str, depth: int = 2) -> set[str]:
        """Files that (transitively) import fp."""
        visited: set[str] = set()
        frontier: set[str] = {fp}
        for _ in range(depth):
            nxt: set[str] = set()
            for f in frontier:
                nxt.update(self._imported_by.get(f, set()) - visited)
            visited.update(nxt)
            frontier = nxt
        return visited


def _py_imports(content: str) -> list[str]:
    out = []
    try:
        for node in ast.walk(ast.parse(content)):
            if isinstance(node, ast.Import):
                for a in node.names:
                    out.append(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                out.append(node.module.split(".")[0])
    except SyntaxError:
        pass
    return out


def _js_imports(content: str) -> list[str]:
    pat = re.compile(
        r"""(?:import|require)\s*(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)?\s*(?:from\s*)?['"]([^'"]+)['"]""",
        re.M,
    )
    return [m.group(1) for m in pat.finditer(content) if m.group(1).startswith(".")]


# ---------------------------------------------------------------------------
# Feature heuristics
# ---------------------------------------------------------------------------

# (trigger words, file name patterns, reason label)
_PATTERNS: list[tuple[list[str], list[str], str]] = [
    (
        [
            "auth",
            "login",
            "jwt",
            "token",
            "oauth",
            "session",
            "password",
            "logout",
            "signup",
            "register",
        ],
        ["auth", "user", "login", "account", "middleware", "decorator", "security"],
        "authentication",
    ),
    (
        ["model", "database", "db", "schema", "migration", "orm", "table", "field"],
        ["model", "schema", "migration", "db", "database", "entity"],
        "data model",
    ),
    (
        ["route", "endpoint", "api", "view", "controller", "url"],
        ["route", "view", "controller", "endpoint", "api", "url", "handler"],
        "routing/API",
    ),
    (
        ["test", "spec", "coverage", "pytest", "unittest", "jest"],
        ["test", "spec", "conftest"],
        "test files",
    ),
    (
        ["dashboard", "ui", "frontend", "template", "html", "page", "component"],
        ["template", "view", "html", "dashboard", "page", "component", "layout"],
        "UI/template",
    ),
    (
        ["notification", "email", "webhook", "event", "signal", "alert"],
        ["notification", "email", "webhook", "event", "signal", "mailer"],
        "notifications",
    ),
    (
        ["config", "setting", "environment", "env", "configuration"],
        ["config", "setting", "env", "configuration", "constants"],
        "configuration",
    ),
    (
        ["celery", "task", "queue", "worker", "async", "background", "job"],
        ["task", "celery", "worker", "queue", "job", "beat"],
        "async tasks",
    ),
    (
        ["search", "filter", "query", "elasticsearch", "index"],
        ["search", "filter", "query", "index"],
        "search",
    ),
    (
        ["payment", "stripe", "billing", "invoice", "subscription"],
        ["payment", "billing", "stripe", "invoice", "subscription"],
        "payments",
    ),
    (
        ["upload", "file", "storage", "s3", "media", "image"],
        ["upload", "storage", "media", "file", "s3"],
        "file storage",
    ),
    (
        ["rbac", "role", "permission", "access", "acl", "policy"],
        ["role", "permission", "access", "policy", "acl", "rbac"],
        "RBAC/permissions",
    ),
    (["cache", "redis", "memcache", "caching"], ["cache", "redis"], "caching"),
    (
        ["log", "logging", "monitor", "trace", "sentry"],
        ["log", "logging", "monitor"],
        "logging",
    ),
]


def _kw(prompt: str) -> set[str]:
    return set(re.findall(r"\b\w+\b", prompt.lower()))


def _name_matches(fp: str, patterns: list[str]) -> bool:
    stem = Path(fp).stem.lower()
    return any(p in stem for p in patterns)


# ---------------------------------------------------------------------------
# ImpactAnalyzer
# ---------------------------------------------------------------------------


class ImpactAnalyzer:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self._graph = _DepGraph()
        self._files: list[str] = []
        self._ready = False

    def build_graph(self) -> None:
        self._files = []
        for p in self.repo_path.rglob("*"):
            if not p.is_file():
                continue
            if any(part in _SKIP_DIRS for part in p.parts):
                continue
            if p.suffix not in _CODE_EXT:
                continue
            rel = str(p.relative_to(self.repo_path))
            self._files.append(rel)

            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            if p.suffix == ".py":
                for imp in _py_imports(content):
                    for cand in self._files:
                        if Path(cand).stem == imp or cand.endswith(f"/{imp}.py"):
                            self._graph.add_edge(rel, cand)
            elif p.suffix in (".js", ".ts", ".jsx", ".tsx"):
                for imp in _js_imports(content):
                    candidate = (
                        str(
                            (p.parent / imp)
                            .resolve()
                            .relative_to(self.repo_path.resolve())
                        )
                        if (p.parent / imp).exists()
                        else imp
                    )
                    self._graph.add_edge(rel, candidate)

        self._ready = True

    def analyze(
        self,
        prompt: str,
        rag_results: Optional[list[dict]] = None,
    ) -> ImpactReport:
        if not self._ready:
            self.build_graph()

        report = ImpactReport(skip=list(self._files))
        words = _kw(prompt)
        to_modify: set[str] = set()

        # 1. RAG hits
        if rag_results:
            for r in rag_results:
                fp = r.get("file_path", "")
                if fp in self._files:
                    to_modify.add(fp)
                    report.reasoning[fp] = "semantic search match"

        # 2. Keyword heuristics
        for triggers, name_pats, reason in _PATTERNS:
            if any(t in words for t in triggers):
                for fp in self._files:
                    if _name_matches(fp, name_pats):
                        to_modify.add(fp)
                        report.reasoning.setdefault(fp, reason)

        # 3. Dependency expansion
        extra: set[str] = set()
        for fp in list(to_modify):
            for dep in self._graph.dependents(fp, depth=1):
                if dep in self._files:
                    extra.add(dep)
                    report.reasoning.setdefault(dep, f"imports {fp}")
        to_modify.update(extra)

        report.modify = sorted(to_modify)
        report.create = self._suggest_new(prompt, to_modify)
        report.skip = sorted(set(self._files) - to_modify)
        return report

    def _suggest_new(self, prompt: str, existing: set[str]) -> list[str]:
        low = prompt.lower()
        sugg = []
        if "test" in low and not any("test" in f for f in existing):
            sugg.append("tests/test_new_feature.py")
        if any(w in low for w in ["service", "services"]) and not any(
            "service" in f for f in existing
        ):
            sugg.append("app/services/new_service.py")
        if "migration" in low:
            sugg.append("migrations/add_feature.py")
        if any(w in low for w in ["template", "html", "page"]) and not any(
            "template" in f for f in existing
        ):
            sugg.append("app/templates/new_feature.html")
        return sugg
