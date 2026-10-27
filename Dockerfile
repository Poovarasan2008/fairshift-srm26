# Use official lightweight Python image
FROM python:3.11-slim

# Set environment variables
# Prevent Python from writing .pyc files & allow real-time stdout logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Set working directory inside container
WORKDIR /app

# Install dependencies first for fast layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application source code
COPY . .

# Expose port (Google Cloud Run defaults to 8080)
EXPOSE 8080

# Run with Gunicorn web server as required for Cloud Run
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 app:app

