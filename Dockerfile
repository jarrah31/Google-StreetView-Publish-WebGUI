FROM python:3.11-slim-bookworm

# Set default values for PUID and PGID. These are the build-time defaults; the
# entrypoint remaps appuser to whatever PUID/PGID are set at runtime.
ENV PUID=1000 \
    PGID=1000

# Create a non-root user to run the application. The ids here are just the
# build-time defaults — docker-entrypoint.sh remaps appuser to the runtime
# PUID/PGID before dropping privileges, so bind-mounted volumes line up.
RUN groupadd -r -g ${PGID} appuser && \
    useradd -r -u ${PUID} -g appuser appuser

WORKDIR /app

# Upgrade OS packages to pick up security patches since the base image was
# built, and install gosu for the privilege drop in the entrypoint.
RUN apt-get update && apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends gosu && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=app.py

# Copy application files (sensitive paths are excluded via .dockerignore)
COPY --chown=appuser:appuser . .

# Install the entrypoint and set baseline permissions on the app code. The
# entrypoint chowns the runtime data dir at startup, so we only need ownership
# of the code itself here.
RUN chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    chmod +x /app/docker-entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5001/healthz')" || exit 1

# Expose the port the app runs on
EXPOSE ${PORT:-5001}

# The container starts as root so the entrypoint can remap appuser to the
# runtime PUID/PGID and chown the bind-mounted /app/userdata, then it drops
# privileges (via gosu) to run the CMD as appuser. Do NOT add `USER appuser`
# here — that would prevent the entrypoint from doing the remap.
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Command to run the application with gunicorn production server.
# This is a single-user tool: one worker keeps the session signing key and the
# in-memory stores (_preview_store, _filenames_cache) consistent (multiple
# workers are separate processes that share neither, which breaks OAuth login
# and Pannellum previews). Threads provide concurrency so a slow photo upload
# doesn't block other requests.
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "-w", "1", "--threads", "4", "app:app"]
