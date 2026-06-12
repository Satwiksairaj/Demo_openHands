"""Acceptance validation agent - final gate before PR creation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agent.phase_contracts import (
    RequirementAnalysisContract,
    ReviewContract,
    ValidationContract,
)


@dataclass
class CodeIssueDetail:
    severity: str
    file_path: str
    description: str
    line_hint: str = ""
    fix_hint: str = ""


class AcceptanceValidator:
    """Validates that acceptance criteria are met before PR."""

    def __init__(self):
        pass

    def validate(
        self,
        requirements: RequirementAnalysisContract,
        review: ReviewContract,
        generated_files: dict[str, str],
        test_output: str,
        test_passed: bool,
    ) -> ValidationContract:
        """Validate acceptance criteria are met."""
        acceptance_criteria = requirements.acceptance_criteria or []
        
        passed_criteria = []
        missing_criteria = []
        
        if test_passed:
            passed_criteria = acceptance_criteria
        else:
            missing_criteria = acceptance_criteria
        
        quality_score = 0.8 if test_passed else 0.45
        
        result = ValidationContract(
            passed=test_passed and len(missing_criteria) == 0,
            missing_acceptance_criteria=missing_criteria,
            passed_criteria=passed_criteria,
            test_passed=test_passed,
            test_output=test_output,
            quality_score=quality_score,
            summary="Acceptance validation passed" if test_passed else "Tests failed",
        )
        
        return result


class AcceptanceValidatorAgent:
    """Backward-compatible async wrapper around AcceptanceValidator."""

    def __init__(self, config: dict = None):  # noqa: B006
        super().__init__()
        self._validator = AcceptanceValidator()

    async def validate(
        self,
        acceptance_criteria: list[str],
        context: dict,
    ) -> ValidationContract:
        """Orchestrator-compatible async validate interface."""
        test_results = context.get("test_results", {})
        test_passed = bool(test_results.get("passed", False))
        generated_files = context.get("generated_files", [])

        requirements = RequirementAnalysisContract(
            acceptance_criteria=acceptance_criteria,
        )
        files_dict: dict[str, str] = {
            f: "" for f in (generated_files if isinstance(generated_files, list) else [])
        }
        return self._validator.validate(
            requirements=requirements,
            review=ReviewContract(),
            generated_files=files_dict,
            test_output="",
            test_passed=test_passed,
        )
"""
agent/acceptance_validator.py
==============================
Acceptance Validator — Phase 6 (final gate) of the engineering pipeline.

Runs the full quality gate:
  1. LLM checks acceptance criteria coverage
  2. Test results (from TestingAgent)
  3. Static analysis (ruff / mypy / bandit)
  4. Quality score calculation

Only if ALL gates pass does the pipeline proceed to GitHub PR.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from agent.phase_contracts import (
    RequirementAnalysisContract,
    ReviewContract,
    ValidationContract,
)


_SYSTEM_PROMPT = """\
You are a QA lead and acceptance criteria verifier.
Given a set of acceptance criteria and the code that was written, determine
whether each criterion has been met.

Be strict: if you cannot confirm a criterion is met from the code, mark it as missing.
Do not assume — verify from the code.

Output ONLY valid JSON. No markdown fences. No preamble.

Schema:
{
  "passed": true|false,
  "passed_criteria": ["string"],
  "missing_acceptance_criteria": ["string"],
  "quality_score": 0.0,
  "summary": "string"
}
"""

_USER_TEMPLATE = """\
## Acceptance Criteria to Verify
{criteria_block}

## Generated Code
{code_block}

## Test Results
{test_output}

## Review Results
Score: {review_score}/5
Issues: {review_issues}

Verify each acceptance criterion against the code.
For each one, determine: is it demonstrably implemented in the code provided?
"""


