# Build stage: Install dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Install CA certificates for SSL
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install all dependencies including dev dependencies (pytest, etc.)
RUN uv sync --frozen --extra dev

# Runtime stage: Create final image
FROM python:3.11-slim

WORKDIR /app

# Install CA certificates for SSL
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy Python environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ ./src/
COPY tests/ ./tests/
COPY pyproject.toml ./

# Set environment to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Default command (can be overridden in docker-compose)
CMD ["python", "-m", "src.cli.main", "--help"]
