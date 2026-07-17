# Source: QWED Universal Commerce Protocol Auditor
FROM python:3.14.6-slim

# Prevent python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Force UTF-8 output so emoji and other non-ASCII prints don't crash
ENV PYTHONUTF8=1

# Install uv (pinned version) for reproducible builds from uv.lock
COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /usr/local/bin/uv

WORKDIR /app
COPY . /app
# Install the project with --frozen so uv.lock pins are enforced.
# If uv.lock is out of sync with pyproject.toml, the build fails.
RUN uv sync --frozen

# action_entrypoint.py is already under /app via COPY . /app above
ENTRYPOINT ["uv", "run", "--project", "/app", "python", "/app/action_entrypoint.py"]
