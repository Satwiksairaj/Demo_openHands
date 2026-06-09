FROM ubuntu:22.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ─── System dependencies ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build tools
    build-essential \
    curl \
    wget \
    git \
    unzip \
    # Python
    python3.11 \
    python3.11-dev \
    python3-pip \
    python3.11-venv \
    # Node.js (via NodeSource)
    ca-certificates \
    gnupg \
    # Java
    default-jdk \
    maven \
    # Go
    golang-go \
    # Rust (installed via rustup later)
    # Other utils
    jq \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# ─── Node.js 20 ───────────────────────────────────────────────────────────────
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest typescript ts-node

# ─── Rust ─────────────────────────────────────────────────────────────────────
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --default-toolchain stable
ENV PATH="/root/.cargo/bin:${PATH}"

# ─── Python alias ─────────────────────────────────────────────────────────────
RUN ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.11 /usr/bin/python

# ─── Python tools ─────────────────────────────────────────────────────────────
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel \
    && pip3 install --no-cache-dir \
    ruff \
    mypy \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    isort

# ─── Git config ───────────────────────────────────────────────────────────────
RUN git config --global user.email "ai-agent@autonomous.dev" \
    && git config --global user.name "AI Dev Agent" \
    && git config --global init.defaultBranch main \
    && git config --global safe.directory '*'

# ─── App setup ────────────────────────────────────────────────────────────────
WORKDIR /app

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy agent code
COPY . .

# Install agent package
RUN pip3 install -e .

# ─── Workspace directory ──────────────────────────────────────────────────────
RUN mkdir -p /workspace && chmod 777 /workspace

# ─── Security hardening ───────────────────────────────────────────────────────
# Run as non-root for isolation
RUN useradd -m -u 1000 agent && \
    chown -R agent:agent /app /workspace
USER agent

# ─── Entrypoint ───────────────────────────────────────────────────────────────
ENTRYPOINT ["python3", "-m", "cli.main"]
CMD ["--help"]
