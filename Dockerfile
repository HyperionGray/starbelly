# Use Python 3.7 as base image (matching project requirements)
FROM python:3.7-slim

# Install dumb-init to properly handle signals and reap zombie processes
RUN apt-get update && \
    apt-get install -y --no-install-recommends dumb-init && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /starbelly

# Install Poetry
RUN pip install --no-cache-dir poetry==1.1.15

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies (without installing the project itself yet)
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Copy the rest of the application
COPY . .

# Install the project
RUN poetry install --no-interaction --no-ansi

# Create conf directory for runtime configuration
RUN mkdir -p /starbelly/conf

# Use dumb-init as the init process (PID 1)
ENTRYPOINT ["/usr/bin/dumb-init", "--"]

# Default command: run container initialization then start the application
CMD ["python", "tools/container_init.py", "python", "-m", "starbelly", "--ip", "0.0.0.0"]
