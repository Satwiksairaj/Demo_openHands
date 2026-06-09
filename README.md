# 🤖 Autonomous AI Developer Agent

> **Jira → Code → Tests → GitHub PR — fully autonomous**

An autonomous AI agent that acts as a software developer: reads Jira stories, understands your codebase, generates production-ready code, runs tests, fixes failures, and creates Pull Requests — all without human intervention.

**Now powered by [OpenHands](https://github.com/All-Hands-AI/OpenHands) SDK** for sandboxed, secure code execution.

---

## Architecture

### Traditional Mode (LangChain)

```text
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                           │
│                 (Controls full workflow)                        │
└──────┬──────────┬──────────┬──────────┬──────────┬─────────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
  │ Jira   │ │  Repo  │ │  Code  │ │Testing │ │GitHub  │
  │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │
  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
  Jira REST   git clone  GPT-4o    npm/pytest  GitHub API
  API v3      & analyze  LangChain  Go/Maven   + GitPython
```

### OpenHands Mode (Recommended)

```text
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                           │
│              (OpenHands Workflow Integration)                   │
└──────┬──────────┬──────────────────────────────┬───────────────┘
       │          │                              │
       ▼          ▼                              ▼
  ┌────────┐ ┌────────┐                    ┌────────────┐
  │ Jira   │ │  Repo  │                    │  GitHub    │
  │ Agent  │ │ Agent  │                    │  Agent     │
  └────────┘ └────────┘                    └────────────┘
                │
                ▼
    ┌───────────────────────────────────────────┐
    │         OpenHands Runtime (Docker)        │
    │  ┌─────────────┐  ┌─────────────────────┐ │
    │  │CodeActAgent │  │ Sandboxed Execution │ │
    │  │  (GPT-4o)   │→ │ - File operations   │ │
    │  │             │  │ - Test execution    │ │
    │  │             │  │ - Code generation   │ │
    │  └─────────────┘  └─────────────────────┘ │
    └───────────────────────────────────────────┘
```

### MCP Integration

```text
┌─────────────────┐     stdio     ┌──────────────────┐
│  LangChain      │◄─────────────►│  MCP Server      │
│  Agent Tools    │               │  - jira_*        │
└─────────────────┘               │  - github_*      │
                                  └──────────────────┘
```

---

## Workflow

```text
Input (Story ID or Prompt)
         │
         ▼
 ┌───────────────┐
 │ 1. Jira Fetch │  → Structured requirements JSON
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │ 2. Repo Clone │  → git clone + git checkout -b feature/STORY-ID
 └───────┬───────┘
         ▼
 ┌────────────────┐
 │ 3. Repo        │  → Framework, patterns, style, relevant files
 │    Analysis    │
 └───────┬────────┘
         ▼
 ┌────────────────┐
 │ 4. Code        │  → Generate/modify files following conventions
 │    Generation  │
 └───────┬────────┘
         ▼
 ┌───────────────┐
 │ 5. Testing    │  → npm test / pytest / go test / cargo test
 │   ┌─────────┐ │
 │   │ FAIL?   │─┼──► Auto-fix & retry (up to 3x)
 │   └─────────┘ │
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │ 6. Validation │  → Acceptance criteria verified by LLM
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │ 7. Git Ops    │  → git add . && git commit && git push
 └───────┬───────┘
         ▼
 ┌───────────────┐
 │ 8. PR Create  │  → Rich PR with test results & summary
 └───────────────┘
```

---

## Architecture Flow

The runtime execution flow is:

1. The user starts the system through `agent run`, `python -m app`, or a natural-language prompt.
2. `cli/main.py` loads environment configuration, validates required credentials, and starts the orchestrator.
3. `agent/orchestrator.py` initializes workflow state and executes each step in sequence.
4. `agent/jira_agent.py` fetches a Jira story or transforms a prompt into structured requirements.
5. `agent/repo_agent.py` clones the target repository, creates a feature branch, and analyzes the codebase.
6. `agent/prompt_builder.py` builds solution-design and implementation prompts using repo context.
7. `agent/openhands_agent.py`, `agent/openhands_runtime.py`, and `agent/code_agent.py` perform code generation and code fixing inside the workspace.
8. `agent/testing_agent.py` runs the appropriate install, lint, build, and test commands for the detected stack.
9. `agent/error_agent.py` classifies failures and supports the self-healing retry loop when tests fail.
10. `agent/github_agent.py` stages, commits, pushes, and creates the GitHub pull request.
11. The orchestrator returns a final execution report with status, changed files, test results, and PR details.

This flow matters because the project is not a single LLM prompt. It is a controlled software-delivery pipeline with planning, implementation, validation, and release stages.

---

## Repository Structure

### Top-Level Structure

```text
autonomous-dev-agent/
|-- agent/
|-- app/
|-- cli/
|-- mcp/
|-- sandbox/
|-- tests/
|-- workspace/
|-- README.md
|-- pyproject.toml
|-- requirements.txt
`-- agent.sh
```

### What Each Folder Does

- `agent/`: core autonomous workflow logic and all specialized agents.
- `app/`: Python module entry points such as `python -m app`.
- `cli/`: command-line interface and terminal output handling.
- `mcp/`: MCP server exposing Jira and GitHub tools.
- `sandbox/`: Docker runtime and deployment configuration.
- `tests/`: unit tests for orchestration and agent behavior.
- `workspace/`: generated or cloned target projects where implementation happens.

### Important Files And Responsibilities

- `agent/orchestrator.py`: master controller for the full workflow.
- `agent/jira_agent.py`: requirement extraction from Jira stories or prompts.
- `agent/repo_agent.py`: repository cloning, branching, and structural analysis.
- `agent/code_agent.py`: orchestrator-facing code generation interface.
- `agent/openhands_agent.py`: OpenHands workflow integration for coding and fixing.
- `agent/openhands_runtime.py`: runtime wrapper for sandbox task execution.
- `agent/testing_agent.py`: multi-language test, lint, and build execution.
- `agent/error_agent.py`: failure classification and retry-loop protection.
- `agent/github_agent.py`: git operations and pull request creation.
- `agent/prompt_builder.py`: context-aware prompt generation.
- `agent/config.py`: configuration dataclasses and validation.
- `cli/main.py`: main CLI entry point and workflow launcher.
- `app/main.py`: Python module startup path forwarding to the CLI.
- `mcp/server.py`: MCP tool server for Jira and GitHub integrations.
- `sandbox/Dockerfile`: multi-runtime container image definition.
- `sandbox/docker-compose.yml`: service orchestration for containerized runs.
- `tests/test_agents.py`: regression coverage for key workflow components.

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Git
- Docker (required for OpenHands mode, optional otherwise)

### 2. Setup

```bash
git clone <this-repo>
cd ai-dev-agent

# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### 3. Run

```bash
# With OpenHands (recommended - sandboxed execution)
agent run --story IGN-245 --openhands
agent run --prompt "Add JWT authentication" --openhands

# Or set USE_OPENHANDS=true in .env and run normally
agent run --story IGN-245

# Traditional mode (without OpenHands)
USE_OPENHANDS=false agent run --story IGN-245

# Via Docker (fully isolated)
USE_DOCKER=1 ./agent.sh run -> story IGN-245
```

---

## OpenHands Integration

This agent supports [OpenHands](https://github.com/All-Hands-AI/OpenHands), an open-source platform for AI software developers.

### Benefits of OpenHands Mode

- **Sandboxed Execution**: All code runs in isolated Docker containers
- **CodeActAgent**: Uses OpenHands' powerful code generation agent
- **Self-Healing**: Automatic error detection and fix attempts
- **Multi-Runtime**: Supports Python, Node.js, Go, Java, Rust out of the box

### Configuration

```bash
# .env configuration for OpenHands
USE_OPENHANDS=true
LLM_MODEL=openai/gpt-4o
LLM_API_KEY=sk-...
OPENHANDS_AGENT=CodeActAgent
SANDBOX_CONTAINER_IMAGE=docker.all-hands.dev/all-hands-ai/runtime:0.30-nikolaik
OPENHANDS_MAX_ITERATIONS=50
```

### CLI Usage

```bash
# Enable OpenHands via flag
agent run --prompt "Add rate limiting" --openhands

# Or via environment
USE_OPENHANDS=true agent run --story IGN-245
```

---

## CLI Reference

```bash
# Check configuration
agent config

# Fetch a Jira story (preview only)
agent fetch IGN-245

# Run full workflow from Jira story
agent run --story IGN-245

# Run from natural language prompt
agent run --prompt "Add rate limiting to all API endpoints"

# Save results to file
agent run --story IGN-245 --output results.json

# With logging
agent --log-level DEBUG run --story IGN-245
```

### Arrow syntax (alternative)

```bash
agent run -> story IGN-245
agent run -> prompt "Add caching layer"
```

---

## Environment Variables

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `OPENAI_API_KEY` | ✅ | OpenAI API key (GPT-4o) |
| `JIRA_BASE_URL` | ✅* | Jira instance URL |
| `JIRA_EMAIL` | ✅* | Atlassian account email |
| `JIRA_API_TOKEN` | ✅* | Jira API token |
| `GITHUB_TOKEN` | ✅ | GitHub Personal Access Token |
| `GITHUB_REPO_URL` | ✅ | Repository clone URL |
| `GITHUB_OWNER` | ✅ | Repository owner |
| `GITHUB_REPO` | ✅ | Repository name |
| `GITHUB_BASE_BRANCH` | — | PR base branch (default: `main`) |
| `TEST_TIMEOUT` | — | Test timeout in seconds (default: 300) |
| `MAX_RETRIES` | — | Max test fix iterations (default: 3) |

*Required only when using Jira story IDs (not needed for `--prompt`)

---

## Supported Project Types

| Language | Detection | Install | Test |
| -------- | --------- | ------- | ---- |
| Node.js | `package.json` | `npm install` | `npm test` |
| Python | `requirements.txt` / `pyproject.toml` | `pip install` | `pytest` |
| Go | `go.mod` | `go mod tidy` | `go test ./...` |
| Java (Maven) | `pom.xml` | — | `mvn test` |
| Java (Gradle) | `build.gradle` | — | `gradle test` |
| Rust | `Cargo.toml` | — | `cargo test` |

---

## MCP Server

The MCP server exposes Jira and GitHub as tools for LangChain agents:

```bash
# Start MCP server (stdio transport)
python3 -m mcp.server

# Available tools:
# - jira_get_story
# - jira_add_comment
# - jira_update_status
# - github_create_pr
# - github_get_repo_info
# - github_list_files
# - github_get_file
```

---

## Docker Sandbox

```bash
# Build the sandbox image
docker build -t ai-dev-agent:latest -f sandbox/Dockerfile .

# Run with Docker Compose
docker compose -f sandbox/docker-compose.yml run agent run --story IGN-245

# Or use the helper script
USE_DOCKER=1 ./agent.sh run -> story IGN-245
```

The sandbox provides:

- Isolated filesystem and network
- All language runtimes (Node.js 20, Python 3.11, Go, Java, Rust)
- Resource limits (4GB RAM, 2 CPUs)
- Security hardening (no-new-privileges, dropped capabilities)

---

## Project Structure

```text
ai-dev-agent/
├── agent/
│   ├── orchestrator.py     # Master workflow controller
│   ├── jira_agent.py       # Jira integration + requirement parsing
│   ├── repo_agent.py       # Repository cloning + analysis
│   ├── code_agent.py       # LLM code generation + fixing
│   ├── testing_agent.py    # Multi-language test runner
│   └── github_agent.py     # Git operations + PR creation
├── mcp/
│   └── server.py           # MCP server (Jira + GitHub tools)
├── cli/
│   └── main.py             # Rich CLI interface
├── sandbox/
│   ├── Dockerfile          # Multi-runtime container
│   └── docker-compose.yml  # Sandbox orchestration
├── tests/
│   └── test_agents.py      # Unit tests
├── agent.sh                # Runner shell script
├── .env.example            # Environment template
└── requirements.txt        # Python dependencies
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## License

MIT