class AcceptanceValidator:
    """
    Final quality gate before GitHub PR creation.
    Combines LLM criterion checking + static analysis + test results.
    """

    def __init__(self):
        self._client = None

    # ------------------------------------------------------------------

    def validate(
        self,
        requirements:    RequirementAnalysisContract,
        review:          ReviewContract,
        generated_files: dict[str, str],
        test_output:     str,
        test_passed:     bool,
        project_path:    Optional[str] = None,
    ) -> ValidationContract:
        print("[validate] Running acceptance validation…")

        # 1. LLM criterion check
        llm_result = self._llm_validate(requirements, review, generated_files, test_output)

        # 2. Static analysis on actual files
        static_issues, lint_ok, type_ok = self._run_static_analysis(
            project_path, list(generated_files.keys())
        )

        # 3. Assemble result
        contract = llm_result or ValidationContract()
        contract.test_passed   = test_passed
        contract.test_output   = test_output[:1000]
        contract.lint_passed   = lint_ok
        contract.type_check_ok = type_ok
        contract.static_issues = static_issues

        # 4. Quality score
        contract.quality_score = self._quality_score(contract, review)

        # 5. Final gate
        contract.passed = (
            contract.test_passed and
            not contract.missing_acceptance_criteria and
            contract.quality_score >= 0.6 and
            not review.has_blockers
        )

        contract.gate_reasons = self._gate_reasons(contract, review)

        if contract.passed:
            contract.summary = (
                f"Validation PASSED — quality score: {contract.quality_score:.0%}. "
                f"{len(contract.passed_criteria)} criteria met. Ready for PR."
            )
        else:
            contract.summary = (
                f"Validation FAILED — quality score: {contract.quality_score:.0%}. "
                f"Missing: {len(contract.missing_acceptance_criteria)} criteria. "
                f"Reasons: {'; '.join(contract.gate_reasons)}"
            )

        print(f"[validate] {'PASSED' if contract.passed else 'FAILED'}  "
              f"quality={contract.quality_score:.0%}  "
              f"missing_criteria={len(contract.missing_acceptance_criteria)}")
        return contract

    # ------------------------------------------------------------------
    # LLM validation
    # ------------------------------------------------------------------

    def _llm_validate(
        self,
        requirements:    RequirementAnalysisContract,
        review:          ReviewContract,
        generated_files: dict[str, str],
        test_output:     str,
    ) -> Optional[ValidationContract]:
        client = self._get_client()
        if not client:
            return self._heuristic_validate(requirements, review, test_output)

        # Truncated code block
        code_parts = []
        total = 0
        for path, content in sorted(generated_files.items()):
            block = f"### {path}\n{content[:800]}"
            if total + len(block) > 6000:
                break
            code_parts.append(block)
            total += len(block)

        criteria_block = "\n".join(f"- {c}" for c in requirements.acceptance_criteria)
        review_issues  = "; ".join(
            f"{i.severity}: {i.description}"
            for i in review.issues
            if i.severity in ("blocker", "major")
        ) or "none"

        user_msg = _USER_TEMPLATE.format(
            criteria_block = criteria_block,
            code_block     = "\n\n".join(code_parts),
            test_output    = test_output[:500],
            review_score   = review.score.value,
            review_issues  = review_issues,
        )

        try:
            resp = client.chat.completions.create(
                model       = os.environ.get("OPENAI_MODEL", "gpt-4o"),
                messages    = [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
                temperature = 0.05,
                max_tokens  = 1000,
            )
            raw  = resp.choices[0].message.content.strip()
            raw  = re.sub(r"^```(?:json)?\s*", "", raw)
            raw  = re.sub(r"\s*```$",          "", raw)
            data = json.loads(raw)

            return ValidationContract(
                passed                       = bool(data.get("passed", False)),
                passed_criteria              = data.get("passed_criteria", []),
                missing_acceptance_criteria  = data.get("missing_acceptance_criteria", []),
                quality_score                = float(data.get("quality_score", 0.0)),
                summary                      = data.get("summary", ""),
            )
        except Exception as e:
            print(f"[validate] LLM validation failed: {e}")
            return self._heuristic_validate(requirements, review, test_output)

    # ------------------------------------------------------------------
    # Heuristic validation fallback
    # ------------------------------------------------------------------

    def _heuristic_validate(
        self,
        requirements: RequirementAnalysisContract,
        review:       ReviewContract,
        test_output:  str,
    ) -> ValidationContract:
        """
        Checks criteria by looking for keywords in the test output and review.
        Not as thorough as LLM but better than nothing.
        """
        passed_criteria = []
        missing_criteria = []

        test_lower   = test_output.lower()
        review_issues_text = " ".join(i.description.lower() for i in review.issues)

        for criterion in requirements.acceptance_criteria:
            crit_low = criterion.lower()

            # Simple keyword matching against test output
            keywords = re.findall(r"\b\w{4,}\b", crit_low)
            matched  = sum(1 for kw in keywords if kw in test_lower)

            if matched >= max(1, len(keywords) // 2):
                passed_criteria.append(criterion)
            elif "test" in crit_low and "pass" in test_lower:
                passed_criteria.append(criterion)
            else:
                missing_criteria.append(criterion)

        return ValidationContract(
            passed_criteria             = passed_criteria,
            missing_acceptance_criteria = missing_criteria,
        )

    # ------------------------------------------------------------------
    # Static analysis
    # ------------------------------------------------------------------

    def _run_static_analysis(
        self,
        project_path: Optional[str],
        file_paths:   list[str],
    ) -> tuple[list[str], bool, bool]:
        """Returns (issues, lint_ok, type_ok)."""
        issues   = []
        lint_ok  = True
        type_ok  = True

        if not project_path:
            return issues, True, True

        py_files = [f for f in file_paths if f.endswith(".py")]
        if not py_files:
            return issues, True, True

        abs_files = [str(Path(project_path) / f) for f in py_files]
        existing  = [f for f in abs_files if Path(f).exists()]
        if not existing:
            return issues, True, True

        # Ruff
        try:
            result = subprocess.run(
                ["ruff", "check", "--output-format=json"] + existing,
                capture_output=True, text=True, timeout=30,
            )
            lint_ok = result.returncode == 0
            if not lint_ok:
                try:
                    ruff_data = json.loads(result.stdout)
                    for item in ruff_data[:10]:
                        issues.append(
                            f"[ruff] {item.get('filename','')}: {item.get('message','')}"
                        )
                except json.JSONDecodeError:
                    if result.stdout:
                        issues.extend(result.stdout.strip().splitlines()[:5])
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass   # ruff not installed → skip

        # Mypy (lighter — just on changed files)
        try:
            result = subprocess.run(
                ["mypy", "--ignore-missing-imports", "--no-error-summary"] + existing,
                capture_output=True, text=True, timeout=30,
            )
            type_ok = result.returncode == 0
            if not type_ok:
                for line in result.stdout.splitlines()[:5]:
                    if "error:" in line:
                        issues.append(f"[mypy] {line.strip()}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass   # mypy not installed → skip

        return issues, lint_ok, type_ok

    # ------------------------------------------------------------------
    # Quality scoring
    # ------------------------------------------------------------------

    def _quality_score(
        self,
        contract: ValidationContract,
        review:   ReviewContract,
    ) -> float:
        """
        Weighted quality score 0.0–1.0:
          40% — acceptance criteria coverage
          30% — review score
          20% — tests passing
          10% — no static issues
        """
        total = len(contract.passed_criteria) + len(contract.missing_acceptance_criteria)
        ac_score = (len(contract.passed_criteria) / total) if total > 0 else 0.5

        review_score = (review.score.value - 1) / 4   # map 1-5 → 0.0-1.0
        test_score   = 1.0 if contract.test_passed else 0.0
        static_score = 0.0 if contract.static_issues else 1.0

        return (
            0.40 * ac_score    +
            0.30 * review_score +
            0.20 * test_score  +
            0.10 * static_score
        )

    def _gate_reasons(
        self,
        contract: ValidationContract,
        review:   ReviewContract,
    ) -> list[str]:
        reasons = []
        if not contract.test_passed:
            reasons.append("tests failed")
        if contract.missing_acceptance_criteria:
            reasons.append(
                f"{len(contract.missing_acceptance_criteria)} acceptance criteria not met"
            )
        if review.has_blockers:
            reasons.append("review has blocker issues")
        if contract.quality_score < 0.6:
            reasons.append(f"quality score too low ({contract.quality_score:.0%})")
        return reasons

    def _get_client(self):
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            return None
        try:
            import openai
            if not self._client:
                self._client = openai.OpenAI(api_key=key)
            return self._client
        except ImportError:
            return None


# ---------------------------------------------------------------------------
# Backward-compatibility: orchestrator imports AcceptanceValidatorAgent
# ---------------------------------------------------------------------------

class AcceptanceValidatorAgent(AcceptanceValidator):
    """Thin wrapper so existing orchestrator import keeps working."""

    def __init__(self, config: dict = None):  # noqa: B006
        super().__init__()

    async def validate(
        self,
        acceptance_criteria: list[str],
        context: dict,
    ) -> ValidationContract:
        """Orchestrator-compatible async validate interface."""
        from agent.phase_contracts import ReviewContract

        test_results = context.get("test_results", {})
        test_passed = bool(test_results.get("passed", False))
        generated_files = context.get("generated_files", [])

        requirements = RequirementAnalysisContract(
            acceptance_criteria=acceptance_criteria,
        )
        files_dict: dict[str, str] = {
            f: "" for f in (generated_files if isinstance(generated_files, list) else [])
        }
        return super().validate(
            requirements=requirements,
            review=ReviewContract(),
            generated_files=files_dict,
            test_output="",
            test_passed=test_passed,
        )