# Docker Permissions Setup

Fix Docker permissions issues for RARSMS deployment.

## 🔧 Quick Fix

The Docker permission error occurs when your user doesn't have access to the Docker daemon. Here are the solutions:

### Linux (Most Common)

**Add your user to the docker group:**
```bash
# Add current user to docker group
sudo usermod -aG docker $USER

# Log out and log back in (or reboot)
# Then test Docker access
docker ps
```

**Alternative: Use sudo for now:**
```bash
# If you can't log out/in immediately
sudo docker compose --profile setup run --rm setup
sudo docker compose up -d

# Then fix permissions later
```

### Verify Docker is Running

```bash
# Check Docker daemon status
sudo systemctl status docker

# Start Docker if not running
sudo systemctl start docker

# Enable Docker to start on boot
sudo systemctl enable docker
```

## 🐧 Platform-Specific Solutions

### Ubuntu/Debian
```bash
# Install Docker if not installed
sudo apt update
sudo apt install docker.io docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Logout and login, then test
docker --version
```

### CentOS/RHEL/Fedora
```bash
# Install Docker
sudo dnf install docker docker-compose

# Add user to docker group
sudo usermod -aG docker $USER

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Logout and login, then test
docker --version
```

### macOS
```bash
# Install Docker Desktop
# Download from: https://www.docker.com/products/docker-desktop

# Docker Desktop handles permissions automatically
# No additional setup needed
```

### Windows
```bash
# Install Docker Desktop
# Download from: https://www.docker.com/products/docker-desktop

# Run as Administrator if needed
# Docker Desktop handles permissions automatically
```

## 🔒 Security Considerations

### Docker Group Warning
Adding users to the `docker` group gives them root-equivalent access to the system. This is necessary for Docker usage but should be limited to trusted users.

### Alternative: Rootless Docker
For better security, consider rootless Docker:

```bash
# Install rootless Docker (advanced)
curl -fsSL https://get.docker.com/rootless | sh

# Follow the installation instructions
# This allows Docker without root access
```

## 🚨 Troubleshooting

### Permission Still Denied After Group Addition

**Solution 1: Force group refresh**
```bash
# Refresh groups without logout
newgrp docker

# Test Docker access
docker ps
```

**Solution 2: Check group membership**
```bash
# Verify you're in docker group
groups $USER

# Should show: ... docker ...
# If not, repeat the usermod command
```

**Solution 3: Restart Docker service**
```bash
sudo systemctl restart docker
```

### Docker Socket Issues

**Check socket permissions:**
```bash
ls -la /var/run/docker.sock
# Should show: srw-rw---- 1 root docker

# Fix if needed:
sudo chmod 666 /var/run/docker.sock
```

**Fix socket ownership:**
```bash
sudo chown root:docker /var/run/docker.sock
```

### WSL (Windows Subsystem for Linux)

**Enable WSL Docker integration:**
1. Install Docker Desktop on Windows
2. Enable WSL integration in Docker Desktop settings
3. Restart WSL: `wsl --shutdown` then reopen

**WSL-specific commands:**
```bash
# In WSL, Docker should work without sudo
docker --version

# If not, check Docker Desktop WSL integration
```

## ✅ Verification Steps

After fixing permissions, verify everything works:

```bash
# Test basic Docker access
docker --version
docker ps

# Test Docker Compose
docker compose --version

# Test RARSMS setup
cd /path/to/rarsms
docker compose --profile setup run --rm setup

# If successful, proceed with deployment
docker compose up -d
```

## 🔄 Complete RARSMS Setup After Permission Fix

Once Docker permissions are fixed:

```bash
# Navigate to RARSMS directory
cd rarsms

# Run setup
docker compose --profile setup run --rm setup

# Edit configuration
nano .env  # or your preferred editor

# Start services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs
```

## 📋 Alternative Deployment Methods

### Using sudo (temporary solution)
```bash
sudo docker compose --profile setup run --rm setup
sudo docker compose up -d
sudo docker compose logs
```

### Using Docker Desktop (GUI)
1. Open Docker Desktop
2. Go to "Containers"
3. Click "Import" or "Create"
4. Select your docker-compose.yml file
5. Configure and start

### Cloud Deployment
Many cloud platforms handle Docker permissions automatically:
- AWS ECS
- Google Cloud Run
- Azure Container Instances
- DigitalOcean App Platform

## 🏠 NAS-Specific Notes

### Synology NAS
- No permission issues with Container Manager
- Use web interface for deployment
- See README-SYNOLOGY.md for details

### QNAP NAS
- Use Container Station
- No command-line permission issues
- Web-based management

### Unraid
- Use Community Applications
- Docker permissions handled by system
- Web-based deployment

## 🎯 Prevention

To avoid permission issues in the future:

1. **Always add new users to docker group during setup**
2. **Use Docker Desktop on desktop systems**
3. **Consider rootless Docker for security**
4. **Use web-based container management on NAS systems**
5. **Document user setup procedures for your environment**

Once permissions are fixed, RARSMS will deploy smoothly with pure Docker Compose commands! 🐳📡