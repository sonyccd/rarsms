FROM alpine:latest

# Install ca-certificates for SSL/TLS
RUN apk --no-cache add ca-certificates tzdata

# Set timezone
ENV TZ=America/New_York

# Create app directory
WORKDIR /app

# Create data directory for PocketBase
RUN mkdir -p /app/pb_data

# Download and install PocketBase
ADD https://github.com/pocketbase/pocketbase/releases/download/v0.30.0/pocketbase_0.30.0_linux_amd64.zip /tmp/pb.zip

RUN unzip /tmp/pb.zip -d /tmp/ && \
    mv /tmp/pocketbase /app/pocketbase && \
    chmod +x /app/pocketbase && \
    rm /tmp/pb.zip

# Copy PocketBase configuration
COPY pb_hooks/ /app/pb_hooks/
COPY pb_migrations/ /app/pb_migrations/
COPY pb_public/ /app/pb_public/

# Create startup script
RUN echo '#!/bin/sh' > /app/start.sh && \
    echo 'echo "Starting PocketBase..."' >> /app/start.sh && \
    echo '/app/pocketbase serve --http=0.0.0.0:8090 --dir=/app/pb_data --hooksDir=/app/pb_hooks --migrationsDir=/app/pb_migrations --publicDir=/app/pb_public' >> /app/start.sh && \
    chmod +x /app/start.sh

# Expose port
EXPOSE 8090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8090/api/health || exit 1

# Run PocketBase
CMD ["/app/start.sh"]