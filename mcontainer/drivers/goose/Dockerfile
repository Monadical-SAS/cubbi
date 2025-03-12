FROM python:3.12-slim

LABEL maintainer="team@monadical.com"
LABEL description="Goose with MCP servers"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    openssh-server \
    bash \
    curl \
    bzip2 \
    iputils-ping \
    iproute2 \
    nano \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Set up SSH server
RUN mkdir /var/run/sshd
RUN echo 'root:root' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Install python dependencies
# This is done before copying scripts for better cache management
WORKDIR /tmp
RUN curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh -o download_cli.sh && \
    chmod +x download_cli.sh && \
    ./download_cli.sh

# Create app directory
WORKDIR /app

# Copy initialization scripts
COPY mc-init.sh /mc-init.sh
COPY entrypoint.sh /entrypoint.sh
COPY mc-driver.yaml /mc-driver.yaml
COPY init-status.sh /init-status.sh

# Extend env via bashrc

# Make scripts executable
RUN chmod +x /mc-init.sh /entrypoint.sh /init-status.sh

# Set up initialization status check on login
RUN echo 'export PATH=/root/.local/bin:$PATH' >> /etc/bash.bashrc
RUN echo '[ -x /init-status.sh ] && /init-status.sh' >> /etc/bash.bashrc

# Set up environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose ports
EXPOSE 8000 22

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]
