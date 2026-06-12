"""Acceptance criteria validation agent."""

from __future__ import annotations

from agent.phase_contracts import AcceptanceValidationContract, StaticValidationContract


class AcceptanceValidatorAgent:
    """Verifies acceptance criteria compliance based on test and validation outputs."""

    def __init__(self, config: dict):
        self.config = config

    async def validate(
        self,
        acceptance_criteria: list[str],
        context: dict,
    ) -> AcceptanceValidationContract:
        test_passed = context.get("test_results", {}).get("passed", False)
        static_validation = context.get("static_validation")
        if isinstance(static_validation, StaticValidationContract):
            static_passed = static_validation.passed
        else:
            static_passed = context.get("static_validation", {}).get("passed", False)
        generated_files = context.get("generated_files", [])

        satisfied: list[str] = []
        missing: list[str] = []
        for criterion in acceptance_criteria:
            if test_passed and static_passed:
                satisfied.append(criterion)
            else:
                missing.append(criterion)

        checks = [
            {"name": "tests_passed", "passed": test_passed},
            {"name": "static_validation", "passed": static_passed},
            {"name": "files_changed", "passed": bool(generated_files)},
        ]

        return AcceptanceValidationContract(
            passed=len(missing) == 0,
            satisfied_criteria=satisfied,
            missing_criteria=missing,
            checks=checks,
        )
