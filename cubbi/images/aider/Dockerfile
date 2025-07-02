FROM python:3.12-slim

LABEL maintainer="team@monadical.com"
LABEL description="Aider AI pair programming for Cubbi"

# Install system dependencies including gosu for user switching
RUN apt-get update && apt-get install -y --no-install-recommends \
    gosu \
    sudo \
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
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager)
WORKDIR /tmp
RUN curl -fsSL https://astral.sh/uv/install.sh -o install.sh && \
    sh install.sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx && \
    rm install.sh

# Install Aider using pip in system Python (more compatible with user switching)
RUN python -m pip install aider-chat

# Make sure aider is in PATH
ENV PATH="/root/.local/bin:$PATH"

# Create app directory
WORKDIR /app

# Copy initialization system
COPY cubbi_init.py /cubbi/cubbi_init.py
COPY aider_plugin.py /cubbi/aider_plugin.py
COPY cubbi_image.yaml /cubbi/cubbi_image.yaml
COPY init-status.sh /cubbi/init-status.sh

# Make scripts executable
RUN chmod +x /cubbi/cubbi_init.py /cubbi/init-status.sh

# Add aider to PATH in bashrc and init status check
RUN echo 'PATH="/root/.local/bin:$PATH"' >> /etc/bash.bashrc
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
