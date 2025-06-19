FROM python:3.12-slim

LABEL maintainer="team@monadical.com"
LABEL description="Claude Code with MCP servers for Cubbi"

# Install system dependencies including gosu for user switching, shadow for useradd/groupadd,
# git, ripgrep, and tmux
RUN apt-get update && apt-get install -y --no-install-recommends \
    gosu \
    passwd \
    bash \
    curl \
    bzip2 \
    iputils-ping \
    iproute2 \
    libxcb1 \
    libdbus-1-3 \
    nano \
    vim \
    git \
    ripgrep \
    tmux \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (for Claude Code)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install deps
WORKDIR /tmp
RUN curl -fsSL https://astral.sh/uv/install.sh -o install.sh && \
    sh install.sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx && \
    rm install.sh

# Install Claude Code
RUN npm install -g @anthropic-ai/claude-code --force --no-os-check

# Create app directory
WORKDIR /app

# Copy initialization system
COPY cubbi_init.py /cubbi/cubbi_init.py
COPY claude_code_plugin.py /cubbi/claude_code_plugin.py
COPY cubbi_image.yaml /cubbi/cubbi_image.yaml
COPY init-status.sh /cubbi/init-status.sh
RUN chmod +x /cubbi/cubbi_init.py /cubbi/init-status.sh
RUN echo '[ -x /cubbi/init-status.sh ] && /cubbi/init-status.sh' >> /etc/bash.bashrc

# Set up environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_LINK_MODE=copy
ENV CLAUDE_CODE_USE_BEDROCK=1
ENV ANTHROPIC_MODEL='us.anthropic.claude-sonnet-4-20250514-v1:0'


# Pre-install the cubbi_init
RUN /cubbi/cubbi_init.py --help

# Set WORKDIR to /app, common practice and expected by cubbi-init.sh
WORKDIR /app

ENTRYPOINT ["/cubbi/cubbi_init.py"]
CMD ["tail", "-f", "/dev/null"]
