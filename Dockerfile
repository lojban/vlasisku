FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV FLASK_APP=vlasisku
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Create a startup script in a location that won't be overwritten by volume mounts
RUN echo '#!/bin/bash\n\
set -e\n\
cd /app\n\
export FLASK_APP=vlasisku\n\
# Initialize database if it does not exist\n\
if [ ! -f vlasisku/data/db.pickle ]; then\n\
    echo "Database not found. Initializing..."\n\
    flask updatedb || echo "Database update failed, continuing anyway..."\n\
fi\n\
# Start the application\n\
exec gunicorn vlasisku:app --access-logfile - --error-logfile - --access-logformat "%(h)s %({x-forwarded-for}i)s %(l)s %(u)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\"" -w 1 -b 0.0.0.0:8080\n\
' > /usr/local/bin/start.sh && chmod +x /usr/local/bin/start.sh

# Run the startup script
ENTRYPOINT ["/usr/local/bin/start.sh"]
