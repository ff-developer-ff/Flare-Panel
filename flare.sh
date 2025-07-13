#!/bin/bash

# 🔥 Flare Panel Ubuntu Installation Script
# GitHub: https://github.com/ff-developer-ff/Flare-Panel.git

echo "🔥 Flare Panel Ubuntu Installation Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[HEADER]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_status "Running as root - proceeding with installation"
else
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

# Update system packages
print_header "Step 1: Updating System Packages"
print_status "Updating package list..."
apt update -y

print_status "Upgrading system packages..."
apt upgrade -y

# Install required packages
print_header "Step 2: Installing Required Packages"
print_status "Installing Python and development tools..."

apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    curl \
    wget \
    unzip \
    tar \
    gzip \
    htop \
    nano \
    vim \
    ufw \
    nginx \
    supervisor

# Verify Python installation
print_status "Verifying Python installation..."
python3 --version

if [ $? -ne 0 ]; then
    print_error "Python3 installation failed"
    exit 1
fi

# Create Flare Panel directory
print_header "Step 3: Setting Up Flare Panel Directory"
print_status "Creating Flare Panel directory..."

cd /root

# Remove old installations if they exist
if [ -d "Flare-Panel" ]; then
    print_warning "Existing Flare Panel directory found. Removing..."
    rm -rf Flare-Panel
fi

# Clone Flare Panel repository
print_status "Cloning Flare Panel from GitHub..."
git clone https://github.com/ff-developer-ff/Flare-Panel.git

if [ $? -ne 0 ]; then
    print_error "Failed to clone Flare Panel repository"
    exit 1
fi

cd Flare-Panel

# Create virtual environment
print_header "Step 4: Setting Up Python Virtual Environment"
print_status "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Install additional packages for VPS
print_status "Installing additional VPS packages..."
pip install gunicorn psutil

# Create necessary directories
print_header "Step 5: Creating Directories and Setting Permissions"
print_status "Creating logs and servers directories..."
mkdir -p logs servers

# Set permissions
print_status "Setting file permissions..."
chmod -R 755 logs/
chmod -R 755 servers/
chmod +x app.py

# Create environment file
print_header "Step 6: Creating Environment Configuration"
print_status "Creating environment configuration..."

cat > .env << EOF
FLASK_ENV=production
SECRET_KEY=flare_panel_secure_key_2025_$(date +%s)
PORT=5000
HOST=0.0.0.0
DEBUG=False
EOF

# Create systemd service
print_header "Step 7: Creating System Service"
print_status "Creating Flare Panel systemd service..."

cat > /etc/systemd/system/flare-panel.service << EOF
[Unit]
Description=Flare Panel Server Management
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/Flare-Panel
Environment=PATH=/root/Flare-Panel/venv/bin
Environment=FLASK_ENV=production
Environment=SECRET_KEY=flare_panel_secure_key_2025_$(date +%s)
ExecStart=/root/Flare-Panel/venv/bin/python app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
print_status "Enabling Flare Panel service..."
systemctl daemon-reload
systemctl enable flare-panel

# Configure firewall
print_header "Step 8: Configuring Firewall"
print_status "Configuring UFW firewall..."

# Allow SSH
ufw allow ssh

# Allow Flare Panel port
ufw allow 5000

# Enable firewall
ufw --force enable

print_status "Firewall configured successfully"

# Start Flare Panel service
print_header "Step 9: Starting Flare Panel Service"
print_status "Starting Flare Panel service..."
systemctl start flare-panel

# Wait a moment for service to start
sleep 3

# Check service status
print_status "Checking service status..."
systemctl status flare-panel --no-pager

# Test if service is running
if systemctl is-active --quiet flare-panel; then
    print_status "Flare Panel service is running successfully!"
else
    print_error "Flare Panel service failed to start"
    print_status "Checking service logs..."
    journalctl -u flare-panel --no-pager -n 20
    exit 1
fi

# Get server IP
SERVER_IP=$(curl -s ifconfig.me)

# Create management script
print_header "Step 10: Creating Management Scripts"
print_status "Creating Flare Panel management script..."

cat > /root/flare-panel-manager.sh << 'EOF'
#!/bin/bash

# Flare Panel Management Script

