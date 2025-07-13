#!/bin/bash

echo "🚀 Installing Server Manager on Ubuntu VPS..."

# GitHub repository URL
GITHUB_REPO="https://github.com/ff-developer-ff/PYTHON-PANEL.git"
REPO_NAME="PYTHON-PANEL"

echo "📥 Downloading from GitHub: $GITHUB_REPO"

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Check Python version
echo "🐍 Checking Python version..."
python3 --version

# Install Python3 and pip3 (if not already installed)
echo "🐍 Installing Python3 and pip3..."
sudo apt install python3 python3-pip python3-venv -y

# Verify Python 3.10+ is available
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python version detected: $PYTHON_VERSION"

# Install required system packages
echo "📚 Installing required packages..."
sudo apt install git curl wget -y

# Check if we're already in the repository directory
if [ -f "app.py" ] && [ -f "install_ubuntu.sh" ]; then
    echo "📁 Already in PYTHON-PANEL directory, continuing installation..."
    CURRENT_DIR=$(pwd)
else
    # Clone or download from GitHub
    echo "📥 Downloading Server Manager from GitHub..."
    if [ -d "$REPO_NAME" ]; then
        echo "📁 Repository already exists, updating..."
        cd $REPO_NAME
        git pull origin main
    else
        echo "📁 Cloning repository..."
        git clone $GITHUB_REPO
        cd $REPO_NAME
    fi
    CURRENT_DIR=$(pwd)
fi

# Create virtual environment
echo "🔧 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip in virtual environment
echo "📦 Upgrading pip..."
pip3 install --upgrade pip

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install flask werkzeug

# Verify installation
echo "✅ Python packages installed:"
pip3 list | grep -E "(flask|werkzeug)"

# Make app.py executable
chmod +x app.py

# Generate secure secret key
echo "🔐 Generating secure secret key..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo "Secret key generated: ${SECRET_KEY:0:20}..."

# Create systemd service for auto-start
echo "⚙️ Creating systemd service..."
sudo tee /etc/systemd/system/server-manager.service > /dev/null <<EOF
[Unit]
Description=Server Manager
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$CURRENT_DIR/venv/bin
Environment=SECRET_KEY=$SECRET_KEY
ExecStart=$CURRENT_DIR/venv/bin/python3 app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable server-manager
sudo systemctl start server-manager

echo "✅ Installation complete!"
echo "⚠️ Note: Firewall configuration not included. Configure manually if needed."
echo "🐍 Python version: $PYTHON_VERSION"
echo "🌐 Server Manager is running at: http://$(curl -s ifconfig.me):5010"
echo "🔑 Login: hxc / 123"
echo "📁 Repository: $GITHUB_REPO"
echo ""
echo "📋 Useful commands:"
echo "  sudo systemctl status server-manager  # Check status"
echo "  sudo systemctl restart server-manager # Restart service"
echo "  sudo systemctl stop server-manager    # Stop service"
echo "  sudo journalctl -u server-manager -f  # View logs"
echo ""
echo "🔄 To update from GitHub:"
echo "  cd $REPO_NAME && git pull origin main"
echo ""
echo "🐍 Python commands you can run in console:"
echo "  python3 --version    # Check Python version"
echo "  pip3 list           # List installed packages"
echo "  python3 app.py      # Run Python scripts" 