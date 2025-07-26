# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# Expose port for webhook
EXPOSE 8081

# Set environment variables
ENV PYTHONPATH=/app
ENV TZ=UTC

# Use webhook handler as entry point
CMD ["python", "-c", "import webhook_handler; import runpod; runpod.serverless.start({'handler': webhook_handler.handler})"]
