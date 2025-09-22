FROM python:3.9-slim

# Create non-root user for security
RUN groupadd -r rarsms && useradd -r -g rarsms rarsms

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY config.yaml* ./
COPY callsigns.txt* ./

# Copy protocol and notification modules
COPY protocols/ ./protocols/
COPY notifiers/ ./notifiers/

# Change ownership to non-root user
RUN chown -R rarsms:rarsms /app

# Switch to non-root user
USER rarsms

# Set up signal handling
STOPSIGNAL SIGTERM

# Run the application
CMD ["python", "main.py"]