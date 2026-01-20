# Source: QWED Universal Commerce Protocol Auditor
FROM python:3.11-slim

# Prevent python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
# Since qwed-ucp is not on PyPI yet (v0.1.0), we install from local or assume it's COPY'd.
# Ideally we pip install ., but here we will COPY src.

WORKDIR /app
COPY . /app
RUN pip install .

# Entrypoint
COPY action_entrypoint.py /action_entrypoint.py
RUN chmod +x /action_entrypoint.py

ENTRYPOINT ["python", "/action_entrypoint.py"]
