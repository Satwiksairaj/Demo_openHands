"""
Configuration management for the AI Developer Agent.
Supports both traditional LangChain and OpenHands SDK modes.
"""
import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class JiraConfig:
    """Jira integration configuration."""
    base_url: str = ""
    email: str = ""
    api_token: str = ""

    @classmethod
    def from_env(cls) -> "JiraConfig":
        return cls(
            base_url=os.getenv("JIRA_BASE_URL", ""),
            email=os.getenv("JIRA_EMAIL", ""),
            api_token=os.getenv("JIRA_API_TOKEN", ""),
        )


@dataclass
class GitHubConfig:
    """GitHub integration configuration."""
    token: str = ""
    repo_url: str = ""
    owner: str = ""
    repo: str = ""
    base_branch: str = "main"

    @classmethod
    def from_env(cls) -> "GitHubConfig":
        return cls(
            token=os.getenv("GITHUB_TOKEN", ""),
            repo_url=os.getenv("GITHUB_REPO_URL", ""),
            owner=os.getenv("GITHUB_OWNER", ""),
            repo=os.getenv("GITHUB_REPO", ""),
            base_branch=os.getenv("GITHUB_BASE_BRANCH", "main"),
        )


@dataclass
class OpenHandsConfig:
    """OpenHands SDK configuration."""
    enabled: bool = False
    llm_model: str = "openai/gpt-4o"
    llm_base_url: str = "https://api.openai.com/v1"
    agent_name: str = "CodeActAgent"
    sandbox_type: str = "docker"
    sandbox_image: str = "docker.all-hands.dev/all-hands-ai/runtime:0.30-nikolaik"
    max_iterations: int = 50
    confirmation_mode: bool = False

    @classmethod
    def from_env(cls) -> "OpenHandsConfig":
        return cls(
            enabled=os.getenv("USE_OPENHANDS", "false").lower() == "true",
            llm_model=os.getenv("LLM_MODEL", "openai/gpt-4o"),
            llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            agent_name=os.getenv("OPENHANDS_AGENT", "CodeActAgent"),
            sandbox_type=os.getenv("SANDBOX_TYPE", "docker"),
            sandbox_image=os.getenv(
                "SANDBOX_CONTAINER_IMAGE",
                "docker.all-hands.dev/all-hands-ai/runtime:0.30-nikolaik"
            ),
            max_iterations=int(os.getenv("OPENHANDS_MAX_ITERATIONS", "50")),
            confirmation_mode=os.getenv("OPENHANDS_CONFIRMATION_MODE", "false").lower() == "true",
        )


@dataclass
class AgentConfig:
    """Main agent configuration."""
    openai_api_key: str = ""
    workspace_base: str = "/tmp/agent-workspaces"
    test_timeout: int = 300
    max_retries: int = 3
    log_level: str = "INFO"
    use_docker: bool = False
    
    # Sub-configurations
    jira: JiraConfig = field(default_factory=JiraConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    openhands: OpenHandsConfig = field(default_factory=OpenHandsConfig)

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load full configuration from environment variables."""
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            workspace_base=os.getenv("WORKSPACE_BASE", "/tmp/agent-workspaces"),
            test_timeout=int(os.getenv("TEST_TIMEOUT", "300")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            use_docker=os.getenv("USE_DOCKER", "false").lower() == "true",
            jira=JiraConfig.from_env(),
            github=GitHubConfig.from_env(),
            openhands=OpenHandsConfig.from_env(),
        )

    def to_dict(self) -> dict:
        """Convert configuration to dictionary for agent initialization."""
        return {
            "openai_api_key": self.openai_api_key,
            "workspace_base": self.workspace_base,
            "test_timeout": self.test_timeout,
            "max_retries": self.max_retries,
            
            # Jira config
            "jira": {
                "base_url": self.jira.base_url,
                "email": self.jira.email,
                "api_token": self.jira.api_token,
            },
            
            # GitHub config
            "github": {
                "token": self.github.token,
                "repo_url": self.github.repo_url,
                "owner": self.github.owner,
                "repo": self.github.repo,
                "base_branch": self.github.base_branch,
            },
            
            # OpenHands config (when enabled)
            "llm_model": self.openhands.llm_model,
            "llm_base_url": self.openhands.llm_base_url,
            "agent_name": self.openhands.agent_name,
            "sandbox_type": self.openhands.sandbox_type,
            "sandbox_image": self.openhands.sandbox_image,
            "max_iterations": self.openhands.max_iterations,
            "confirmation_mode": self.openhands.confirmation_mode,
        }

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required")
        
        if not self.github.token:
            errors.append("GITHUB_TOKEN is required")
        
        if not self.github.repo_url:
            errors.append("GITHUB_REPO_URL is required")
        
        return errors


def load_config() -> AgentConfig:
    """Load and validate configuration."""
    config = AgentConfig.from_env()
    errors = config.validate()
    
    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
    
    return config
