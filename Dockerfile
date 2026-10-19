# ARG BASE_IMAGE=swebench/sweb.eval.x86_64.sympy_1776_sympy-23534:latest
ARG BASE_IMAGE=python:3.10-slim
FROM ${BASE_IMAGE}

RUN apt-get update && apt-get install -y \
    git \
    bash \
    curl \
    && rm -rf /var/lib/apt/lists/*
# Install UV
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin/:/root/.cargo/bin:$PATH"

# Copy your student code
WORKDIR /app
# Copy dependency files first (for caching)
COPY pyproject.toml uv.lock mcp_tools_mbpp.py mcp_tools_swebench.py ./
COPY student/ ./student/
RUN uv sync --no-dev

# Copy your student code

# Set environment
ENV PYTHONPATH="/app"