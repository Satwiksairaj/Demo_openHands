"""
Error Analysis Agent - Classifies failures, extracts root causes,
detects infinite loops, and generates targeted healing strategies.
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Maps error patterns → error category
ERROR_PATTERNS = [
    (r"SyntaxError", "SyntaxError"),
    (r"IndentationError", "IndentationError"),
    (r"TabError", "IndentationError"),
    (r"ModuleNotFoundError|No module named", "ModuleNotFoundError"),
    (r"ImportError", "ImportError"),
    (r"AssertionError", "AssertionError"),
    (r"RuntimeError", "RuntimeError"),
    (r"TypeError", "TypeError"),
    (r"ValueError", "ValueError"),
    (r"AttributeError", "AttributeError"),
    (r"KeyError", "KeyError"),
    (r"FileNotFoundError", "FileNotFoundError"),
    (r"PermissionError", "PermissionError"),
    (r"ConnectionError|ConnectionRefusedError|TimeoutError", "NetworkError"),
    (r"subprocess\.CalledProcessError|exit code [1-9]", "ExecutionError"),
    (r"collected 0 items", "NoTestsFound"),
    (r"ERROR collecting", "CollectionError"),
]

FIX_STRATEGIES = {
    "SyntaxError": "Rewrite the entire file from scratch with correct syntax. Never patch syntax errors line-by-line.",
    "IndentationError": "Rewrite the entire file using exactly 4 spaces per indent level. No tabs.",
    "ModuleNotFoundError": "Install the missing package with: pip install -q <package>. Check if it's a local module path issue.",
    "ImportError": "Install missing dependency or fix the import path. Check __init__.py files.",
    "AssertionError": "Fix the implementation logic to match what the test expects. Do not modify tests unless requirement is wrong.",
    "RuntimeError": "Add null checks and error handling. Trace the full stack to find the root source.",
    "TypeError": "Check function signatures and argument types. Verify return types match expectations.",
    "ValueError": "Validate inputs before processing. Check data format and range.",
    "AttributeError": "Verify the object has the expected attribute. Check for None references.",
    "KeyError": "Check dictionary keys exist before access. Use .get() with defaults.",
    "FileNotFoundError": "Verify the file path is correct relative to the working directory.",
    "NetworkError": "Check connectivity and service availability. Add retry logic with backoff.",
    "ExecutionError": "Check the command exists and has correct arguments. Verify working directory.",
    "NoTestsFound": "Ensure test files are named test_*.py or *_test.py and functions start with test_.",
    "CollectionError": "Fix the syntax/import error in the test file so pytest can import it.",
}


@dataclass
class ErrorReport:
    """Structured result of error analysis."""

    type: str
    root_cause: str
    affected_files: list[str] = field(default_factory=list)
    affected_lines: list[str] = field(default_factory=list)
    fix_strategy: str = ""
    is_repeated: bool = False
    occurrence_count: int = 1
    raw_output: str = ""


class ErrorAnalysisAgent:
    """
    Analyzes test/build failures, classifies them, detects repeated loops,
    and provides targeted fix strategies for the autonomous healing loop.
    """

    def __init__(self, max_identical_failures: int = 2):
        self.max_identical_failures = max_identical_failures
        # Maps failure_hash → count to detect loops
        self._failure_counts: dict[str, int] = {}

    def analyze(self, test_output: str, error_message: str = "") -> ErrorReport:
        """
        Classify the error, extract affected files/lines, detect loops,
        and recommend a fix strategy.
        """
        combined = (test_output + "\n" + error_message).strip()

        error_type = self._classify(combined)
        affected_files = self._extract_files(combined)
        affected_lines = self._extract_lines(combined)
        root_cause = self._extract_root_cause(combined, error_type)
        fix_strategy = FIX_STRATEGIES.get(
            error_type, "Analyze the full output and fix the root cause."
        )

        failure_hash = self._hash_failure(error_type, affected_files, root_cause)
        self._failure_counts[failure_hash] = (
            self._failure_counts.get(failure_hash, 0) + 1
        )
        count = self._failure_counts[failure_hash]
        is_repeated = count > self.max_identical_failures

        if is_repeated:
            logger.warning(
                f"⚠️  Identical failure detected {count} times "
                f"(type={error_type}, files={affected_files}). "
                "Loop protection triggered."
            )

        return ErrorReport(
            type=error_type,
            root_cause=root_cause,
            affected_files=affected_files,
            affected_lines=affected_lines,
            fix_strategy=fix_strategy,
            is_repeated=is_repeated,
            occurrence_count=count,
            raw_output=combined[:2000],
        )

    def is_loop_detected(self, test_output: str, error_message: str = "") -> bool:
        """Quick check — returns True if this exact failure has happened too many times."""
        combined = (test_output + "\n" + error_message).strip()
        error_type = self._classify(combined)
        affected_files = self._extract_files(combined)
        root_cause = self._extract_root_cause(combined, error_type)
        failure_hash = self._hash_failure(error_type, affected_files, root_cause)
        count = self._failure_counts.get(failure_hash, 0)
        return count >= self.max_identical_failures

    def reset(self) -> None:
        """Reset failure tracking — call between workflow runs."""
        self._failure_counts.clear()

    def format_report(self, report: ErrorReport) -> str:
        """Format an ErrorReport as a human-readable string for logging."""
        lines = [
            f"Error Type    : {report.type}",
            f"Root Cause    : {report.root_cause}",
            f"Affected Files: {', '.join(report.affected_files) or 'unknown'}",
            f"Fix Strategy  : {report.fix_strategy}",
            f"Occurrences   : {report.occurrence_count}",
        ]
        if report.is_repeated:
            lines.append("⚠️  LOOP DETECTED — autonomous healing halted")
        return "\n".join(lines)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _classify(self, output: str) -> str:
        for pattern, category in ERROR_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                return category
        return "UnknownError"

    def _extract_files(self, output: str) -> list[str]:
        """Extract file paths mentioned in error output."""
        files: list[str] = []
        # Python traceback: File "path/to/file.py", line N
        for match in re.finditer(r'File ["\']([^"\']+\.py)["\']', output):
            path = match.group(1)
            # Skip stdlib/site-packages
            if "site-packages" not in path and "frozen" not in path:
                files.append(path)
        # Also catch bare paths like C:\...\file.py or /path/to/file.py
        for match in re.finditer(
            r"(?:^|\s)([A-Za-z]:\\[^\s:]+\.py|/[^\s:]+\.py)", output, re.MULTILINE
        ):
            path = match.group(1)
            if "site-packages" not in path:
                files.append(path)
        return list(dict.fromkeys(files))  # deduplicate, preserve order

    def _extract_lines(self, output: str) -> list[str]:
        """Extract specific error lines from output."""
        lines = []
        for match in re.finditer(r"^\s*(?:E\s+.+|>{3}.+)$", output, re.MULTILINE):
            line = match.group(0).strip()
            if len(line) > 5:
                lines.append(line)
        return lines[:10]

    def _extract_root_cause(self, output: str, error_type: str) -> str:
        """Extract the single most relevant error message line."""
        # Look for the last occurrence of the error type
        pattern = rf"{error_type}:?\s*(.+)"
        matches = re.findall(pattern, output, re.IGNORECASE)
        if matches:
            return matches[-1].strip()[:200]

        # Fallback: last non-empty line of the output
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if lines:
            return lines[-1][:200]

        return "See raw output"

    def _hash_failure(self, error_type: str, files: list[str], root_cause: str) -> str:
        """Stable hash for a failure signature — used to detect loops."""
        sig = f"{error_type}|{','.join(sorted(files))}|{root_cause[:100]}"
        return hashlib.md5(sig.encode()).hexdigest()
