FROM python:3.11-slim

# Set default values for PUID and PGID
ENV PUID=1000 \
    PGID=1000

# Create a non-root user to run the application with customizable UID/GID
RUN groupadd -r -g ${PGID} appuser && \
    useradd -r -u ${PUID} -g appuser appuser

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=app.py

# Copy application files
COPY --chown=appuser:appuser . .

# Create necessary directories with proper permissions
RUN chown -R appuser:appuser /app && \
    chmod -R 755 /app 

# Clean up
RUN rm -f /app/userdata/*

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-5001}/ || exit 1

# Expose the port the app runs on
EXPOSE ${PORT:-5001}

# Command to run the application with gunicorn production server
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "-w", "4", "app:app"]
