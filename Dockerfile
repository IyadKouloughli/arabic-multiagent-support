FROM python:3.11-slim AS base

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and dataset (honoring .dockerignore)
COPY . .

# Ensure entrypoint has Unix line endings and execute permissions
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose default ports
EXPOSE 8000
EXPOSE 8501

ENTRYPOINT ["/app/entrypoint.sh"]
