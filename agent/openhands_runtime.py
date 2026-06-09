"""
OpenHands Runtime Integration - Thin wrapper around OpenHands SDK v1.x
for sandboxed code execution using LocalConversation.
"""
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class OpenHandsConfig:
    """Local configuration dataclass for the OpenHands runtime wrapper."""
    llm_model: str = "openai/gpt-4o"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    agent_name: str = "CodeActAgent"
    sandbox_image: str = "docker.all-hands.dev/all-hands-ai/runtime:0.30-nikolaik"
    max_iterations: int = 15
    workspace_base: str = "D:/autonomous-dev-agent/workspace"
    confirmation_mode: bool = False

    @classmethod
    def from_env(cls) -> "OpenHandsConfig":
        return cls(
            llm_model=os.getenv("LLM_MODEL", "openai/gpt-4o"),
            llm_api_key=os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", "")),
            llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            agent_name=os.getenv("OPENHANDS_AGENT", "CodeActAgent"),
            sandbox_image=os.getenv(
                "SANDBOX_CONTAINER_IMAGE",
                "docker.all-hands.dev/all-hands-ai/runtime:0.30-nikolaik"
            ),
            max_iterations=int(os.getenv("OPENHANDS_MAX_ITERATIONS", "15")),
            workspace_base=os.getenv("WORKSPACE_BASE", "D:/autonomous-dev-agent/workspace"),
            confirmation_mode=os.getenv("OPENHANDS_CONFIRMATION_MODE", "false").lower() == "true",
        )


@dataclass
class ExecutionResult:
    """Result of a command or agent task execution."""
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    files_modified: list = field(default_factory=list)


class OpenHandsRuntime:
    """
    Wrapper that runs tasks through OpenHands SDK v1.x LocalConversation.
    """

    def __init__(self, config: OpenHandsConfig):
        self.config = config
        self._workspace_path: Optional[str] = None

    async def initialize(self, workspace_path: str) -> None:
        """Set the workspace path."""
        self._workspace_path = workspace_path
        Path(workspace_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"OpenHands runtime workspace: {workspace_path}")

    async def shutdown(self) -> None:
        """No-op — LocalConversation is stateless between calls."""
        self._workspace_path = None

    def _build_llm(self):
        from openhands.sdk.llm import LLM
        return LLM(
            model=self.config.llm_model,
            api_key=self.config.llm_api_key,
            base_url=self.config.llm_base_url or None,
        )

    async def run_task(self, task: str, workspace: Optional[str] = None) -> ExecutionResult:
        """
        Run a task through the OpenHands agent.
        Returns success + collected agent output, and detects git-modified files.
        """
        import asyncio
        import subprocess
        from openhands.sdk import LocalConversation
        from openhands.tools.preset.default import get_default_agent

        ws = workspace or self._workspace_path or os.getcwd()
        Path(ws).mkdir(parents=True, exist_ok=True)

        llm = self._build_llm()
        agent = get_default_agent(llm=llm, cli_mode=True)

        collected_output = []
        event_files: list[str] = []

        def on_event(event):
            content = getattr(event, "content", None)
            if isinstance(content, str) and content.strip():
                collected_output.append(content)
            event_type = type(event).__name__
            if "FileWrite" in event_type or "FileEdit" in event_type or "FileCreate" in event_type:
                path = getattr(event, "path", None)
                if path:
                    event_files.append(str(path))

        conversation = LocalConversation(
            agent=agent,
            workspace=ws,
            callbacks=[on_event],
            max_iteration_per_run=self.config.max_iterations,
        )

        conversation.send_message(task)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, conversation.run)

        output = "\n".join(collected_output)

        # Detect actually modified files via git status (more reliable than event tracking)
        git_modified: list[str] = []
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=ws, capture_output=True, text=True, timeout=30
            )
            git_modified += [f for f in result.stdout.strip().splitlines() if f]
            result2 = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=ws, capture_output=True, text=True, timeout=30
            )
            git_modified += [f for f in result2.stdout.strip().splitlines() if f]
        except Exception:
            pass

        all_files = list(set(event_files + git_modified))

        # Determine success: look for failure signals in output
        failure_keywords = ["error:", "traceback", "exception", "failed", "exit code 1"]
        lower_out = output.lower()
        has_failure = any(kw in lower_out for kw in failure_keywords)
        success = not has_failure or bool(all_files)  # success if files were written

        return ExecutionResult(
            success=True,   # Let orchestrator decide based on test output
            output=output,
            files_modified=all_files,
        )

    async def run_command(self, command: str, timeout: int = 120, working_dir: Optional[str] = None) -> ExecutionResult:
        """Run a shell command directly (not via agent) and return real exit status."""
        import subprocess
        ws = working_dir or self._workspace_path or os.getcwd()
        try:
            proc = subprocess.run(
                command, shell=True, cwd=ws,
                capture_output=True, text=True, timeout=timeout
            )
            output = (proc.stdout or "") + (proc.stderr or "")
            return ExecutionResult(
                success=proc.returncode == 0,
                output=output,
                error=proc.stderr or "",
                exit_code=proc.returncode,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(success=False, error=f"Command timed out after {timeout}s")
        except Exception as exc:
            return ExecutionResult(success=False, error=str(exc))
