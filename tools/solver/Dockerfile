# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY ./app /app

# Expose port 8086 for this microservice
EXPOSE 8086

# Validate the API key and then start the application
CMD ["sh", "-c", "python validate_api_key.py && uvicorn main:app --host 0.0.0.0 --port 8086 --workers 4"]
