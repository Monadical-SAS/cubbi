FROM python:3.12-slim

LABEL maintainer="team@monadical.com"
LABEL description="Goose for Cubbi"

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
RUN curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh -o download_cli.sh && \
    chmod +x download_cli.sh && \
    ./download_cli.sh && \
    mv /root/.local/bin/goose /usr/local/bin/goose && \
    rm -rf download_cli.sh /tmp/goose-*

# Create app directory
WORKDIR /app

# Copy initialization system
COPY cubbi_init.py /cubbi/cubbi_init.py
COPY goose_plugin.py /cubbi/goose_plugin.py
COPY cubbi_image.yaml /cubbi/cubbi_image.yaml
COPY init-status.sh /cubbi/init-status.sh
RUN chmod +x /cubbi/cubbi_init.py /cubbi/init-status.sh
RUN echo '[ -x /cubbi/init-status.sh ] && /cubbi/init-status.sh' >> /etc/bash.bashrc

# Set up environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_LINK_MODE=copy

# Pre-install the cubbi_init
RUN /cubbi/cubbi_init.py --help

# Set WORKDIR to /app, common practice and expected by cubbi-init.sh
WORKDIR /app

ENTRYPOINT ["/cubbi/cubbi_init.py"]
CMD ["tail", "-f", "/dev/null"]
