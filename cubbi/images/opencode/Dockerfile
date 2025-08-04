FROM python:3.12-slim

LABEL maintainer="team@monadical.com"
LABEL description="Opencode for Cubbi"

# Install system dependencies including gosu for user switching and shadow for useradd/groupadd
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

# Install deps
WORKDIR /tmp
RUN curl -fsSL https://astral.sh/uv/install.sh -o install.sh && \
    sh install.sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx && \
    rm install.sh

# Install Node.js
ARG NODE_VERSION=v22.16.0
RUN mkdir -p /opt/node && \
    ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
    NODE_ARCH=linux-x64; \
    elif [ "$ARCH" = "aarch64" ]; then \
    NODE_ARCH=linux-arm64; \
    else \
    echo "Unsupported architecture"; exit 1; \
    fi && \
    curl -fsSL https://nodejs.org/dist/$NODE_VERSION/node-$NODE_VERSION-$NODE_ARCH.tar.gz -o node.tar.gz && \
    tar -xf node.tar.gz -C /opt/node --strip-components=1 && \
    rm node.tar.gz


ENV PATH="/opt/node/bin:$PATH"
RUN npm i -g yarn
RUN npm i -g opencode-ai

# Create app directory
WORKDIR /app

# Copy initialization system
COPY cubbi_init.py /cubbi/cubbi_init.py
COPY opencode_plugin.py /cubbi/opencode_plugin.py
COPY cubbi_image.yaml /cubbi/cubbi_image.yaml
COPY init-status.sh /cubbi/init-status.sh
RUN chmod +x /cubbi/cubbi_init.py /cubbi/init-status.sh
RUN echo 'PATH="/opt/node/bin:$PATH"' >> /etc/bash.bashrc
RUN echo '[ -x /cubbi/init-status.sh ] && /cubbi/init-status.sh' >> /etc/bash.bashrc

# Set up environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_LINK_MODE=copy
ENV COLORTERM=truecolor

# Pre-install the cubbi_init
RUN /cubbi/cubbi_init.py --help

# Set WORKDIR to /app, common practice and expected by cubbi-init.sh
WORKDIR /app

ENTRYPOINT ["/cubbi/cubbi_init.py"]
CMD ["tail", "-f", "/dev/null"]
