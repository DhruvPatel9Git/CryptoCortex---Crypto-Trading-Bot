FROM python:3.10-slim

# Reduce layers and keep image small
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps required for some libraries
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . /app

# Make startup script executable
RUN chmod +x Backend/startup.sh


# Expose the port that Render will route to
ENV PORT=8000
EXPOSE 8000

# Use startup script as entrypoint so we can download large model files at container start
ENTRYPOINT ["./Backend/startup.sh"]

# Default command for web service (executed after startup script)
# Use Gunicorn with Uvicorn worker for production-ready async serving
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8000", "--workers", "1"]
