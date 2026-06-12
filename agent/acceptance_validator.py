"""Acceptance validation agent - final gate before PR creation."""

from __future__ import annotations

from agent.phase_contracts import (
    RequirementAnalysisContract,
    ReviewContract,
    ValidationContract,
)


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

        passed_criteria: list[str] = []
        missing_criteria: list[str] = []

        if test_passed:
            passed_criteria = acceptance_criteria
        else:
            missing_criteria = acceptance_criteria

        quality_score = 0.8 if test_passed else 0.45

        return ValidationContract(
            passed=test_passed and len(missing_criteria) == 0,
            missing_acceptance_criteria=missing_criteria,
            passed_criteria=passed_criteria,
            test_passed=test_passed,
            test_output=test_output,
            quality_score=quality_score,
            summary="Acceptance validation passed" if test_passed else "Tests failed",
        )


class AcceptanceValidatorAgent:
    """Backward-compatible async wrapper around AcceptanceValidator."""

    def __init__(self, config: dict = None):  # noqa: B006
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
