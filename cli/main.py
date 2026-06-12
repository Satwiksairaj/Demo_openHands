"""
CLI Interface for the Autonomous AI Developer Agent.
8-Step Workflow: Jira -> Repo Clone -> Analysis -> Code -> Tests -> Validate -> Git -> PR
"""

# ── Force UTF-8 output on Windows before anything else ────────────────────────
import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")

# Reconfigure stdout/stderr to UTF-8 if needed (Python 3.7+)
stdout_reconfigure = getattr(sys.stdout, "reconfigure", None)
stderr_reconfigure = getattr(sys.stderr, "reconfigure", None)
if callable(stdout_reconfigure) and callable(stderr_reconfigure):
    try:
        stdout_reconfigure(encoding="utf-8", errors="replace")
        stderr_reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich import box

# Safe console — no legacy Windows renderer, always UTF-8
console = Console(
    force_terminal=True,
    legacy_windows=False,
    highlight=False,
)

load_dotenv()


# ── Logging ───────────────────────────────────────────────────────────────────


def setup_logging(log_level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(message)s",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                markup=True,
                show_path=False,
            )
        ],
    )


# ── Config ────────────────────────────────────────────────────────────────────


def load_config() -> dict:
    """Load all configuration from environment variables / .env file."""
    return {
        "openai_api_key": os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY", ""),
        "workspace_base": os.getenv(
            "WORKSPACE_BASE", "D:/autonomous-dev-agent/workspace"
        ),
        "test_timeout": int(os.getenv("TEST_TIMEOUT", "300")),
        "jira": {
            "base_url": os.getenv("JIRA_BASE_URL", "").rstrip("/"),
            "email": os.getenv("JIRA_EMAIL", ""),
            "api_token": os.getenv("JIRA_API_TOKEN", ""),
        },
        "github": {
            "token": os.getenv("GITHUB_TOKEN", ""),
            "repo_url": os.getenv("GITHUB_REPO_URL", ""),
            "owner": os.getenv("GITHUB_OWNER", ""),
            "repo": os.getenv("GITHUB_REPO", ""),
            "base_branch": os.getenv("GITHUB_BASE_BRANCH", "main"),
        },
        "llm_model": os.getenv("LLM_MODEL", "openai/gpt-4o"),
        "llm_base_url": os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        "agent_name": os.getenv("OPENHANDS_AGENT", "CodeActAgent"),
        "sandbox_image": os.getenv(
            "SANDBOX_CONTAINER_IMAGE",
            "docker.all-hands.dev/all-hands-ai/runtime:0.30-nikolaik",
        ),
        "max_iterations": int(os.getenv("OPENHANDS_MAX_ITERATIONS", "15")),
        "max_identical_failures": int(os.getenv("MAX_IDENTICAL_FAILURES", "2")),
        "confirmation_mode": os.getenv("OPENHANDS_CONFIRMATION_MODE", "false").lower()
        == "true",
    }


def validate_config(config: dict, require_jira: bool = False) -> list[str]:
    errors: list[str] = []
    if not config.get("openai_api_key"):
        errors.append("OPENAI_API_KEY (or LLM_API_KEY) is required")
    if not config["github"].get("token"):
        errors.append("GITHUB_TOKEN is required")
    if not config["github"].get("repo_url"):
        errors.append("GITHUB_REPO_URL is required")
    if not config["github"].get("owner"):
        errors.append("GITHUB_OWNER is required")
    if not config["github"].get("repo"):
        errors.append("GITHUB_REPO is required")
    if require_jira:
        if not config["jira"].get("base_url"):
            errors.append("JIRA_BASE_URL is required")
        if not config["jira"].get("email"):
            errors.append("JIRA_EMAIL is required")
        if not config["jira"].get("api_token"):
            errors.append("JIRA_API_TOKEN is required")
    return errors


# ── UI helpers ────────────────────────────────────────────────────────────────

BANNER = """\
+---------------------------------------------------------------+
|   Autonomous AI Developer Agent  v1.0.0                       |
|                                                               |
|   Jira -> Code -> Tests -> GitHub PR  (fully autonomous)      |
+---------------------------------------------------------------+"""

