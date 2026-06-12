"""
Orchestrator Agent - Controls the complete autonomous development workflow.
Supports both traditional LLM-based code generation and OpenHands SDK integration.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from agent.jira_agent import JiraAgent
from agent.repo_agent import RepositoryAgent
from agent.code_agent import CodeGenerationAgent
from agent.testing_agent import TestingAgent
from agent.github_agent import GitHubAgent
from agent.openhands_agent import OpenHandsWorkflowIntegration
from agent.prompt_builder import PromptBuilderAgent
from agent.error_agent import ErrorAnalysisAgent
from agent.requirement_agent import RequirementAnalysisAgent
from agent.architecture_agent import ArchitectureAgent
from agent.solution_designer import SolutionDesignerAgent
from agent.planning_agent import PlanningAgent
from agent.static_validation import StaticValidationAgent
from agent.acceptance_validator import AcceptanceValidatorAgent
from agent.review_agent import ReviewAgent
from agent.impact_analyzer import ImpactAnalyzer
from agent.phase_contracts import (
    AcceptanceValidationContract,
    ArchitectureContract,
    ImpactAnalysisContract,
    ImplementationPlanContract,
    RequirementAnalysisContract,
    ReviewReportContract,
    SolutionDesignContract,
    StaticValidationContract,
)
from app.services.project_context_manager import ProjectContextManager

OPENHANDS_AVAILABLE = True

logger = logging.getLogger(__name__)


class WorkflowStep(Enum):
    INIT = "init"
    JIRA_FETCH = "jira_fetch"
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    ARCHITECTURE = "architecture"
    PROJECT_CONTEXT = "project_context"
    REPO_CLONE = "repo_clone"
    REPO_UNDERSTANDING = "repo_understanding"
    SOLUTION_DESIGN = "solution_design"
    IMPACT_ANALYSIS = "impact_analysis"
    IMPLEMENTATION_PLAN = "implementation_plan"
    CODE_GENERATION = "code_generation"
    STATIC_VALIDATION = "static_validation"
    TESTING = "testing"
    HEALING = "healing"
    ACCEPTANCE_VALIDATION = "acceptance_validation"
    REVIEW = "review"
    GIT_OPS = "git_ops"
    PR_CREATION = "pr_creation"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class WorkflowState:
    story_id: Optional[str] = None
    natural_prompt: Optional[str] = None
    current_step: WorkflowStep = WorkflowStep.INIT
    story_data: dict = field(default_factory=dict)
    requirement_analysis: RequirementAnalysisContract = field(
        default_factory=RequirementAnalysisContract
    )
    architecture: ArchitectureContract = field(
    default_factory=ArchitectureContract
    )
    project_context: dict = field(default_factory=dict)
    repo_analysis: dict = field(default_factory=dict)
    solution_design: SolutionDesignContract = field(
        default_factory=SolutionDesignContract
    )
    impact_analysis: ImpactAnalysisContract = field(
        default_factory=ImpactAnalysisContract
    )
    implementation_plan: ImplementationPlanContract = field(
        default_factory=ImplementationPlanContract
    )
    generated_files: list = field(default_factory=list)
    static_validation: StaticValidationContract = field(
        default_factory=StaticValidationContract
    )
    test_results: dict = field(default_factory=dict)
    review_report: ReviewReportContract = field(default_factory=ReviewReportContract)
    validation_report: AcceptanceValidationContract = field(
        default_factory=AcceptanceValidationContract
    )
    healing_attempts: list = field(default_factory=list)  # list of ErrorReport dicts
    execution_report: dict = field(default_factory=dict)
    pr_url: Optional[str] = None
    branch_name: Optional[str] = None
    workspace_path: Optional[str] = None
    errors: list = field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 8
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None


class OrchestratorAgent:
    """
    Master orchestrator that coordinates all sub-agents to complete
    the full autonomous software development lifecycle using OpenHands.
    """

    def __init__(self, config: dict, strict_mode: bool = True):
        self.config = config
        self.strict_mode = strict_mode
        if not self.strict_mode:
            raise ValueError("Only strict_mode=True is supported")

        # Core agents
        self.jira_agent = JiraAgent(config)
        self.repo_agent = RepositoryAgent(config)
        self.github_agent = GitHubAgent(config)
        self.state = WorkflowState()

        logger.info("🚀 Using OpenHands SDK for code generation and testing")
        self.openhands = OpenHandsWorkflowIntegration(config)
        self.code_agent = CodeGenerationAgent(config)
        self.testing_agent = TestingAgent(config)
        self.prompt_builder = PromptBuilderAgent()
        self.error_agent = ErrorAnalysisAgent(
            max_identical_failures=config.get("max_identical_failures", 2)
        )
        self.requirement_agent = RequirementAnalysisAgent(config)
        self.architecture_agent = ArchitectureAgent(config)
        self.solution_designer = SolutionDesignerAgent(config)
        self.planning_agent = PlanningAgent(config)
        self.static_validation_agent = StaticValidationAgent(config)
        self.acceptance_validator = AcceptanceValidatorAgent(config)
        self.review_agent = ReviewAgent(config)
        self.context_manager = ProjectContextManager()
        self.impact_analyzer: Optional[ImpactAnalyzer] = None

    async def run(self,  story_id: Optional[str] = None,
    prompt: Optional[str] = None) -> WorkflowState:
        """Execute the complete autonomous development workflow."""
        self.state.story_id = story_id
        self.state.natural_prompt = prompt

        logger.info("🚀 Starting autonomous development workflow")
        logger.info(f"   Story ID: {story_id or 'N/A'}")
        logger.info(f"   Prompt: {prompt or 'N/A'}")

        steps = [
            (WorkflowStep.JIRA_FETCH, self._step_jira_fetch),
            (WorkflowStep.REQUIREMENT_ANALYSIS, self._step_requirement_analysis),
            (WorkflowStep.ARCHITECTURE, self._step_architecture),
            (WorkflowStep.PROJECT_CONTEXT, self._step_project_context),
            (WorkflowStep.REPO_CLONE, self._step_repo_clone),
            (WorkflowStep.REPO_UNDERSTANDING, self._step_repo_analysis),
            (WorkflowStep.SOLUTION_DESIGN, self._step_solution_design),
            (WorkflowStep.IMPACT_ANALYSIS, self._step_impact_analysis),
            (WorkflowStep.IMPLEMENTATION_PLAN, self._step_implementation_plan),
            (WorkflowStep.CODE_GENERATION, self._step_code_generation),
            (WorkflowStep.STATIC_VALIDATION, self._step_static_validation),
            (WorkflowStep.TESTING, self._step_testing),
            (WorkflowStep.HEALING, self._step_healing),
            (WorkflowStep.ACCEPTANCE_VALIDATION, self._step_validation),
            (WorkflowStep.REVIEW, self._step_review),
            (WorkflowStep.GIT_OPS, self._step_git_ops),
            (WorkflowStep.PR_CREATION, self._step_pr_creation),
        ]

        for step_enum, step_fn in steps:
            self.state.current_step = step_enum
            logger.info(f"\n{'='*60}")
            logger.info(f"📍 Step: {step_enum.value.upper()}")
            logger.info(f"{'='*60}")
            try:
                await step_fn()
            except Exception as e:
                logger.error(f"❌ Step {step_enum.value} failed: {e}")
                self.state.errors.append({"step": step_enum.value, "error": str(e)})
                self.state.current_step = WorkflowStep.FAILED
                self.state.completed_at = datetime.now(timezone.utc).isoformat()
                # return self.state
                raise


        self.state.current_step = WorkflowStep.COMPLETE
        self.state.completed_at = datetime.now(timezone.utc).isoformat()
        if self.openhands:
            await self.openhands.teardown()

        self.state.execution_report = self._build_execution_report()
        logger.info(f"\n✅ Workflow complete! PR: {self.state.pr_url}")
        logger.info(self._format_execution_report(self.state.execution_report))
        return self.state

    async def _step_jira_fetch(self):
        """Step 1: Fetch and parse Jira story."""
        if self.state.story_id:
            logger.info(f"Fetching Jira story: {self.state.story_id}")
            self.state.story_data = await self.jira_agent.fetch_story(
                self.state.story_id
            )
        else:
            logger.info("Parsing natural language prompt into requirements")
            self.state.story_data = await self.jira_agent.parse_prompt(
                self.state.natural_prompt
            )

        logger.info(
            f"✅ Requirements parsed: {json.dumps(self.state.story_data, indent=2)}"
        )

    async def _step_requirement_analysis(self):
        """Phase 1: Structured requirement analysis."""
        self.state.requirement_analysis = await self.requirement_agent.analyze(
            self.state.story_data
        )
        
        logger.info(
            f"✅ Requirement analysis: {json.dumps(self.state.requirement_analysis.to_dict(), indent=2)}"
        )
    async def _step_architecture(self):
        # NEW
        self.state.architecture = await self.architecture_agent.analyze(
            self.state.requirement_analysis,
            self.state.repo_analysis,
        )

        logger.info(
        f"🏗 Architecture:\n"
        f"{json.dumps(self.state.architecture.to_dict(), indent=2)}"
        )

    
    async def _step_project_context(self):
        """Phase 2: Load and update project context memory."""
        active = self.context_manager.get_active_project()
        if active:
            self.state.project_context = {
                "project_name": active.project_name,
                "path": active.path,
                "framework": active.framework,
                "architecture": getattr(active, "architecture", ""),
                "language": active.language,
                "database": active.database,
                "auth_pattern": active.auth_pattern,
                "test_framework": active.test_framework,
                "coding_style": active.coding_style,
                "coding_conventions": getattr(active, "coding_conventions", ""),
                "decisions": active.decisions,
                "story_history": active.story_history,
                "project_history": getattr(active, "project_history", []),
            }
        else:
            self.state.project_context = {}
        logger.info("✅ Project context loaded")

    async def _step_repo_clone(self):
        """Step 2: Clone repository and create feature branch."""
        from datetime import datetime as _dt, timezone as _tz

        repo_url = self.config["github"]["repo_url"]
        story_id = self.state.story_data.get("story_id", "feature")
        # Add a timestamp suffix so every run gets a unique branch name
        ts = _dt.now(_tz.utc).strftime("%Y%m%d%H%M")
        self.state.branch_name = f"feature/{story_id.lower()}-{ts}"

        logger.info(f"Cloning: {repo_url}")
        logger.info(f"Branch: {self.state.branch_name}")

        self.state.workspace_path = await self.repo_agent.clone_and_branch(
            repo_url, self.state.branch_name
        )
        logger.info(f"✅ Repository ready at: {self.state.workspace_path}")

    async def _step_repo_analysis(self):
        """Phase 3: Repository understanding."""
        logger.info(f"Analyzing repository at: {self.state.workspace_path}")
        self.state.repo_analysis = await self.repo_agent.analyze(
            self.state.workspace_path, self.state.story_data
        )
        self.context_manager.update_from_analysis(self.state.repo_analysis)
        logger.info(f"✅ Analysis:\n{json.dumps(self.state.repo_analysis, indent=2)}")

    async def _step_solution_design(self):
        """Phase 4: Design solution before coding."""
        self.state.solution_design = await self.solution_designer.design(
            requirements=self.state.requirement_analysis,
            architecture=self.state.architecture,
            repository_analysis=self.state.repo_analysis,
            project_context=self.state.project_context,
        )
        logger.info(
            f"✅ Solution design:\n{json.dumps(self.state.solution_design.to_dict(), indent=2)}"
        )

    async def _step_impact_analysis(self):
        """Phase 5: Analyze codebase impact and modification boundaries."""
        self.impact_analyzer = ImpactAnalyzer(self.state.workspace_path)
        query = " ".join(self.state.story_data.get("requirements", []))
        self.state.impact_analysis = ImpactAnalysisContract.from_dict(
            self.impact_analyzer.analyze_structured(query)
        )
        logger.info(
            f"✅ Impact analysis:\n{json.dumps(self.state.impact_analysis.to_dict(), indent=2)}"
        )

    async def _step_implementation_plan(self):
        """Phase 6: Create implementation roadmap."""
        self.state.implementation_plan = await self.planning_agent.plan(
            solution_design=self.state.solution_design,
            impact_analysis=self.state.impact_analysis,
        )
        logger.info(
            f"✅ Implementation plan:\n{json.dumps(self.state.implementation_plan.to_dict(), indent=2)}"
        )

    async def _step_code_generation(self):
        """Phase 7: Generate implementation after design and planning."""
        logger.info("Generating implementation code...")

        self.state.generated_files = await self.code_agent.generate(
            story=self.state.story_data,
            repo_analysis=self.state.repo_analysis,
            workspace=self.state.workspace_path,
            solution_design=self.state.solution_design.to_dict(),
            implementation_plan=self.state.implementation_plan.to_dict(),
            impact_analysis=self.state.impact_analysis.to_dict(),
        )

        # Always detect changed files via git diff (most reliable)
        if not self.state.generated_files and self.state.workspace_path:
            import subprocess

            try:
                r1 = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD"],
                    cwd=self.state.workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                r2 = subprocess.run(
                    ["git", "ls-files", "--others", "--exclude-standard"],
                    cwd=self.state.workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                self.state.generated_files = [
                    f
                    for f in r1.stdout.strip().splitlines()
                    + r2.stdout.strip().splitlines()
                    if f
                ]
            except Exception:
                pass

        logger.info(f"Generated/modified {len(self.state.generated_files)} files")
        for f in self.state.generated_files:
            logger.info(f"   - {f}")

    async def _step_static_validation(self):
        """Phase 8: Static validation gate before tests."""
        self.state.static_validation = await self.static_validation_agent.run(
            self.state.workspace_path
        )
        logger.info(
            "✅ Static validation:\n"
            f"{json.dumps(self.state.static_validation.to_dict(), indent=2)[:1200]}"
        )

    async def _step_testing(self):
        """Phase 9: Run tests."""
        self.error_agent.reset()

        language = self.state.repo_analysis.get("language", "")
        pkg_manager = self.state.repo_analysis.get("package_manager", "")
        if "javascript" in language or "typescript" in language or pkg_manager == "npm":
            project_type = "nodejs"
        elif "go" in language:
            project_type = "go"
        elif "rust" in language:
            project_type = "rust"
        elif "java" in language:
            project_type = "java-maven" if pkg_manager == "maven" else "java-gradle"
        else:
            project_type = "python"

        test_commands = {
            "nodejs": "npm test",
            "python": "pytest . -v --tb=short -x",
            "go": "go test ./... -v",
            "rust": "cargo test",
            "java-maven": "mvn test",
            "java-gradle": "gradle test",
        }
        import glob as _glob
        import subprocess as _sp

        base_cmd = test_commands.get(project_type, "pytest . -v --tb=short")

        for attempt in range(1, self.state.max_iterations + 1):
            logger.info(f"\n🧪 Test attempt {attempt}/{self.state.max_iterations}")

            # Scope pytest to explicitly discovered test files when available;
            # otherwise fall back to `pytest .` so pytest does its own discovery
            # (avoids passing a shell glob literal on Windows that never expands).
            test_cmd = base_cmd
            if project_type == "python":
                explicit: list[str] = [
                    f
                    for f in (self.state.generated_files or [])
                    if f.endswith(".py") and "test" in f.lower()
                ]
                if not explicit:
                    # Search both workspace root and tests/ subdirectory
                    for pattern in (
                        os.path.join(self.state.workspace_path, "test_*.py"),
                        os.path.join(self.state.workspace_path, "tests", "test_*.py"),
                        os.path.join(self.state.workspace_path, "*", "test_*.py"),
                    ):
                        explicit.extend(
                            os.path.relpath(p, self.state.workspace_path)
                            for p in _glob.glob(pattern)
                        )
                if explicit:
                    test_cmd = (
                        f"pytest {' '.join(explicit)} -v --tb=short -x"
                    )
                # else: keep base_cmd = "pytest . -v --tb=short -x"

            proc = _sp.run(
                test_cmd,
                shell=True,
                cwd=self.state.workspace_path,
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = (proc.stdout or "") + (proc.stderr or "")
            passed = proc.returncode == 0

            self.state.test_results = {
                "passed": passed,
                "output": output,
                "exit_code": proc.returncode,
                "attempts": attempt,
                "command": test_cmd,
            }

            if passed:
                logger.info("✅ All tests passed!")
                return

            # Analyse the failure
            error_report = self.error_agent.analyze(output)
            self.state.healing_attempts.append(
                {
                    "attempt": attempt,
                    "error_type": error_report.type,
                    "root_cause": error_report.root_cause,
                    "affected_files": error_report.affected_files,
                    "is_repeated": error_report.is_repeated,
                }
            )
            logger.warning(
                f"\n❌ Tests failed (attempt {attempt}):\n"
                + self.error_agent.format_report(error_report)
            )

            # Loop protection — stop if identical failure repeats
            if error_report.is_repeated:
                logger.error(
                    "🔴 Autonomous Healing Failed — identical failure repeated "
                    f"{error_report.occurrence_count} times.\n"
                    "Manual Intervention Required."
                )
                raise RuntimeError(
                    f"Loop protection triggered after {attempt} attempts. "
                    f"Repeated error: {error_report.type}: {error_report.root_cause}"
                )

            if attempt < self.state.max_iterations:
                logger.info(
                    f"🔧 Applying autonomous fix (error_type={error_report.type})..."
                )
                fix_prompt = self.prompt_builder.build_fix_prompt(
                    test_output=output,
                    error_classification={
                        "type": error_report.type,
                        "root_cause": error_report.root_cause,
                        "fix_strategy": error_report.fix_strategy,
                        "affected_files": error_report.affected_files,
                    },
                    attempt=attempt,
                    max_attempts=self.state.max_iterations,
                    workspace=self.state.workspace_path,
                )
                from agent.openhands_agent import TaskContext

                await self.openhands._agent.fix_code(
                    test_output=fix_prompt,
                    error_message=error_report.root_cause,
                    context=TaskContext(repo_analysis=self.state.repo_analysis),
                )
                self.state.iteration_count = attempt

        raise RuntimeError(
            f"Tests failed after {self.state.max_iterations} attempts. "
            f"Last error: {self.state.test_results.get('output', '')[:300]}"
        )

    async def _step_healing(self):
        """Phase 10: Healing is integrated in testing loop; this records phase completion."""
        logger.info("✅ Autonomous healing phase completed within testing loop")

    async def _step_validation(self):
        """Phase 11: Validate acceptance criteria compliance."""
        logger.info("Validating acceptance criteria compliance...")

        validation = await self.acceptance_validator.validate(
            acceptance_criteria=self.state.requirement_analysis.acceptance_criteria,
            context={
                "test_results": self.state.test_results,
                "static_validation": self.state.static_validation,
                "generated_files": self.state.generated_files,
            },
        )

        # Security validation: scan for common issues in generated files
        security_issues = self._run_security_check()
        validation.security_issues = security_issues
        validation.security_passed = len(security_issues) == 0

        self.state.validation_report = validation

        if not validation.passed:
            reason = "Acceptance criteria not fully met"
            logger.warning(f"Validation warning: {reason} — continuing to create PR")
        if security_issues:
            logger.warning(f"Security issues found: {security_issues}")
        logger.info("✅ Validation complete")

    async def _step_review(self):
        """Phase 12: Review generated changes and quality score."""
        self.state.review_report = await self.review_agent.review(
            workspace=self.state.workspace_path,
            generated_files=self.state.generated_files,
            context={
                "test_results": self.state.test_results,
                "static_validation": self.state.static_validation,
            },
        )
        logger.info(
            f"✅ Review report: {json.dumps(self.state.review_report.to_dict(), indent=2)}"
        )
        if not self.state.review_report.passed:
            logger.warning(
                "Review score below threshold (<85). Triggering one targeted improvement pass."
            )
            self.state.generated_files = await self.code_agent.fix_from_test_output(
                test_results={
                    "output": "\n".join(self.state.review_report.issues),
                    "error": "Review score below threshold",
                },
                workspace=self.state.workspace_path,
                repo_analysis=self.state.repo_analysis,
            )
            self.state.review_report = await self.review_agent.review(
                workspace=self.state.workspace_path,
                generated_files=self.state.generated_files,
                context={
                    "test_results": self.state.test_results,
                    "static_validation": self.state.static_validation,
                },
            )

    def _run_security_check(self) -> list[str]:
        """Basic static security scan on generated Python files."""
        import subprocess as _sp

        issues: list[str] = []
        if not self.state.workspace_path:
            return issues
        # Only run bandit if available
        try:
            result = _sp.run(
                ["bandit", "-r", ".", "-ll", "-q", "--format", "txt"],
                cwd=self.state.workspace_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode not in (0, 1):  # 1 = issues found
                return issues
            for line in result.stdout.splitlines():
                if line.startswith(">> Issue"):
                    issues.append(line.strip())
        except (FileNotFoundError, Exception):
            pass  # bandit not installed — skip
        return issues

    async def _step_git_ops(self):
        """Step 7: Commit and push changes."""
        story_id = self.state.story_data.get("story_id", "feature")
        title = self.state.story_data.get("title", "implementation")
        commit_msg = f"[{story_id}] {title}"

        logger.info(f"Committing: {commit_msg}")
        await self.github_agent.commit_and_push(
            workspace=self.state.workspace_path,
            branch=self.state.branch_name,
            message=commit_msg,
        )
        logger.info("✅ Changes committed and pushed")

    async def _step_pr_creation(self):
        """Step 9: Create Pull Request with full context."""
        self.state.pr_url = await self.github_agent.create_pull_request(
            branch=self.state.branch_name,
            story=self.state.story_data,
            test_results=self.state.test_results,
            generated_files=self.state.generated_files,
            repo_analysis=self.state.repo_analysis,
        )
        logger.info(f"✅ Pull Request created: {self.state.pr_url}")

    # ── Execution report ─────────────────────────────────────────────────────

    def _build_execution_report(self) -> dict:
        """Build the final structured execution report."""
        started = datetime.fromisoformat(self.state.started_at)
        completed = datetime.fromisoformat(
            self.state.completed_at or datetime.now(timezone.utc).isoformat()
        )
        duration_s = (completed - started).total_seconds()

        return {
            "summary": {
                "story_id": self.state.story_data.get("story_id", "N/A"),
                "title": self.state.story_data.get("title", "N/A"),
                "status": self.state.current_step.value,
                "duration_seconds": round(duration_s, 1),
                "pr_url": self.state.pr_url,
                "branch": self.state.branch_name,
                "workspace": self.state.workspace_path,
            },
            "requirement_analysis": self.state.story_data,
            "requirements_structured": self.state.requirement_analysis.to_dict(),
            "project_context": self.state.project_context,
            "repository_analysis": self.state.repo_analysis,
            "architecture_plan": self.state.solution_design.to_dict(),
            "impact_analysis": self.state.impact_analysis.to_dict(),
            "implementation_plan": self.state.implementation_plan.to_dict(),
            "implementation_summary": {
                "files_changed": self.state.generated_files,
                "files_count": len(self.state.generated_files),
            },
            "static_validation": self.state.static_validation.to_dict(),
            "test_results": {
                "passed": self.state.test_results.get("passed", False),
                "attempts": self.state.test_results.get("attempts", 0),
                "output_tail": self.state.test_results.get("output", "")[-800:],
            },
            "healing_attempts": self.state.healing_attempts,
            "validation_report": self.state.validation_report.to_dict(),
            "review_report": self.state.review_report.to_dict(),
            "git_summary": {
                "branch": self.state.branch_name,
                "commit_message": (
                    f"[{self.state.story_data.get('story_id', '')}] "
                    f"{self.state.story_data.get('title', '')}"
                ),
            },
            "pull_request_summary": {
                "url": self.state.pr_url,
                "title": (
                    f"[{self.state.story_data.get('story_id', '')}] "
                    f"{self.state.story_data.get('title', '')}"
                ),
            },
            "errors": self.state.errors,
        }

    def _format_execution_report(self, report: dict) -> str:
        """Format the execution report for terminal display."""
        s = report["summary"]
        lines = [
            "\n" + "=" * 65,
            "  EXECUTION REPORT",
            "=" * 65,
            f"  Story    : {s['story_id']} — {s['title']}",
            f"  Status   : {s['status'].upper()}",
            f"  Duration : {s['duration_seconds']}s",
            f"  Branch   : {s['branch']}",
            f"  PR       : {s['pr_url'] or 'N/A'}",
            "-" * 65,
            f"  Files Changed : {report['implementation_summary']['files_count']}",
            f"  Tests Passed  : {report['test_results']['passed']}",
            f"  Heal Attempts : {len(report['healing_attempts'])}",
            f"  Validation    : {'PASSED' if report['validation_report'].get('passed', True) else 'WARNED'}",
            "=" * 65,
        ]
        return "\n".join(lines)
