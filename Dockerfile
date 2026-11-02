# =============================================================================
# Stage 1: Build & Dependencies
# =============================================================================
FROM python:3.13-slim AS builder

WORKDIR /build

# Prevent Python from writing bytecode and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies
# ✅ Added: OpenCV + PaddleOCR system libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment for isolated, clean dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2: Production Runtime
# =============================================================================
FROM python:3.13-slim AS runner

WORKDIR /app

# Configure runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PATH="/opt/venv/bin:$PATH"

# ✅ Added system dependencies needed at RUNTIME for OCR & CV models
# libgl1 / libglib2.0-0 / libgomp1 are required by OpenCV and Paddle
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create a dedicated non-root system group and user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup --no-create-home appuser

# Copy application source code and entrypoint with non-root ownership
COPY --chown=appuser:appgroup app /app/app
COPY --chown=appuser:appgroup docker-entrypoint.sh /app/docker-entrypoint.sh

# Ensure execution permission on entrypoint script
RUN chmod +x /app/docker-entrypoint.sh

# Switch to non-root user
USER appuser

# Default application port
EXPOSE 8000

# Container healthcheck using FastAPI root endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f "http://localhost:${PORT:-8000}/" || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]