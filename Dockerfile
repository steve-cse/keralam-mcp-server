FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./

# Install deps with uv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# Copy your source code
COPY main.py .

# Set environment for virtualenv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

# Run mcp from the venv
ENTRYPOINT ["mcp"]
CMD ["run", "main.py"]
