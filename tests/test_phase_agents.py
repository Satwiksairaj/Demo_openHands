"""Unit tests for typed phase agents and contracts."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agent.acceptance_validator import AcceptanceValidator, AcceptanceValidatorAgent
from agent.architecture_agent import ArchitectureAgent
from agent.phase_contracts import (
    ArchitectureContract,
    ImpactAnalysisContract,
    ImplementationPlanContract,
    RequirementAnalysisContract,
    ReviewContract,
    SolutionDesignContract,
    StaticValidationContract,
    ValidationContract,
)
from agent.planning_agent import PlanningAgent
from agent.requirement_agent import RequirementAgent, RequirementAnalysisAgent
from agent.review_agent import ReviewAgent
from agent.solution_designer import SolutionDesignerAgent
from agent.static_validation import StaticValidationAgent

CONFIG: dict = {}


@pytest.mark.asyncio
async def test_requirement_agent_returns_contract() -> None:
    agent = RequirementAgent()
    result = agent.analyse("Add secure login with JWT tokens")

    assert isinstance(result, RequirementAnalysisContract)
    assert isinstance(result.functional_requirements, list)


@pytest.mark.asyncio
async def test_requirement_analysis_agent_compat_wrapper() -> None:
    agent = RequirementAnalysisAgent(CONFIG)
    story = {
        "story_id": "TEST-1",
        "title": "Add secure login",
        "requirements": ["Implement JWT login", "Protect API endpoints"],
        "acceptance_criteria": ["Login works"],
    }
    result = await agent.analyze(story)

    assert isinstance(result, RequirementAnalysisContract)
    assert result.story_id == "TEST-1"


@pytest.mark.asyncio
async def test_architecture_agent_analyze() -> None:
    agent = ArchitectureAgent()
    requirements = RequirementAnalysisContract(
        functional_requirements=["Handle login flow"],
    )
    repo_analysis = {"framework": "Flask", "patterns": ["MVC"]}

    result = await agent.analyze(requirements, repo_analysis)

    assert isinstance(result, ArchitectureContract)
    assert result.architecture_style is not None


@pytest.mark.asyncio
async def test_solution_designer_uses_contracts() -> None:
    agent = SolutionDesignerAgent(CONFIG)

    requirements = RequirementAnalysisContract(
        acceptance_criteria=["Returns 200"],
        risks=[],
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

    design = await agent.design(requirements, architecture, repo, {})

    assert isinstance(design, SolutionDesignContract)


@pytest.mark.asyncio
async def test_planning_agent_uses_contracts() -> None:
    agent = PlanningAgent(CONFIG)
    requirements = RequirementAnalysisContract(
        functional_requirements=["Handle requests"],
        acceptance_criteria=["Returns 200"],
    )
    architecture = ArchitectureContract(architecture_style="layered")
    impact = ImpactAnalysisContract(
        files_to_modify=["app.py"],
        files_to_create=["tests/test_app.py"],
    )

    plan = agent.plan(requirements, architecture, impact)

    assert isinstance(plan, ImplementationPlanContract)
    assert isinstance(plan.implementation_steps, list)


@pytest.mark.asyncio
async def test_static_validation_returns_contract() -> None:
    agent = StaticValidationAgent(CONFIG)

    ok = MagicMock(returncode=0, stdout="ok", stderr="")
    with patch("agent.static_validation.subprocess.run", return_value=ok):
        result = await agent.run("/tmp/repo")

    assert isinstance(result, StaticValidationContract)
    assert result.passed is True


@pytest.mark.asyncio
async def test_acceptance_validator_returns_contract() -> None:
    agent = AcceptanceValidator()
    requirements = RequirementAnalysisContract(
        acceptance_criteria=["Feature X works"],
    )
    review = ReviewContract()

    result = agent.validate(
        requirements=requirements,
        review=review,
        generated_files={"app.py": "print('hello')"},
        test_output="all pass",
        test_passed=True,
    )

    assert isinstance(result, ValidationContract)


@pytest.mark.asyncio
async def test_acceptance_validatoragent_compat_wrapper() -> None:
    agent = AcceptanceValidatorAgent(CONFIG)

    result = await agent.validate(
        acceptance_criteria=["Feature works"],
        context={
            "test_results": {"passed": True},
            "generated_files": [],
            "static_validation": None,
        },
    )

    assert isinstance(result, ValidationContract)


@pytest.mark.asyncio
async def test_review_agent_returns_contract() -> None:
    agent = ReviewAgent()
    requirements = RequirementAnalysisContract(
        functional_requirements=["Login feature"],
    )
    architecture = ArchitectureContract(architecture_style="layered")
    plan = ImplementationPlanContract()

    result = agent.review(
        generated_files={"auth.py": "class Auth: pass"},
        requirements=requirements,
        architecture=architecture,
        plan=plan,
    )

    assert isinstance(result, ReviewContract)
    assert hasattr(result, "score")
    assert hasattr(result, "issues")
