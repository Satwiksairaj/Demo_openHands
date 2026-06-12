"""Shared typed contracts used by phase agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReviewScore(Enum):
    FAIL = 1
    PASS_MINOR = 3
    PASS_STRONG = 4
    PASS_EXCELLENT = 5


@dataclass
class RequirementAnalysisContract:
    functional_requirements: list[str] = field(default_factory=list)
    non_functional_requirements: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    domain_entities: list[str] = field(default_factory=list)
    api_endpoints: list[str] = field(default_factory=list)
    edge_cases: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    story_id: str = ""
    complexity: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "functional_requirements": self.functional_requirements,
            "non_functional_requirements": self.non_functional_requirements,
            "acceptance_criteria": self.acceptance_criteria,
            "domain_entities": self.domain_entities,
            "api_endpoints": self.api_endpoints,
            "edge_cases": self.edge_cases,
            "risks": self.risks,
            "dependencies": self.dependencies,
            "story_id": self.story_id,
            "complexity": self.complexity,
        }


@dataclass
class ArchitectureContract:
    architecture_style: str = "layered"
    modules: list[str] = field(default_factory=list)
    integration_points: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "architecture_style": self.architecture_style,
            "modules": self.modules,
            "integration_points": self.integration_points,
            "risks": self.risks,
        }


@dataclass
class ImpactAnalysisContract:
    files_to_modify: list[str] = field(default_factory=list)
    files_to_create: list[str] = field(default_factory=list)
    files_to_avoid: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_to_modify": self.files_to_modify,
            "files_to_create": self.files_to_create,
            "files_to_avoid": self.files_to_avoid,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ImpactAnalysisContract":
        payload = data or {}
        return cls(
            files_to_modify=list(payload.get("files_to_modify", [])),
            files_to_create=list(payload.get("files_to_create", [])),
            files_to_avoid=list(payload.get("files_to_avoid", [])),
        )


@dataclass
class ImplementationStep:
    order: int
    description: str
    file_path: str = ""
    change_type: str = "modify"


@dataclass
class ImplementationPlanContract:
    implementation_steps: list[ImplementationStep] = field(default_factory=list)
    test_strategy: list[str] = field(default_factory=list)
    approach_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "implementation_steps": [
                {
                    "order": s.order,
                    "description": s.description,
                    "file_path": s.file_path,
                    "change_type": s.change_type,
                }
                for s in self.implementation_steps
            ],
            "test_strategy": self.test_strategy,
            "approach_summary": self.approach_summary,
        }


@dataclass
class CodeIssue:
    severity: str
    file_path: str
    description: str


@dataclass
class ReviewContract:
    score: ReviewScore = ReviewScore.PASS_MINOR
    approved: bool = True
    issues: list[CodeIssue] = field(default_factory=list)
    summary: str = ""

    @property
    def passed(self) -> bool:
        return self.approved

    @property
    def has_blockers(self) -> bool:
        return any(i.severity == "blocker" for i in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score.value,
            "approved": self.approved,
            "passed": self.passed,
            "issues": [
                {
                    "severity": i.severity,
                    "file_path": i.file_path,
                    "description": i.description,
                }
                for i in self.issues
            ],
            "summary": self.summary,
        }


@dataclass
class ValidationContract:
    passed: bool = False
    missing_acceptance_criteria: list[str] = field(default_factory=list)
    passed_criteria: list[str] = field(default_factory=list)
    test_passed: bool = False
    test_output: str = ""
    quality_score: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "missing_acceptance_criteria": self.missing_acceptance_criteria,
            "passed_criteria": self.passed_criteria,
            "test_passed": self.test_passed,
            "test_output": self.test_output,
            "quality_score": self.quality_score,
            "summary": self.summary,
        }


@dataclass
class StaticValidationContract:
    passed: bool = False
    issues: list[str] = field(default_factory=list)
    output: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "issues": self.issues, "output": self.output}


@dataclass
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


AcceptanceValidationContract = ValidationContract
ReviewReportContract = ReviewContract
