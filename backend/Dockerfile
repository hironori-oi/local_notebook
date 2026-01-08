# Backend Dockerfile
# Multi-stage build for smaller final image

# Stage 1: Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install poetry
RUN pip install poetry==1.7.1

# Copy dependency files and app directory
COPY pyproject.toml poetry.lock* ./
COPY app ./app

# Configure poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies (without dev dependencies)
RUN poetry install --only main --no-interaction --no-ansi

# Stage 2: Production stage
FROM python:3.11-slim as production

WORKDIR /app

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Install runtime dependencies (including ffmpeg for yt-dlp audio extraction)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/uploads data/audio_temp && chown -R appuser:appgroup data

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
