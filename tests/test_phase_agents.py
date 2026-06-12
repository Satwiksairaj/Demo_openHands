"""Unit tests for typed phase agents and contracts."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agent.acceptance_validator import AcceptanceValidatorAgent
from agent.phase_contracts import (
    ImpactAnalysisContract,
    RequirementAnalysisContract,
    ArchitectureContract,
    SolutionDesignContract,
    StaticValidationContract,
)
from agent.planning_agent import PlanningAgent
from agent.requirement_agent import RequirementAnalysisAgent
from agent.phase_contracts import ArchitectureContract
from agent.review_agent import ReviewAgent
from agent.solution_designer import SolutionDesignerAgent
from agent.static_validation import StaticValidationAgent

CONFIG: dict = {}


@pytest.mark.asyncio
async def test_requirement_agent_returns_contract() -> None:
    agent = RequirementAnalysisAgent(CONFIG)
    story = {
        "title": "Add secure login",
        "requirements": ["Implement login", "Improve performance"],
        "acceptance_criteria": ["Login works"],
        "technical_hints": ["Use OAuth validation"],
    }

    result = await agent.analyze(story)

    assert isinstance(result, RequirementAnalysisContract)
    assert result.business_goal == "Add secure login"
    assert "Improve performance" in result.non_functional_requirements


# @pytest.mark.asyncio
# async def test_solution_designer_uses_contracts() -> None:
#     agent = SolutionDesignerAgent(CONFIG)
#     requirements = RequirementAnalysisContract(
#         acceptance_criteria=["Returns 200"], risks=["Auth regression"]
#     )
#     repo = {
#         "entry_points": ["app.py"],
#         "routes": ["routes.py"],
#         "models": ["models.py"],
#         "tests": ["tests/test_app.py"],
#         "architecture": "layered",
#     }
@pytest.mark.asyncio
async def test_solution_designer_uses_contracts() -> None:
    agent = SolutionDesignerAgent(CONFIG)

    requirements = RequirementAnalysisContract(
        acceptance_criteria=["Returns 200"],
        risks=["Auth regression"],
    )

    architecture = ArchitectureContract(
        architecture_style="layered",
        modules=["Authentication"],
        integration_points=["API"],
        risks=[],
    )

    repo = {
        "entry_points": ["app.py"],
        "routes": ["routes.py"],
        "models": ["models.py"],
        "tests": ["tests/test_app.py"],
        "architecture": "layered",
    }

    design = await agent.design(
        requirements,
        architecture,
        repo,
        {},
    )

    assert isinstance(design, SolutionDesignContract)

    #design = await agent.design(requirements, repo, {})
    # from agent.phase_contracts import ArchitectureContract

    architecture = ArchitectureContract(
        architecture_style="layered",
        modules=["Auth"],
        integration_points=["API"],
        risks=[]
    )
    
    design = await agent.design(
        requirements,
        architecture,
        repo,
        {},
    )

    assert isinstance(design, SolutionDesignContract)
    assert "app.py" in design.files_to_modify
    assert design.test_plan == ["Returns 200"]


@pytest.mark.asyncio
async def test_planning_agent_uses_contracts() -> None:
    agent = PlanningAgent(CONFIG)
    design = SolutionDesignContract(implementation_steps=["Refactor handler"])
    impact = ImpactAnalysisContract(
        files_to_modify=["app.py"], files_to_create=["tests/test_app.py"]
    )

    plan = await agent.plan(design, impact)

    assert "Modify app.py" in plan.implementation_steps
    assert "Create tests/test_app.py" in plan.implementation_steps


@pytest.mark.asyncio
async def test_static_validation_returns_contract() -> None:
    agent = StaticValidationAgent(CONFIG)

    ok = MagicMock(returncode=0, stdout="ok", stderr="")
    with patch("agent.static_validation.subprocess.run", return_value=ok):
        report = await agent.run(".")

    assert isinstance(report, StaticValidationContract)
    assert report.passed is True


@pytest.mark.asyncio
async def test_acceptance_validator_returns_contract() -> None:
    agent = AcceptanceValidatorAgent(CONFIG)

    report = await agent.validate(
        acceptance_criteria=["AC1", "AC2"],
        context={
            "test_results": {"passed": True},
            "static_validation": StaticValidationContract(passed=True),
            "generated_files": ["app.py"],
        },
    )

    assert report.passed is True
    assert len(report.satisfied_criteria) == 2


@pytest.mark.asyncio
async def test_review_agent_returns_contract(tmp_path) -> None:
    agent = ReviewAgent(CONFIG)
    small_file = tmp_path / "a.py"
    small_file.write_text("print('ok')\n", encoding="utf-8")

    report = await agent.review(
        workspace=str(tmp_path),
        generated_files=["a.py"],
        context={
            "test_results": {"passed": True},
            "static_validation": {"passed": True},
        },
    )

    assert report.passed is True
    assert report.score >= 85
