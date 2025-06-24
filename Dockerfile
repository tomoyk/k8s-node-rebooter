# Multi-stage build to install dependencies
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/app/packages -r requirements.txt

# Final stage using slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /app/packages /app/packages

# Copy the main script
COPY restart_notready.py .

# Add OCI label
LABEL org.opencontainers.image.source https://github.com/tomoyk/k8s-node-rebooter

# Set Python path to include installed packages
ENV PYTHONPATH=/app/packages

# Set the entrypoint
ENTRYPOINT ["python3", "restart_notready.py"]