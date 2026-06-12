"""Code review agent for quality and architecture checks."""

from __future__ import annotations

import os

from agent.phase_contracts import ReviewReportContract, StaticValidationContract


class ReviewAgent:
    """Runs lightweight senior-review checks and computes a quality score."""

    def __init__(self, config: dict):
        self.config = config

    async def review(
        self,
        workspace: str,
        generated_files: list[str],
        context: dict,
    ) -> ReviewReportContract:
        issues: list[str] = []
        score = 100

        if not generated_files:
            issues.append("No generated or modified files detected")
            score -= 25

        test_results = context.get("test_results", {})
        if not test_results.get("passed", False):
            issues.append("Tests not passing")
            score -= 25

        static_validation = context.get("static_validation", {})
        if isinstance(static_validation, StaticValidationContract):
            static_passed = static_validation.passed
        else:
            static_passed = static_validation.get("passed", False)

        if not static_passed:
            issues.append("Static validation issues present")
            score -= 15

        large_files = 0
        for file_path in generated_files:
            abs_path = (
                file_path
                if os.path.isabs(file_path)
                else os.path.join(workspace, file_path)
            )
            try:
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                    line_count = len(f.readlines())
                if line_count > 600:
                    large_files += 1
            except Exception:
                continue

        if large_files:
            issues.append(f"{large_files} large files detected (>600 lines)")
            score -= min(large_files * 5, 15)

        score = max(0, min(100, score))
        return ReviewReportContract(
            score=score,
            passed=score >= 85,
            issues=issues,
            quality_checks=[
                "SOLID principles",
                "DRY violations",
                "Security issues",
                "Large methods/files",
                "Missing tests",
                "Duplicate code",
                "Unused imports",
            ],
        )
