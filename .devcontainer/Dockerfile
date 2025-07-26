FROM python:3.12-bookworm

# Install system dependencies and tools
RUN apt-get update && apt-get install -y \
    # Basic utilities
    curl \
    wget \
    git \
    sudo \
    # Build essentials
    build-essential \
    # Zsh and utilities
    zsh \
    # Direnv
    direnv \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Switch to non-root user for installations
USER $USERNAME
WORKDIR /home/$USERNAME

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Claude Code
RUN curl -fsSL https://claude.ai/install.sh | bash

# Configure zsh with Oh My Zsh
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended

# Configure direnv for zsh
RUN echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc

# Add uv and Claude Code to PATH in both bash and zsh
RUN echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc \
    && echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc

# Set zsh as default shell
ENV SHELL=/usr/bin/zsh

# Set working directory
WORKDIR /workspace

# Create .envrc file for direnv (will be populated later if needed)
RUN touch /workspace/.envrc || true

# Ensure proper permissions
USER root
RUN chown -R $USERNAME:$USERNAME /home/$USERNAME

# Switch back to non-root user
USER $USERNAME

# Default command
CMD ["/usr/bin/zsh"]