STEP_LABELS = {
    "jira_fetch": "Step 1/15  Jira Story Fetch",
    "requirement_analysis": "Step 2/15  Requirement Analysis",
    "project_context": "Step 3/15  Project Context Loading",
    "repo_clone": "Step 4/15  Repository Clone",
    "repo_understanding": "Step 5/15  Repository Understanding",
    "solution_design": "Step 6/15  Solution Design",
    "impact_analysis": "Step 7/15  Impact Analysis",
    "implementation_plan": "Step 8/15  Implementation Planning",
    "code_generation": "Step 9/15  Code Generation",
    "static_validation": "Step 10/15  Static Validation",
    "testing": "Step 11/15  Testing",
    "healing": "Step 12/15  Autonomous Healing",
    "acceptance_validation": "Step 13/15  Acceptance Validation",
    "review": "Step 14/15  Code Review",
    "git_ops": "Step 15/15  Git Commit & Push",
    "complete": "DONE",
    "failed": "FAILED",
}


def print_banner() -> None:
    console.print(BANNER, style="bold cyan")
    console.print()


def print_results(state) -> None:
    """Render final workflow results as a Rich table."""
    story = state.story_data
    passed = state.test_results.get("passed", False)

    table = Table(box=box.SIMPLE_HEAVY, show_header=False)
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    table.add_row("Story ID", story.get("story_id", "N/A"))
    table.add_row("Title", story.get("title", "N/A"))
    table.add_row("Branch", state.branch_name or "N/A")
    table.add_row("Tests", "[green]PASSED[/green]" if passed else "[red]FAILED[/red]")
    table.add_row("Files Changed", str(len(state.generated_files)))
    table.add_row("PR URL", state.pr_url or "N/A")
    table.add_row("Retries", str(state.iteration_count))

    status_val = state.current_step.value
    color = "green" if status_val == "complete" else "red"
    table.add_row("Status", f"[{color}]{status_val.upper()}[/{color}]")

    if state.started_at and state.completed_at:
        started = datetime.fromisoformat(state.started_at)
        completed = datetime.fromisoformat(state.completed_at)
        secs = (completed - started).total_seconds()
        table.add_row("Duration", f"{secs:.1f}s")

    border = "green" if status_val == "complete" else "red"
    console.print(Panel(table, title="[bold]Workflow Results", border_style=border))


# ── CLI Commands ──────────────────────────────────────────────────────────────


@click.group()
@click.option(
    "--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)"
)
@click.pass_context
def cli(ctx, log_level):
    """Autonomous AI Developer Agent

    Reads from Jira or a natural-language prompt, generates code in an
    isolated workspace, runs tests, and opens a GitHub Pull Request.
    """
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level
    setup_logging(log_level)


