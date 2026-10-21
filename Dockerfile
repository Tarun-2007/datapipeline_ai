# DataPulse AI - Base Production Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy platform source code
COPY . .

# Expose default API and Streamlit ports
EXPOSE 8000 8501

# Default command: launch FastAPI server
CMD ["uvicorn", "app.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
