#!/bin/bash

# 🔥 Flare Panel One-Line Installation Script
# Run with: curl -sSL https://raw.githubusercontent.com/ff-developer-ff/Flare-Panel/main/flare.sh | bash

echo "🔥 Flare Panel - One-Line Installation"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}❌ This script must be run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Starting Flare Panel installation...${NC}"

# Update system
echo -e "${BLUE}📦 Updating system packages...${NC}"
apt update -y && apt upgrade -y

# Install required packages
echo -e "${BLUE}📦 Installing required packages...${NC}"
apt install -y python3 python3-pip python3-venv git curl wget unzip tar gzip htop nano vim ufw

# Verify Python
echo -e "${BLUE}🐍 Verifying Python installation...${NC}"
python3 --version

# Navigate to root and clone Flare Panel
echo -e "${BLUE}📥 Cloning Flare Panel...${NC}"
cd /root
rm -rf Flare-Panel 2>/dev/null
git clone https://github.com/ff-developer-ff/Flare-Panel.git
cd Flare-Panel

# Setup Python environment
echo -e "${BLUE}🔧 Setting up Python environment...${NC}"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psutil

# Create directories and set permissions
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p logs servers
chmod -R 755 logs/ servers/
chmod +x app.py

# Create environment file
echo -e "${BLUE}⚙️ Creating configuration...${NC}"
cat > .env << EOF
FLASK_ENV=production
SECRET_KEY=flare_panel_secure_key_2025_$(date +%s)
PORT=5000
HOST=0.0.0.0
DEBUG=False
EOF

# Create systemd service
echo -e "${BLUE}🔧 Creating system service...${NC}"
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

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
echo -e "${BLUE}🚀 Starting Flare Panel service...${NC}"
systemctl daemon-reload
systemctl enable flare-panel
systemctl start flare-panel

# Configure firewall
echo -e "${BLUE}🛡️ Configuring firewall...${NC}"
ufw allow ssh
ufw allow 5000
ufw --force enable

# Wait for service to start
sleep 3

# Get server IP
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_VPS_IP")

# Check if service is running
if systemctl is-active --quiet flare-panel; then
    echo ""
    echo -e "${GREEN}🎉 Flare Panel Installation Complete!${NC}"
    echo ""
    echo -e "${BLUE}📋 Access Information:${NC}"
    echo "  • URL: http://$SERVER_IP:5000"
    echo "  • Username: hxc"
    echo "  • Password: 123"
    echo ""
    echo -e "${BLUE}🛠️ Management Commands:${NC}"
    echo "  • Start:   systemctl start flare-panel"
    echo "  • Stop:    systemctl stop flare-panel"
    echo "  • Restart: systemctl restart flare-panel"
    echo "  • Status:  systemctl status flare-panel"
    echo "  • Logs:    journalctl -u flare-panel -f"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Change default password after first login!${NC}"
    echo ""
    echo -e "${GREEN}🔥 Flare Panel is ready to use!${NC}"
else
    echo -e "${RED}❌ Installation failed. Check logs:${NC}"
    journalctl -u flare-panel --no-pager -n 10
    exit 1
fi 