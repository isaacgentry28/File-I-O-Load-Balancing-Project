FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal system deps (kept small)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy application code (build context is ./server from docker-compose)
# Copy the entire context into /app so files are found during build
COPY . /app

# Provide a default config so the image can start even if no mount is supplied during development
RUN test -f /app/server_config.json || printf '{"repo_root": "repo_data/server-1", "api_key": "dev-key-123"}' > /app/server_config.json

# Install Python deps
RUN python -m pip install --upgrade pip \
    && pip install fastapi "uvicorn[standard]" python-multipart

EXPOSE 8000

# Note: server_config.json will be mounted at runtime via docker-compose (to allow host edits)
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
