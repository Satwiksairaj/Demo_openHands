"""
Learning System - Phase 11 of the 14-phase autonomous engineering workflow.

After every failure, stores:
  - Issue description
  - Root cause
  - Fix applied
  - Outcome (resolved/unresolved)

Future runs use this memory to avoid previously observed failures.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class LearningEntry:
    """A single recorded failure and its resolution."""

    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    error_type: str = ""
    issue: str = ""
    root_cause: str = ""
    fix_applied: str = ""
    outcome: str = "unresolved"  # "resolved" | "unresolved" | "partial"
    project: str = ""
    file_affected: str = ""
    occurrences: int = 1


class LearningSystem:
    """
    Phase 11 — Persistent failure memory store.

    Stores failures per run and across runs under workspace/.agent/learning.json.
    Provides hints to code generation to avoid known failure patterns.
    """

    def __init__(self, workspace_base: str):
        self.store_path = Path(workspace_base) / ".agent" / "learning.json"
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: list[LearningEntry] = self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> list[LearningEntry]:
        if not self.store_path.exists():
            return []
        try:
            raw = json.loads(self.store_path.read_text(encoding="utf-8"))
            return [LearningEntry(**e) for e in raw]
        except Exception:
            return []

    def _save(self) -> None:
        self.store_path.write_text(
            json.dumps([asdict(e) for e in self._entries], indent=2),
            encoding="utf-8",
        )

    # ── Write ─────────────────────────────────────────────────────────────────

    def record_failure(
        self,
        error_type: str,
        issue: str,
        root_cause: str,
        fix_applied: str = "",
        outcome: str = "unresolved",
        project: str = "",
        file_affected: str = "",
    ) -> LearningEntry:
        """Record a new failure event. Increments count if duplicate."""
        existing = self._find_similar(error_type, root_cause)
        if existing:
            existing.occurrences += 1
            existing.outcome = outcome
            if fix_applied:
                existing.fix_applied = fix_applied
            existing.timestamp = datetime.now(timezone.utc).isoformat()
            self._save()
            logger.debug(
                f"Learning: updated existing entry for {error_type} (×{existing.occurrences})"
            )
            return existing

        entry = LearningEntry(
            error_type=error_type,
            issue=issue,
            root_cause=root_cause,
            fix_applied=fix_applied,
            outcome=outcome,
            project=project,
            file_affected=file_affected,
        )
        self._entries.append(entry)
        self._save()
        logger.info(f"Learning: recorded new failure — {error_type}: {root_cause[:80]}")
        return entry

    def mark_resolved(self, error_type: str, root_cause: str, fix_applied: str) -> None:
        """Update an existing entry as resolved."""
        entry = self._find_similar(error_type, root_cause)
        if entry:
            entry.outcome = "resolved"
            entry.fix_applied = fix_applied
            entry.timestamp = datetime.now(timezone.utc).isoformat()
            self._save()
            logger.info(f"Learning: marked {error_type} as resolved")

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_hints_for_prompt(self, error_types: Optional[list[str]] = None) -> str:
        """
        Returns a formatted block of known failure patterns to inject into
        code generation/fix prompts so the agent avoids repeating mistakes.
        """
        if not self._entries:
            return ""

        relevant = self._entries
        if error_types:
            relevant = [e for e in self._entries if e.error_type in error_types]

        if not relevant:
            return ""

        lines = [
            "KNOWN FAILURE PATTERNS — avoid these mistakes:",
        ]
        seen: set[str] = set()
        for entry in sorted(relevant, key=lambda e: e.occurrences, reverse=True)[:10]:
            key = f"{entry.error_type}:{entry.root_cause[:60]}"
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"\n• Issue: {entry.issue}")
            lines.append(f"  Root Cause: {entry.root_cause}")
            if entry.fix_applied:
                lines.append(f"  Correct Fix: {entry.fix_applied}")
            if entry.file_affected:
                lines.append(f"  Affected: {entry.file_affected}")

        return "\n".join(lines)

    def get_repeated_failures(self, min_occurrences: int = 2) -> list[LearningEntry]:
        """Return failures seen more than N times — these are systemic issues."""
        return [e for e in self._entries if e.occurrences >= min_occurrences]

    def summary(self) -> dict:
        total = len(self._entries)
        resolved = sum(1 for e in self._entries if e.outcome == "resolved")
        repeated = len(self.get_repeated_failures())
        by_type: dict[str, int] = {}
        for e in self._entries:
            by_type[e.error_type] = by_type.get(e.error_type, 0) + 1
        return {
            "total_failures_recorded": total,
            "resolved": resolved,
            "unresolved": total - resolved,
            "repeated_patterns": repeated,
            "by_error_type": by_type,
        }

    # ── Private ───────────────────────────────────────────────────────────────

    def _find_similar(
        self, error_type: str, root_cause: str, similarity_chars: int = 60
    ) -> Optional[LearningEntry]:
        for entry in self._entries:
            if (
                entry.error_type == error_type
                and entry.root_cause[:similarity_chars] == root_cause[:similarity_chars]
            ):
                return entry
        return None

    def format_summary_report(self) -> str:
        s = self.summary()
        lines = [
            "── PHASE 11: LEARNING SYSTEM ────────────────────────────",
            f"  Total Recorded  : {s['total_failures_recorded']}",
            f"  Resolved        : {s['resolved']}",
            f"  Unresolved      : {s['unresolved']}",
            f"  Repeated Issues : {s['repeated_patterns']}",
        ]
        if s["by_error_type"]:
            lines.append("  By Error Type:")
            for etype, count in sorted(s["by_error_type"].items(), key=lambda x: -x[1]):
                lines.append(f"    {etype}: {count}")
        lines.append("─────────────────────────────────────────────────────────")
        return "\n".join(lines)
