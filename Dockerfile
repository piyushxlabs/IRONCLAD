# Multi-stage production container for Amazon Bedrock AgentCore Runtime
# Target: Python 3.11 with fast deterministic uv dependency management

FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv binary from official distribution
COPY --from=ghcr.io/astral-sh/uv:0.6.5 /uv /bin/uv

# Build-time environment optimization
ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy dependency specifications
COPY pyproject.toml uv.lock ./

# Install locked production dependencies without dev extras
RUN uv sync --frozen --no-dev --no-editable

# Production runner stage
FROM python:3.11-slim AS runner

WORKDIR /app

# Create unprivileged system user for OWASP runtime container isolation
RUN groupadd -r ironclad && useradd -r -g ironclad -u 1001 ironclad

# Copy compiled virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    IRONCLAD_RUNTIME_MODE=bedrock

# Copy application source code and reference catalogs
COPY src/ /app/src/
COPY README.md /app/README.md

# Set ownership to unprivileged user
RUN chown -R ironclad:ironclad /app

USER ironclad

# Expose Bedrock AgentCore standard port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/ping')" || exit 1

# Start the Bedrock AgentCore application
CMD ["python", "-m", "src.main"]
