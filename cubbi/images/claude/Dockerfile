FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    sudo \
    openssh-server \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Create SSH host keys and configure SSH
RUN mkdir -p /var/run/sshd && chmod 0755 /var/run/sshd
# Do NOT enable root login or set root password here

# Install Node.js 23.x and update npm to latest version
RUN curl -fsSL https://deb.nodesource.com/setup_23.x -o nodesource_setup.sh && \
    bash nodesource_setup.sh && \
    apt-get install -y nodejs && \
    npm install -g npm@11.4.1 && \
    rm nodesource_setup.sh && \
    rm -rf /var/lib/apt/lists/*

# Install deps
WORKDIR /tmp
RUN curl -fsSL https://astral.sh/uv/install.sh -o install.sh && \
    chmod +x install.sh && \
    ./install.sh && \
    rm install.sh

# Make uv available in PATH for all users
ENV PATH="/root/.local/bin:$PATH"

# Copy cubbi container files
COPY cubbi-image.yaml /cubbi-image.yaml
COPY cubbi-init.sh /cubbi-init.sh
COPY entrypoint.sh /entrypoint.sh
COPY init-status.sh /init-status.sh

# Make scripts executable
RUN chmod +x /cubbi-init.sh /entrypoint.sh /init-status.sh

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]
CMD ["sleep", "infinity"]