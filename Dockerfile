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

# Run a simple HTTP server for webhooks
CMD ["python", "-c", "from http.server import HTTPServer, BaseHTTPRequestHandler; import json; import webhook_handler; \
class WebhookHandler(BaseHTTPRequestHandler): \
    def do_POST(self): \
        content_length = int(self.headers['Content-Length']); \
        post_data = self.rfile.read(content_length); \
        try: \
            data = json.loads(post_data.decode('utf-8')); \
            result = webhook_handler.handler(data); \
            self.send_response(200); \
            self.send_header('Content-type', 'application/json'); \
            self.end_headers(); \
            self.wfile.write(json.dumps(result).encode('utf-8')); \
        except Exception as e: \
            self.send_response(500); \
            self.end_headers(); \
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8')); \
    def log_message(self, format, *args): pass; \
httpd = HTTPServer(('0.0.0.0', 8081), WebhookHandler); \
print('Server starting on port 8081...'); \
httpd.serve_forever()"]