@cli.command()
@click.option(
    "--story",
    "-s",
    default=None,
    metavar="STORY_ID",
    help="Jira story ID  (e.g. IGN-245)",
)
@click.option(
    "--prompt",
    "-p",
    default=None,
    metavar="TEXT",
    help='Natural-language task  (e.g. "Add JWT auth")',
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Analyse only — do not write code or create PR",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Save JSON results to this file",
)
@click.pass_context
def run(ctx, story, prompt, dry_run, output):
    """Run the autonomous 8-step development workflow.

    \b
    Examples:
      agent run --story IGN-245
      agent run --prompt "Add a login rate limiter to the API"
      agent run -> story IGN-245
      agent run -> prompt "Add JWT auth"
    """
    print_banner()

    if not story and not prompt:
        console.print("[red]ERROR: provide --story STORY_ID or --prompt TEXT[/red]")
        sys.exit(1)

    config = load_config()
    require_jira = bool(story)
    errors = validate_config(config, require_jira=require_jira)
    if errors:
        console.print("[bold red]Configuration errors:[/bold red]")
        for e in errors:
            console.print(f"  [red]x[/red] {e}")
        console.print()
        console.print(
            "[yellow]Add the missing values to your .env file and retry.[/yellow]"
        )
        sys.exit(1)

    if story:
        console.print(f"[bold]Jira Story:[/bold] [cyan]{story}[/cyan]")
    else:
        console.print(f"[bold]Prompt:[/bold] [cyan]{prompt}[/cyan]")

    if dry_run:
        console.print("[yellow]Dry-run mode: analysis only, no code changes.[/yellow]")

    console.print()

    # ── run the 8-step workflow ───────────────────────────────────────────────
    async def _run():
        from agent.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent(config, strict_mode=True)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        ) as progress:
            task_id = progress.add_task(STEP_LABELS["jira_fetch"], total=None)

            # Patch the orchestrator to update the spinner label per step
            original_run = orch.run

            async def run_with_progress(**kwargs):

                async def step_hook(step_enum):
                    label = STEP_LABELS.get(step_enum.value, step_enum.value)
                    progress.update(task_id, description=label)

                # Intercept each step transition
                # orig_steps = orch.__class__._step_jira_fetch

                state = await original_run(**kwargs)
                progress.update(
                    task_id,
                    description=STEP_LABELS.get(state.current_step.value, "Done"),
                )
                return state

            return await run_with_progress(
                story_id=story,
                prompt=prompt,
            )

    try:
        state = asyncio.run(_run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Workflow interrupted.[/yellow]")
        sys.exit(130)
    except Exception as exc:
        console.print(f"\n[bold red]Workflow failed:[/bold red] {exc}")
        logging.exception("Workflow error")
        sys.exit(1)

    console.print()
    print_results(state)

    if state.errors:
        console.print("\n[bold red]Errors encountered:[/bold red]")
        for err in state.errors:
            console.print(f"  [{err['step']}] {err['error']}")

    if output:
        payload = {
            "story_id": state.story_id,
            "story_data": state.story_data,
            "branch": state.branch_name,
            "pr_url": state.pr_url,
            "files": state.generated_files,
            "test_results": state.test_results,
            "status": state.current_step.value,
            "errors": state.errors,
            "started_at": state.started_at,
            "completed_at": state.completed_at,
        }
        Path(output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        console.print(f"\n[green]Results saved -> {output}[/green]")

    sys.exit(0 if state.current_step.value == "complete" else 1)


@cli.command()
def config():
    """Show current configuration status."""
    print_banner()
    cfg = load_config()

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold")
    table.add_column("Variable", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Value", style="dim")

    checks = [
        ("OPENAI_API_KEY", cfg.get("openai_api_key")),
        ("JIRA_BASE_URL", cfg["jira"].get("base_url")),
        ("JIRA_EMAIL", cfg["jira"].get("email")),
        ("JIRA_API_TOKEN", cfg["jira"].get("api_token")),
        ("GITHUB_TOKEN", cfg["github"].get("token")),
        ("GITHUB_REPO_URL", cfg["github"].get("repo_url")),
        ("GITHUB_OWNER", cfg["github"].get("owner")),
        ("GITHUB_REPO", cfg["github"].get("repo")),
        ("GITHUB_BASE_BRANCH", cfg["github"].get("base_branch")),
    ]

    for name, value in checks:
        if value:
            masked = value[:4] + "***" if len(value) > 4 else "***"
            table.add_row(name, "[green]Set[/green]", masked)
        else:
            table.add_row(name, "[red]Missing[/red]", "")

    console.print(Panel(table, title="[bold]Configuration Status", border_style="cyan"))


@cli.command()
@click.argument("story_id")
def fetch(story_id):
    """Fetch and display a Jira story (Step 1 only)."""
    print_banner()
    cfg = load_config()

    errors = validate_config(cfg, require_jira=True)
    if errors:
        for e in errors:
            console.print(f"[red]x {e}[/red]")
        sys.exit(1)

    async def _fetch():
        from agent.jira_agent import JiraAgent

        return await JiraAgent(cfg).fetch_story(story_id)

    with console.status(f"Fetching {story_id} ..."):
        story = asyncio.run(_fetch())

    console.print_json(json.dumps(story, indent=2))


@cli.command()
def version():
    """Show version information."""
    console.print("AI Dev Agent v1.0.0")
    console.print("Powered by OpenHands SDK + OpenAI GPT-4o")


@cli.command()
def context():
    """Show active project context."""

    from app.services.project_context_manager import ProjectContextManager

    cfg = load_config()

    mgr = ProjectContextManager(cfg["workspace_base"] + "/workspace")

    ctx = mgr.get_active_project()

    if not ctx:
        console.print("[yellow]No active project context found[/yellow]")
        return

    console.print_json(data=ctx.__dict__)


@cli.command(name="projects")
def list_projects():
    """List all projects in registry."""

    from app.services.project_context_manager import ProjectContextManager

    cfg = load_config()

    mgr = ProjectContextManager(cfg["workspace_base"] + "/workspace")

    projects = mgr.list_projects()

    if not projects:
        console.print("[yellow]No projects found[/yellow]")
        return

    console.print_json(data=projects)


# ── Entry point ───────────────────────────────────────────────────────────────


def main():
    """
    Entry point — also supports the arrow syntax:
      agent run -> story IGN-245
      agent run -> prompt "Add JWT auth"
    """
    args = sys.argv[1:]

    # Translate:  agent run -> story IGN-245
    #         to: agent run --story IGN-245
    if len(args) >= 3 and args[0] == "run" and args[1] == "->":
        mode = args[2].lower()  # "story" or "prompt"
        value = " ".join(args[3:]) if len(args) > 3 else ""
        if mode == "story":
            sys.argv = [sys.argv[0], "run", "--story", value]
        elif mode == "prompt":
            sys.argv = [sys.argv[0], "run", "--prompt", value]

    cli(obj={})


if __name__ == "__main__":
    main()
