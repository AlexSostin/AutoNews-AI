# Use Python 3.13 slim image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Create media directories
RUN mkdir -p /app/media/articles /app/static /app/staticfiles

# Collect static files will be done in docker-compose command
# Migrations will be done in docker-compose command

# Expose port
EXPOSE 8001

# Run server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8001"]
