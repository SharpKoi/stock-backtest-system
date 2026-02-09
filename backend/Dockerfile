# Multi-stage build for smaller final image
FROM python:3.13-slim AS builder

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==2.0.1

# Set working directory
WORKDIR /app

# Copy SDK to parent directory (to match relative path in pyproject.toml)
COPY vici-trade-sdk /vici-trade-sdk

# Copy poetry files to /app
COPY backend/pyproject.toml backend/poetry.lock backend/poetry.toml /app/

# Configure Poetry to not create virtual environment and install dependencies
# The path in pyproject.toml is "../vici-trade-sdk" which resolves to /vici-trade-sdk
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --only main --no-interaction --no-ansi


# ============= Final Stage =============
FROM python:3.13-slim

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser backend/app /app/app
COPY --chown=appuser:appuser backend/strategies /app/strategies

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /var/app/workspaces && \
    chown -R appuser:appuser /app /var/app/workspaces

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
