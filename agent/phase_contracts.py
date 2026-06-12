"""Shared typed contracts across orchestrator phase agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RequirementAnalysisContract:
    business_goal: str = ""
    functional_requirements: list[str] = field(default_factory=list)
    non_functional_requirements: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "business_goal": self.business_goal,
            "functional_requirements": self.functional_requirements,
            "non_functional_requirements": self.non_functional_requirements,
            "acceptance_criteria": self.acceptance_criteria,
            "risks": self.risks,
            "dependencies": self.dependencies,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "RequirementAnalysisContract":
        payload = data or {}
        return cls(
            business_goal=str(payload.get("business_goal", "")),
            functional_requirements=list(payload.get("functional_requirements", [])),
            non_functional_requirements=list(
                payload.get("non_functional_requirements", [])
            ),
            acceptance_criteria=list(payload.get("acceptance_criteria", [])),
            risks=list(payload.get("risks", [])),
            dependencies=list(payload.get("dependencies", [])),
        )


@dataclass(slots=True)
class ArchitectureContract:
    architecture_style: str = ""
    modules: list[str] = field(default_factory=list)
    integration_points: list[str] = field(default_factory=list)
    database_changes: list[str] = field(default_factory=list)
    api_changes: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "architecture_style": self.architecture_style,
            "modules": self.modules,
            "integration_points": self.integration_points,
            "database_changes": self.database_changes,
            "api_changes": self.api_changes,
            "risks": self.risks,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ArchitectureContract":
        payload = data or {}
        return cls(
            architecture_style=str(payload.get("architecture_style", "")),
            modules=list(payload.get("modules", [])),
            integration_points=list(payload.get("integration_points", [])),
            database_changes=list(payload.get("database_changes", [])),
            api_changes=list(payload.get("api_changes", [])),
            risks=list(payload.get("risks", [])),
        )


@dataclass(slots=True)
class SolutionDesignContract:
    files_to_modify: list[str] = field(default_factory=list)
    files_to_create: list[str] = field(default_factory=list)
    architecture_changes: list[str] = field(default_factory=list)
    implementation_steps: list[str] = field(default_factory=list)
    test_plan: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_to_modify": self.files_to_modify,
            "files_to_create": self.files_to_create,
            "architecture_changes": self.architecture_changes,
            "implementation_steps": self.implementation_steps,
            "test_plan": self.test_plan,
            "risks": self.risks,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SolutionDesignContract":
        payload = data or {}
        return cls(
            files_to_modify=list(payload.get("files_to_modify", [])),
            files_to_create=list(payload.get("files_to_create", [])),
            architecture_changes=list(payload.get("architecture_changes", [])),
            implementation_steps=list(payload.get("implementation_steps", [])),
            test_plan=list(payload.get("test_plan", [])),
            risks=list(payload.get("risks", [])),
        )


@dataclass(slots=True)
class ImpactAnalysisContract:
    files_to_modify: list[str] = field(default_factory=list)
    files_to_create: list[str] = field(default_factory=list)
    files_to_avoid: list[str] = field(default_factory=list)
    affected_tests: list[str] = field(default_factory=list)
    reasoning: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_to_modify": self.files_to_modify,
            "files_to_create": self.files_to_create,
            "files_to_avoid": self.files_to_avoid,
            "affected_tests": self.affected_tests,
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ImpactAnalysisContract":
        payload = data or {}
        return cls(
            files_to_modify=list(payload.get("files_to_modify", [])),
            files_to_create=list(payload.get("files_to_create", [])),
            files_to_avoid=list(payload.get("files_to_avoid", [])),
            affected_tests=list(payload.get("affected_tests", [])),
            reasoning=dict(payload.get("reasoning", {})),
        )


@dataclass(slots=True)
class ImplementationPlanContract:
    implementation_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"implementation_steps": self.implementation_steps}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ImplementationPlanContract":
        payload = data or {}
        return cls(implementation_steps=list(payload.get("implementation_steps", [])))


@dataclass(slots=True)
class StaticValidationContract:
    passed: bool = False
    issues: list[str] = field(default_factory=list)
    output: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "issues": self.issues,
            "output": self.output,
        }


@dataclass(slots=True)
class AcceptanceValidationContract:
    passed: bool = False
    satisfied_criteria: list[str] = field(default_factory=list)
    missing_criteria: list[str] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)
    security_issues: list[str] = field(default_factory=list)
    security_passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "satisfied_criteria": self.satisfied_criteria,
            "missing_criteria": self.missing_criteria,
            "checks": self.checks,
            "security_issues": self.security_issues,
            "security_passed": self.security_passed,
        }


@dataclass(slots=True)
class ReviewReportContract:
    score: int = 0
    passed: bool = False
    issues: list[str] = field(default_factory=list)
    quality_checks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "passed": self.passed,
            "issues": self.issues,
            "quality_checks": self.quality_checks,
        }
