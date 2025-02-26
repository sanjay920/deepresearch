FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create workspace directory
RUN mkdir -p /app/workspace

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV WORKSPACE_DIR=/app/workspace

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 