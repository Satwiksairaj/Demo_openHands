"""
Agent module - Contains all agent implementations for the autonomous development workflow.
"""

# from agent.orchestrator import OrchestratorAgent, WorkflowState, WorkflowStep
# from agent.jira_agent import JiraAgent
# from agent.repo_agent import RepositoryAgent
# from agent.code_agent import CodeGenerationAgent
# from agent.testing_agent import TestingAgent
# from agent.github_agent import GitHubAgent
# from agent.config import AgentConfig, load_config
# from agent.prompt_builder import PromptBuilderAgent
# from agent.error_agent import ErrorAnalysisAgent, ErrorReport
# from agent import OpenHandsDevAgent

# # Optional OpenHands components
# try:
#     from agent.openhands_runtime import (
#         OpenHandsRuntime,
#         OpenHandsConfig,
#         ExecutionResult,
#     )
#     from agent.openhands_agent import (
#         OpenHandsDevAgent,
#         OpenHandsWorkflowIntegration,
#         TaskContext,
#         TaskResult,
#     )

#     OPENHANDS_AVAILABLE = True
# except ImportError:
#     OPENHANDS_AVAILABLE = False

# __all__ = [
#     "OrchestratorAgent",
#     "WorkflowState",
#     "WorkflowStep",
#     "JiraAgent",
#     "RepositoryAgent",
#     "CodeGenerationAgent",
#     "TestingAgent",
#     "GitHubAgent",
#     "AgentConfig",
#     "load_config",
#     "PromptBuilderAgent",
#     "ErrorAnalysisAgent",
#     "ErrorReport",
#     "OPENHANDS_AVAILABLE",
# ]

# if OPENHANDS_AVAILABLE:
#     __all__.extend(
#         [
#             "OpenHandsRuntime",
#             "OpenHandsConfig",
#             "ExecutionResult",
#             "OpenHandsDevAgent",
#             "OpenHandsWorkflowIntegration",
#             "TaskContext",
#             "TaskResult",
#         ]
#     )

from agent.openhands_runtime import (
    OpenHandsRuntime,
    OpenHandsConfig,
    ExecutionResult,
)

from agent.openhands_agent import (
    OpenHandsDevAgent,
    OpenHandsWorkflowIntegration,
    TaskContext,
    TaskResult,
)

OPENHANDS_AVAILABLE = True

__all__ = [
    "OpenHandsRuntime",
    "OpenHandsConfig",
    "ExecutionResult",
    "OpenHandsDevAgent",
    "OpenHandsWorkflowIntegration",
    "TaskContext",
    "TaskResult",
    "OPENHANDS_AVAILABLE",
]
