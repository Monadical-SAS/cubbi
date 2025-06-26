FROM node:20-slim

LABEL maintainer="team@monadical.com"
LABEL description="Google Gemini CLI for Cubbi"

# Install system dependencies including gosu for user switching
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
    tmux \
    git-core \
    ripgrep \
    openssh-client \
    vim \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager) for cubbi_init.py compatibility
WORKDIR /tmp
RUN curl -fsSL https://astral.sh/uv/install.sh -o install.sh && \
    sh install.sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx && \
    rm install.sh

# Install Gemini CLI globally
RUN npm install -g @google/gemini-cli

# Verify installation
RUN gemini --version

# Create app directory
WORKDIR /app

# Copy initialization system
COPY cubbi_init.py /cubbi/cubbi_init.py
COPY gemini_cli_plugin.py /cubbi/gemini_cli_plugin.py
COPY cubbi_image.yaml /cubbi/cubbi_image.yaml
COPY init-status.sh /cubbi/init-status.sh

# Make scripts executable
RUN chmod +x /cubbi/cubbi_init.py /cubbi/init-status.sh

# Add init status check to bashrc
RUN echo '[ -x /cubbi/init-status.sh ] && /cubbi/init-status.sh' >> /etc/bash.bashrc

# Set up environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_LINK_MODE=copy

# Pre-install the cubbi_init
RUN /cubbi/cubbi_init.py --help

# Set WORKDIR to /app
WORKDIR /app

ENTRYPOINT ["/cubbi/cubbi_init.py"]
CMD ["tail", "-f", "/dev/null"]