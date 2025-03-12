FROM python:3.12-slim

LABEL maintainer="team@monadical.com"
LABEL description="Goose with MCP servers"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    openssh-server \
    bash \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up SSH server
RUN mkdir /var/run/sshd
RUN echo 'root:root' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Create app directory
WORKDIR /app

# Install python dependencies
# This is done before copying scripts for better cache management
RUN pip install --no-cache-dir goose-ai langfuse

# Copy initialization scripts
COPY mc-init.sh /mc-init.sh
COPY entrypoint.sh /entrypoint.sh
COPY mc-driver.yaml /mc-driver.yaml
COPY init-status.sh /init-status.sh

# Make scripts executable
RUN chmod +x /mc-init.sh /entrypoint.sh /init-status.sh

# Set up initialization status check on login
RUN echo '[ -x /init-status.sh ] && /init-status.sh' >> /etc/bash.bashrc

# Set up environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose ports
EXPOSE 8000 22

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]