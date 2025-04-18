FROM python:3.12-slim

LABEL maintainer="team@monadical.com"
LABEL description="Goose with MCP servers for Cubbi"

# Install system dependencies including gosu for user switching and shadow for useradd/groupadd
RUN apt-get update && apt-get install -y --no-install-recommends \
    gosu \
    passwd \
    git \
    openssh-server \
    bash \
    curl \
    bzip2 \
    iputils-ping \
    iproute2 \
    libxcb1 \
    libdbus-1-3 \
    nano \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Set up SSH server directory (configuration will be handled by entrypoint if needed)
RUN mkdir -p /var/run/sshd && chmod 0755 /var/run/sshd
# Do NOT enable root login or set root password here

# Install deps
WORKDIR /tmp
RUN curl -fsSL https://astral.sh/uv/install.sh -o install.sh && \
    sh install.sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx && \
    rm install.sh
RUN curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh -o download_cli.sh && \
    chmod +x download_cli.sh && \
    ./download_cli.sh && \
    mv /root/.local/bin/goose /usr/local/bin/goose && \
    rm -rf download_cli.sh /tmp/goose-*

# Create app directory
WORKDIR /app

# Copy initialization scripts
COPY cubbi-init.sh /cubbi-init.sh
COPY entrypoint.sh /entrypoint.sh
COPY cubbi-image.yaml /cubbi-image.yaml
COPY init-status.sh /init-status.sh
COPY update-goose-config.py /usr/local/bin/update-goose-config.py

# Extend env via bashrc

# Make scripts executable
RUN chmod +x /cubbi-init.sh /entrypoint.sh /init-status.sh \
    /usr/local/bin/update-goose-config.py

# Set up initialization status check on login
RUN echo '[ -x /init-status.sh ] && /init-status.sh' >> /etc/bash.bashrc

# Set up environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Set WORKDIR to /app, common practice and expected by cubbi-init.sh
WORKDIR /app

# Expose ports
EXPOSE 8000 22

# Set entrypoint - container starts as root, entrypoint handles user switching
ENTRYPOINT ["/entrypoint.sh"]
# Default command if none is provided (entrypoint will run this via gosu)
CMD ["tail", "-f", "/dev/null"]