case "$1" in
    start)
        echo "Starting Flare Panel..."
        systemctl start flare-panel
        ;;
    stop)
        echo "Stopping Flare Panel..."
        systemctl stop flare-panel
        ;;
    restart)
        echo "Restarting Flare Panel..."
        systemctl restart flare-panel
        ;;
    status)
        echo "Flare Panel Status:"
        systemctl status flare-panel --no-pager
        ;;
    logs)
        echo "Flare Panel Logs:"
        journalctl -u flare-panel -f
        ;;
    update)
        echo "Updating Flare Panel..."
        cd /root/Flare-Panel
        systemctl stop flare-panel
        git pull origin main
        source venv/bin/activate
        pip install -r requirements.txt
        systemctl start flare-panel
        echo "Flare Panel updated successfully!"
        ;;
    backup)
        echo "Creating backup..."
        cd /root
        tar -czf flare-panel-backup-$(date +%Y%m%d_%H%M%S).tar.gz Flare-Panel/
        echo "Backup created: flare-panel-backup-$(date +%Y%m%d_%H%M%S).tar.gz"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|update|backup}"
        echo ""
        echo "Commands:"
        echo "  start   - Start Flare Panel service"
        echo "  stop    - Stop Flare Panel service"
        echo "  restart - Restart Flare Panel service"
        echo "  status  - Show Flare Panel status"
        echo "  logs    - Show Flare Panel logs"
        echo "  update  - Update Flare Panel from GitHub"
        echo "  backup  - Create backup of Flare Panel"
        exit 1
        ;;
esac
EOF

chmod +x /root/flare-panel-manager.sh

# Create quick access script
cat > /root/flare-panel-access.sh << EOF
#!/bin/bash

# Flare Panel Quick Access Script

echo "🔥 Flare Panel Quick Access"
echo "=========================="
echo ""
echo "Server IP: $SERVER_IP"
echo "Access URL: http://$SERVER_IP:5000"
echo ""
echo "Default Login Credentials:"
echo "Username: hxc"
echo "Password: 123"
echo ""
echo "Management Commands:"
echo "  ./flare-panel-manager.sh start   - Start Flare Panel"
echo "  ./flare-panel-manager.sh stop    - Stop Flare Panel"
echo "  ./flare-panel-manager.sh restart - Restart Flare Panel"
echo "  ./flare-panel-manager.sh status  - Show status"
echo "  ./flare-panel-manager.sh logs    - Show logs"
echo "  ./flare-panel-manager.sh update  - Update Flare Panel"
echo "  ./flare-panel-manager.sh backup  - Create backup"
echo ""
echo "⚠️  IMPORTANT: Change default password after first login!"
EOF

chmod +x /root/flare-panel-access.sh

# Installation complete
print_header "🎉 Flare Panel Installation Complete!"
echo ""
echo -e "${GREEN}✅ Flare Panel has been successfully installed!${NC}"
echo ""
echo -e "${BLUE}📋 Installation Summary:${NC}"
echo "  • Flare Panel installed in: /root/Flare-Panel"
echo "  • Service name: flare-panel"
echo "  • Access URL: http://$SERVER_IP:5000"
echo "  • Default username: hxc"
echo "  • Default password: 123"
echo ""
echo -e "${BLUE}🛠️  Management Commands:${NC}"
echo "  • Start:   systemctl start flare-panel"
echo "  • Stop:    systemctl stop flare-panel"
echo "  • Restart: systemctl restart flare-panel"
echo "  • Status:  systemctl status flare-panel"
echo "  • Logs:    journalctl -u flare-panel -f"
echo ""
echo -e "${BLUE}📁 Quick Access:${NC}"
echo "  • Run: ./flare-panel-access.sh"
echo "  • Management: ./flare-panel-manager.sh [command]"
echo ""
echo -e "${YELLOW}⚠️  Security Notes:${NC}"
echo "  • Change default password after first login"
echo "  • Firewall is enabled and configured"
echo "  • Service runs as root (consider changing for production)"
echo ""
echo -e "${GREEN}🚀 Flare Panel is ready to use!${NC}"
echo ""

# Show quick access info
./flare-panel-access.sh

echo ""
echo -e "${BLUE}📞 Support:${NC}"
echo "  • GitHub: https://github.com/ff-developer-ff/Flare-Panel"
echo "  • Issues: Create GitHub issue for bugs"
echo ""
echo -e "${GREEN}🔥 Flare Panel - Advanced Server Management Platform${NC}" 