# Multi-stage build to install dependencies
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/app/packages -r requirements.txt

# Final stage using distroless image
FROM gcr.io/distroless/python3-debian11

# Set working directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /app/packages /app/packages

# Copy the main script
COPY restart_notready.py .

# Make script executable
RUN chmod +x restart_notready.py

# Create necessary directories
RUN mkdir -p /kube /config /secrets

# Set Python path to include installed packages
ENV PYTHONPATH=/app/packages

# Set the entrypoint
ENTRYPOINT ["python3", "restart_notready.py"]