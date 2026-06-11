"""
RepoIndexer
Location: agent/repo_indexer.py

Indexes the active project's codebase into chunks, embeds them (OpenAI or
keyword fallback), and provides semantic search.  This is what lets the agent
"know" the codebase the way Copilot does — finding the right 5 files out of 200.

Index stored at:  workspace/<project_name>/.agent_index/
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import openai as _openai

    _OPENAI_OK = True
except ImportError:
    _OPENAI_OK = False

import os

# ---------------------------------------------------------------------------
# Chunk dataclass
# ---------------------------------------------------------------------------


@dataclass
class CodeChunk:
    file_path: str
    chunk_type: str  # function | class | route | model | module
    name: str
    content: str
    start_line: int
    end_line: int
    language: str
    embedding: Optional[list] = None

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "chunk_type": self.chunk_type,
            "name": self.name,
            "content": self.content,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "language": self.language,
            "embedding": self.embedding,
        }


# ---------------------------------------------------------------------------
# Language parsers
# ---------------------------------------------------------------------------


def _parse_python(file_path: str, content: str) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    lines = content.splitlines()
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            s, e = node.lineno - 1, getattr(node, "end_lineno", node.lineno)
            ctype = "function"
            for d in node.decorator_list:
                dname = ""
                if isinstance(d, ast.Name):
                    dname = d.id
                elif isinstance(d, ast.Attribute):
                    dname = d.attr
                elif isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute):
                    dname = d.func.attr
                if dname in ("route", "get", "post", "put", "delete", "patch"):
                    ctype = "route"
                    break
            chunks.append(
                CodeChunk(
                    file_path=file_path,
                    chunk_type=ctype,
                    name=node.name,
                    content="\n".join(lines[s:e]),
                    start_line=s + 1,
                    end_line=e,
                    language="python",
                )
            )

        elif isinstance(node, ast.ClassDef):
            s, e = node.lineno - 1, getattr(node, "end_lineno", node.lineno)
            ctype = (
                "model"
                if any(isinstance(b, ast.Name) and "Model" in b.id for b in node.bases)
                else "class"
            )
            chunks.append(
                CodeChunk(
                    file_path=file_path,
                    chunk_type=ctype,
                    name=node.name,
                    content="\n".join(lines[s:e]),
                    start_line=s + 1,
                    end_line=e,
                    language="python",
                )
            )

    return chunks


def _parse_js_ts(file_path: str, content: str, language: str) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    lines = content.splitlines()
    pats = [
        (
            re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(", re.M),
            "function",
        ),
        (
            re.compile(
                r"^(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s+)?\(", re.M
            ),
            "function",
        ),
        (re.compile(r"^(?:export\s+)?class\s+(\w+)", re.M), "class"),
    ]
    for pat, ctype in pats:
        for m in pat.finditer(content):
            sl = content[: m.start()].count("\n")
            el = min(sl + 50, len(lines))
            chunks.append(
                CodeChunk(
                    file_path=file_path,
                    chunk_type=ctype,
                    name=m.group(1),
                    content="\n".join(lines[sl:el]),
                    start_line=sl + 1,
                    end_line=el,
                    language=language,
                )
            )
    return chunks


def _parse_file(file_path: str, content: str) -> list[CodeChunk]:
    ext = Path(file_path).suffix.lower()
    if ext == ".py":
        return _parse_python(file_path, content)
    if ext in (".js", ".jsx"):
        return _parse_js_ts(file_path, content, "javascript")
    if ext in (".ts", ".tsx"):
        return _parse_js_ts(file_path, content, "typescript")
    # Whole-file chunk for other types
    return [
        CodeChunk(
            file_path=file_path,
            chunk_type="module",
            name=Path(file_path).stem,
            content=content[:3000],
            start_line=1,
            end_line=content.count("\n") + 1,
            language=ext.lstrip(".") or "text",
        )
    ]


# ---------------------------------------------------------------------------
# Simple JSON-backed vector store (zero external dependencies)
# ---------------------------------------------------------------------------


class _Store:
    def __init__(self, path: Path):
        self._path = path
        self._chunks: list[dict] = []
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            try:
                self._chunks = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                self._chunks = []

    def _save(self):
        self._path.write_text(
            json.dumps(self._chunks, ensure_ascii=False),
            encoding="utf-8",
        )

    def upsert(self, chunks: list[CodeChunk]):
        new_files = {c.file_path for c in chunks}
        self._chunks = [c for c in self._chunks if c["file_path"] not in new_files]
        self._chunks.extend(c.to_dict() for c in chunks)
        self._save()

    def remove_file(self, fp: str):
        self._chunks = [c for c in self._chunks if c["file_path"] != fp]
        self._save()

    # ── Keyword search (always available) ─────────────────────────
    def kw_search(self, query: str, k: int) -> list[dict]:
        words = set(re.findall(r"\w+", query.lower()))
        scored = []
        for c in self._chunks:
            text = (c["name"] + " " + c["chunk_type"] + " " + c["content"]).lower()
            score = sum(1 for w in words if w in text)
            if score:
                scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:k]]

    # ── Embedding cosine search ────────────────────────────────────
    def emb_search(self, query_emb: list, k: int) -> list[dict]:
        def dot(a, b):
            return sum(x * y for x, y in zip(a, b))

        def nm(v):
            return sum(x * x for x in v) ** 0.5

        scored = []
        for c in self._chunks:
            e = c.get("embedding")
            if e:
                sc = dot(query_emb, e) / (nm(query_emb) * nm(e) + 1e-9)
                scored.append((sc, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:k]]


# ---------------------------------------------------------------------------
# Skip rules
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
_SKIP_EXT = {
    ".pyc",
    ".lock",
    ".png",
    ".jpg",
    ".gif",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".min.js",
}
_MAX_BYTES = 80_000
_CODE_EXT = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".go",
    ".java",
    ".rb",
    ".rs",
    ".php",
    ".cs",
}


# ---------------------------------------------------------------------------
# RepoIndexer
# ---------------------------------------------------------------------------


class RepoIndexer:
    """
    Index a repository and provide semantic/keyword search over its code.

    Index lives at: <repo_path>/.agent_index/
    """

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        idx_dir = self.repo_path / ".agent_index"
        self._store = _Store(idx_dir / "chunks.json")
        self._hash_file = idx_dir / "hashes.json"
        self._hash_file.parent.mkdir(parents=True, exist_ok=True)
        self._hashes: dict[str, str] = {}
        if self._hash_file.exists():
            try:
                self._hashes = json.loads(self._hash_file.read_text())
            except Exception:
                self._hashes = {}

    # ------------------------------------------------------------------
    def _fhash(self, p: Path) -> str:
        return hashlib.md5(p.read_bytes()).hexdigest()

    def _should_index(self, p: Path) -> bool:
        if any(part in _SKIP_DIRS for part in p.parts):
            return False
        if p.suffix in _SKIP_EXT:
            return False
        if p.suffix not in _CODE_EXT and p.suffix not in {
            ".html",
            ".md",
            ".yaml",
            ".yml",
            ".toml",
            ".cfg",
            ".ini",
            ".env.example",
        }:
            return False
        try:
            return p.stat().st_size <= _MAX_BYTES
        except OSError:
            return False

    def _embed(self, texts: list[str]) -> list[Optional[list]]:
        if not _OPENAI_OK:
            return [None] * len(texts)
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return [None] * len(texts)
        try:
            client = _openai.OpenAI(api_key=api_key)
            resp = client.embeddings.create(
                model="text-embedding-3-small",
                input=[t[:8000] for t in texts],
            )
            return [item.embedding for item in resp.data]
        except Exception as exc:
            print(f"[index] Embedding failed ({exc}) — using keyword search")
            return [None] * len(texts)

    # ------------------------------------------------------------------
    def index_repo(self, incremental: bool = True) -> int:
        """
        Walk the repo and index changed files.
        Returns number of files newly indexed.
        """
        new_hashes: dict[str, str] = {}
        to_index: list[tuple[str, Path]] = []

        for p in self.repo_path.rglob("*"):
            if not p.is_file() or not self._should_index(p):
                continue
            rel = str(p.relative_to(self.repo_path))
            h = self._fhash(p)
            new_hashes[rel] = h
            if incremental and self._hashes.get(rel) == h:
                continue
            to_index.append((rel, p))

        # Remove deleted
        for old in set(self._hashes) - set(new_hashes):
            self._store.remove_file(old)

        if not to_index:
            print("[index] Up to date — no changes")
            return 0

        print(f"[index] Indexing {len(to_index)} file(s)…")
        all_chunks: list[CodeChunk] = []
        for rel, p in to_index:
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                all_chunks.extend(_parse_file(rel, content))
            except Exception as exc:
                print(f"[index] Skip {rel}: {exc}")

        # Embed in batches
        BATCH = 50
        for i in range(0, len(all_chunks), BATCH):
            batch = all_chunks[i : i + BATCH]
            texts = [f"{c.chunk_type} {c.name}\n{c.content}" for c in batch]
            embeddings = self._embed(texts)
            for chunk, emb in zip(batch, embeddings):
                chunk.embedding = emb

        self._store.upsert(all_chunks)
        self._hashes = new_hashes
        self._hash_file.write_text(json.dumps(new_hashes), encoding="utf-8")
        print(f"[index] Done — {len(all_chunks)} chunks stored")
        return len(to_index)

    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int = 8) -> list[dict]:
        """Semantic search with embedding fallback to keyword search."""
        embs = self._embed([query])
        if embs[0]:
            results = self._store.emb_search(embs[0], top_k)
            if results:
                return results
        return self._store.kw_search(query, top_k)

    def format_for_prompt(self, results: list[dict], max_chars: int = 6000) -> str:
        parts, total = [], 0
        for r in results:
            block = (
                f"### {r['chunk_type']}: {r['name']}  "
                f"({r['file_path']}:{r['start_line']})\n"
                f"{r['content']}"
            )
            if total + len(block) > max_chars:
                break
            parts.append(block)
            total += len(block)
        return "\n\n---\n\n".join(parts)
