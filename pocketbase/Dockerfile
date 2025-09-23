FROM alpine:latest

# Install required packages
RUN apk add --no-cache \
    ca-certificates \
    unzip \
    wget \
    curl

# Create app directory
WORKDIR /pb

# Download and install latest PocketBase
RUN LATEST_VERSION=$(wget -qO- https://api.github.com/repos/pocketbase/pocketbase/releases/latest | grep -o '"tag_name": "[^"]*' | grep -o '[^"]*$' | sed 's/^v//') && \
    wget https://github.com/pocketbase/pocketbase/releases/download/v${LATEST_VERSION}/pocketbase_${LATEST_VERSION}_linux_amd64.zip && \
    unzip pocketbase_${LATEST_VERSION}_linux_amd64.zip && \
    chmod +x pocketbase && \
    rm pocketbase_${LATEST_VERSION}_linux_amd64.zip

# Create data directory
RUN mkdir -p /pb/pb_data /pb/pb_public

# Expose port
EXPOSE 8090

# Run PocketBase
CMD ["./pocketbase", "serve", "--http=0.0.0.0:8090"]