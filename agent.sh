#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# AI Developer Agent - Runner Script
#
# Usage:
#   ./agent.sh run -> story IGN-245
#   ./agent.sh run -> prompt "Add JWT auth feature"
#   ./agent.sh config
#   ./agent.sh fetch IGN-245
#
# With Docker:
#   USE_DOCKER=1 ./agent.sh run -> story IGN-245
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USE_DOCKER="${USE_DOCKER:-0}"

# Load .env if it exists
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

# ─── Docker mode ──────────────────────────────────────────────────────────────
if [[ "$USE_DOCKER" == "1" ]]; then
    echo "🐳 Running in Docker sandbox..."

    # Build image if needed
    if ! docker image inspect ai-dev-agent:latest &>/dev/null; then
        echo "Building Docker image..."
        docker build -t ai-dev-agent:latest -f "$SCRIPT_DIR/sandbox/Dockerfile" "$SCRIPT_DIR"
    fi

    docker run --rm -it \
        -e OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
        -e JIRA_BASE_URL="${JIRA_BASE_URL:-}" \
        -e JIRA_EMAIL="${JIRA_EMAIL:-}" \
        -e JIRA_API_TOKEN="${JIRA_API_TOKEN:-}" \
        -e GITHUB_TOKEN="${GITHUB_TOKEN:-}" \
        -e GITHUB_REPO_URL="${GITHUB_REPO_URL:-}" \
        -e GITHUB_OWNER="${GITHUB_OWNER:-}" \
        -e GITHUB_REPO="${GITHUB_REPO:-}" \
        -e GITHUB_BASE_BRANCH="${GITHUB_BASE_BRANCH:-main}" \
        -e WORKSPACE_BASE="/workspace" \
        -e TEST_TIMEOUT="${TEST_TIMEOUT:-300}" \
        -e LOG_LEVEL="${LOG_LEVEL:-INFO}" \
        -v agent-workspace:/workspace \
        ai-dev-agent:latest \
        "$@"
    exit $?
fi

# ─── Local mode ───────────────────────────────────────────────────────────────
# Check Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 is required. Install from https://python.org"
    exit 1
fi

# Create virtualenv if needed
VENV_DIR="$SCRIPT_DIR/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --quiet --upgrade pip
    pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
    pip install --quiet -e "$SCRIPT_DIR"
    echo "✅ Environment ready"
else
    source "$VENV_DIR/bin/activate"
fi

# Run the agent
python3 -m cli.main "$@"
