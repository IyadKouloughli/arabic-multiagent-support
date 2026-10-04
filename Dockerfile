FROM python:3.11-slim AS base

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and dataset
COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose ports: 8000 for FastAPI API, 8501 for Streamlit Dashboard
EXPOSE 8000
EXPOSE 8501

# Default command launches FastAPI service
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
