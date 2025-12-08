FROM python:3.11-slim

WORKDIR /app

# Install dependencies
# docker: Python Docker SDK
# requests: For HTTP health checks
RUN pip install --no-cache-dir docker requests

# Create logs directory
RUN mkdir -p /app/logs

# Copy Agent Code
COPY agent.py .

# Run unbuffered for real-time logs
CMD ["python", "-u", "agent.py"]
