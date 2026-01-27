# Use Python 3.13 slim image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies including FFmpeg for video screenshot extraction
RUN apt-get update && apt-get install -y \
    postgresql-client \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Force cache invalidation - change this value to force rebuild
ARG CACHEBUST=1

# Copy project
COPY . /app/

# Create media directories
RUN mkdir -p /app/media/articles /app/static /app/staticfiles

# Copy and set permissions for entrypoint script
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 8001

# Run entrypoint script
CMD ["/app/entrypoint.sh"]
