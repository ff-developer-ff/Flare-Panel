# 🚀 Server Manager for Ubuntu VPS

A Python server management web application optimized for Ubuntu VPS deployment.

## 🌟 Features

- **Python Server Management** - Create and manage Python Flask servers
- **Real-time Console** - Execute commands directly from web interface
- **File Management** - Upload, delete, and manage files per server
- **VPS Optimized** - Designed specifically for Ubuntu VPS environments
- **Auto-start Service** - Runs as systemd service for reliability

## 📋 Requirements

- Ubuntu 18.04+ or Ubuntu 20.04+
- Python 3.8+
- sudo privileges

## 🚀 Quick Installation

### Method 1: Automatic Installation
```bash
# Download and run installation script
wget https://raw.githubusercontent.com/ff-developer-ff/PYTHON-PANEL/main/install_ubuntu.sh
chmod +x install_ubuntu.sh
./install_ubuntu.sh
```

### Method 2: Direct from GitHub
```bash
# Clone repository and install
git clone https://github.com/ff-developer-ff/PYTHON-PANEL.git
cd PYTHON-PANEL
chmod +x install_ubuntu.sh
./install_ubuntu.sh
```

### Method 3: One-Line Installation
```bash
curl -sSL https://raw.githubusercontent.com/ff-developer-ff/PYTHON-PANEL/main/install_ubuntu.sh | bash
```

### Method 2: Manual Installation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python3 and dependencies
sudo apt install python3 python3-pip python3-venv git curl wget -y

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip3 install -r requirements.txt

# Run the application
python3 app.py
```

## 🔧 Configuration

### Default Login
- **Username:** hxc
- **Password:** 123

### Port Configuration
- **Main Interface:** Port 5010
- **Server Ports:** Configurable (5000-9999)

### Firewall Setup (Optional)
```bash
# Allow port 5010 (if needed)
sudo ufw allow 5010

# Enable firewall (if needed)
sudo ufw enable
```

## 📁 Directory Structure
```
PYTHON-PANEL/
├── app.py                 # Main application
├── requirements.txt       # Python dependencies
├── install_ubuntu.sh      # Installation script
├── servers/              # Individual server directories
├── logs/                 # Server logs
└── templates/            # HTML templates
```

## 🔗 GitHub Repository
- **Repository:** https://github.com/ff-developer-ff/PYTHON-PANEL.git
- **Direct Download:** `git clone https://github.com/ff-developer-ff/PYTHON-PANEL.git`

## 🎮 Usage

### 1. Access Web Interface
- Open browser: `http://YOUR_VPS_IP:5010`
- Login with: hxc / 123

### 2. Create a Server
- Click "Create Server"
- Enter server name and port
- Click "Create"

### 3. Manage Server
- **Start/Stop:** Use Run/Stop buttons
- **Console:** Click Console button to access command line
- **Files:** Click Files button to manage server files

### 4. Console Commands
Common Ubuntu commands you can run:
```bash
python3 --version          # Check Python version
pip3 install package       # Install Python packages
ls -la                     # List files
cd folder                  # Change directory
sudo apt update           # Update system packages
nano file.py              # Edit files
```

## 🔧 Systemd Service Management

### Check Status
```bash
sudo systemctl status server-manager
```

### Start/Stop/Restart
```bash
sudo systemctl start server-manager
sudo systemctl stop server-manager
sudo systemctl restart server-manager
```

### View Logs
```bash
sudo journalctl -u server-manager -f
```

### Enable Auto-start
```bash
sudo systemctl enable server-manager
```

## 🛠️ Troubleshooting

### Port Already in Use
```bash
# Find process using port 5000
sudo lsof -i :5000

# Kill process
sudo kill -9 PID
```

### Permission Issues
```bash
# Fix permissions
sudo chown -R $USER:$USER /path/to/server-manager
chmod +x app.py
```

### Python Not Found
```bash
# Install Python3
sudo apt install python3 python3-pip -y

# Check Python version
python3 --version
```

## 🔒 Security Notes

- Change default password after installation
- Use HTTPS in production
- Configure firewall properly
- Keep system updated

## 📞 Support

For issues and questions:
- Check logs: `sudo journalctl -u server-manager -f`
- Console output: Available in web interface
- System logs: `/var/log/syslog`

---

**Made for Ubuntu VPS deployment** 🐧 