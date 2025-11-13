# Docker Deployment Guide

This directory contains Docker configuration files for deploying Starbelly in a containerized environment.

## Files

- **Dockerfile**: Builds the Starbelly application container with proper init process handling
- **docker-compose.prod.yml**: Production-ready Docker Compose configuration
- **.dockerignore**: Specifies files to exclude from the Docker build context

## Why Use an Init Process?

When running applications in Docker containers, the first process (PID 1) has special responsibilities:

1. **Signal Handling**: PID 1 must properly handle and forward signals (SIGTERM, SIGINT, etc.) to child processes
2. **Zombie Reaping**: PID 1 must reap zombie processes to prevent resource leaks
3. **Graceful Shutdown**: Proper signal handling ensures containers shut down gracefully instead of hanging

Python applications don't naturally handle these responsibilities well when running as PID 1. This is why the Dockerfile uses `dumb-init` as the init process.

## Quick Start

### Building and Running with Docker Compose

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down
```

### Building the Docker Image Manually

```bash
# Build the image
docker build -t starbelly:latest .

# Run a container
docker run -d \
  --name starbelly \
  -p 8000:8000 \
  -v $(pwd)/conf:/starbelly/conf \
  starbelly:latest
```

## Configuration

The container expects configuration in the `/starbelly/conf` directory. You can:

1. Mount a volume with your configuration:
   ```bash
   docker run -v /path/to/your/conf:/starbelly/conf starbelly:latest
   ```

2. Let the `container_init.py` script create default configuration on first run

## Environment Variables

You can customize the application behavior using environment variables:

- `STARBELLY_LOG_LEVEL`: Set logging level (debug, info, warning, error, critical)

## Signal Handling

Thanks to `dumb-init`, the containers properly handle:

- **SIGTERM**: Graceful shutdown (used by `docker stop`)
- **SIGINT**: Interrupt signal (Ctrl+C)
- **SIGKILL**: Forceful termination (not catchable, used as last resort)

Test signal handling:

```bash
# Start container
docker run --name test-starbelly starbelly:latest

# In another terminal, send SIGTERM (should shutdown gracefully)
docker stop test-starbelly

# Container should stop within a few seconds
```

## Development vs Production

- The `dev/docker-compose.yml` is for development with external Starbelly server
- The `docker-compose.prod.yml` is for production deployment with the server in a container

## Troubleshooting

### Container hangs on shutdown

If your container hangs when stopping, verify that:
1. The Dockerfile uses `dumb-init` as ENTRYPOINT
2. The application properly handles signals
3. You're not running the application with shell wrappers that don't forward signals

### Database connection issues

Ensure the database service is fully started before the application:
```yaml
depends_on:
  - db
```

For more robust startup, consider using a wait script or retries in `container_init.py`.

## Further Reading

- [dumb-init documentation](https://github.com/Yelp/dumb-init)
- [Docker and the PID 1 zombie reaping problem](https://blog.phusion.nl/2015/01/20/docker-and-the-pid-1-zombie-reaping-problem/)
- [Best practices for signals in Docker](https://www.docker.com/blog/docker-best-practices-choosing-between-run-cmd-and-entrypoint/)
