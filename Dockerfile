# Source: QWED Universal Commerce Protocol Auditor
FROM python:3.14.6-slim

# Prevent python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Force UTF-8 output so emoji and other non-ASCII prints don't crash
ENV PYTHONUTF8=1
# qwed-ucp is imported from source; the project itself is never built/installed
# (see uv sync --no-install-project below), so no first-party build backend runs.
ENV PYTHONPATH=/app/src

# Install uv (pinned version) for reproducible builds from uv.lock
COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /usr/local/bin/uv

WORKDIR /app
COPY . /app
# Dependency install is locked and script-free:
#   --frozen            asserts uv.lock matches pyproject.toml (fails otherwise)
#   --no-build           third-party deps must come from wheels; no build backend
#                        (setup.py/PEP 517 hooks) is ever executed
#   --no-install-project keeps qwed-ucp itself out of the install step; it is
#                        imported from /app/src via PYTHONPATH above
RUN uv sync --frozen --no-build --no-install-project

# action_entrypoint.py is already under /app via COPY . /app above.
# Run the locked environment's interpreter directly: no sync, no build, and no
# package-manager script execution at container start.
ENTRYPOINT ["/app/.venv/bin/python", "/app/action_entrypoint.py"]
