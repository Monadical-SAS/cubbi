FROM python:3.12-slim

LABEL maintainer="team@monadical.com"
LABEL description="Aider"

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    vim \
    nano \
    openssh-server \
    sudo \
    screen \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Set up SSH server
RUN mkdir /var/run/sshd
RUN echo 'root:root' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Setup working directory
WORKDIR /app

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.cargo/bin:${PATH}"

# Install aider using the official install script
RUN curl https://aider.chat/install.sh | sh

# Copy scripts
COPY entrypoint.sh /
COPY mc-init.sh /
COPY update-aider-config.sh /usr/local/bin/

# Make scripts executable
RUN chmod +x /entrypoint.sh
RUN chmod +x /mc-init.sh
RUN chmod +x /usr/local/bin/update-aider-config.sh

# Expose ports for SSH and editor integration
EXPOSE 22 8080

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]