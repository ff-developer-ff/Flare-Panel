# 🔥 Flare Panel - Complete Guide

![Flare Panel](https://img.shields.io/badge/Flare%20Panel-Advanced%20Server%20Management-orange?style=for-the-badge&logo=fire)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-green?style=for-the-badge&logo=flask)
![Ubuntu](https://img.shields.io/badge/Ubuntu-20.04+-orange?style=for-the-badge&logo=ubuntu)

## 📋 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [VPS Requirements](#vps-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Server Types](#server-types)
- [File Management](#file-management)
- [Console Commands](#console-commands)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)

---

## 🚀 Overview

**Flare Panel** is a modern, enterprise-grade server management platform designed for Python hosting and server administration. Built with Flask and featuring a sleek dark theme with glassmorphism effects, Flare Panel provides comprehensive server management capabilities similar to Pterodactyl but specifically optimized for Python applications.

### Key Highlights
- **Modern UI/UX**: Dark theme with orange accents and glassmorphism effects
- **Real-time Console**: Live command execution and log monitoring
- **File Management**: Advanced file browser with code editor
- **Multi-Server Support**: Manage multiple Python servers simultaneously
- **VPS Optimized**: Designed specifically for Ubuntu VPS environments

---

## ✨ Features

### 🎨 User Interface
- **Dark Theme**: Professional black gradient background
- **Glassmorphism**: Modern glass-like effects with backdrop blur
- **Responsive Design**: Works on desktop and mobile devices
- **Smooth Animations**: Hover effects and transitions
- **Fire Icon**: Branded with fire icon for Flare Panel identity

### 🖥️ Server Management
- **Multiple Server Types**: Flask, Gunicorn, Python HTTP Server
- **Real-time Status**: Live server status monitoring
- **Start/Stop Control**: Easy server control from console
- **Process Management**: PID tracking and process monitoring
- **Port Management**: Dynamic port allocation and management

### 📁 File Management
- **File Browser**: Navigate server directories
- **Code Editor**: Built-in CodeMirror editor with syntax highlighting
- **File Operations**: Upload, download, delete, rename, move
- **Folder Management**: Create and manage directories
- **Archive Support**: Extract ZIP, TAR.GZ, RAR files

### 💻 Console Features
- **Real-time Logs**: Live server output monitoring
- **Command Execution**: Execute commands directly on servers
- **Command History**: Arrow key navigation through command history
- **Auto-refresh**: Automatic log updates every second
- **Error Handling**: Comprehensive error reporting

### 🔧 Advanced Features
- **Template System**: Pre-built server templates
- **Environment Variables**: Automatic environment setup
- **Log Management**: Centralized log storage
- **Backup System**: Server configuration backups
- **Multi-user Support**: Session-based authentication

---

## 💻 VPS Requirements

### Minimum Requirements
- **OS**: Ubuntu 20.04 LTS or higher
- **RAM**: 1 GB (2 GB recommended)
- **Storage**: 10 GB available space
- **CPU**: 1 vCPU (2 vCPU recommended)
- **Network**: Stable internet connection
- **Python**: Python 3.10+ (3.10.12 tested)

### Recommended Requirements
- **OS**: Ubuntu 22.04 LTS
- **RAM**: 4 GB or higher
- **Storage**: 20 GB SSD
- **CPU**: 2+ vCPU cores
- **Network**: High-speed connection
- **Python**: Python 3.11+ for best performance

### System Dependencies
```bash
# Required system packages
- python3 (3.10+)
- python3-pip
- python3-venv
- git
- curl
- wget
- unzip
- tar
- gzip
```

---

## 🛠️ Installation

### Quick Installation (Ubuntu VPS)

#### Step 1: System Update
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv git curl wget unzip tar gzip

# Verify Python version
python3 --version
```

#### Step 2: Clone Flare Panel
```bash
# Navigate to root directory
cd /root

# Clone Flare Panel repository
git clone https://github.com/ff-developer-ff/Flare-Panel.git

# Navigate to Flare Panel directory
cd Flare-Panel

# Check contents
ls -la
```

#### Step 3: Python Environment Setup
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install additional packages for VPS
pip install gunicorn psutil
```

#### Step 4: Create Directories
```bash
# Create necessary directories
mkdir -p logs servers

# Set permissions
chmod -R 755 logs/
chmod -R 755 servers/
chmod +x app.py
```

#### Step 5: Configuration
```bash
# Set environment variables
export FLASK_ENV=production
export SECRET_KEY="flare_panel_secure_key_2025_$(date +%s)"

# Create environment file
cat > .env << EOF
FLASK_ENV=production
SECRET_KEY=flare_panel_secure_key_2025_$(date +%s)
PORT=5000
HOST=0.0.0.0
DEBUG=False
EOF
```

#### Step 6: Test Installation
```bash
# Test Flare Panel
python3 app.py

# If successful, stop with Ctrl+C and continue to service setup
```

### Production Setup

#### Step 1: Create System Service
```bash
# Create systemd service file
sudo tee /etc/systemd/system/flare-panel.service > /dev/null << EOF
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
```

#### Step 2: Enable and Start Service
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable flare-panel

# Start service
sudo systemctl start flare-panel

# Check status
sudo systemctl status flare-panel

# View logs
sudo journalctl -u flare-panel -f
```

#### Step 3: Firewall Configuration
```bash
# Allow Flare Panel port
sudo ufw allow 5000

# Allow SSH (if not already allowed)
sudo ufw allow ssh

# Enable firewall
sudo ufw enable

# Check firewall status
sudo ufw status
```

---

## ⚙️ Configuration

### Environment Variables
```bash
# Required
SECRET_KEY=your-secure-secret-key
FLASK_ENV=production

# Optional
PORT=5000
HOST=0.0.0.0
DEBUG=False
```

### Default Login Credentials
```
Username: hxc
Password: 123
```

**⚠️ Important**: Change these credentials after first login!

### Directory Structure
```
Flare-Panel/
├── app.py                 # Main application
├── requirements.txt       # Python dependencies
├── servers.json          # Server configurations
├── logs/                 # Server logs
├── servers/              # Server directories
├── templates/            # HTML templates
└── venv/                 # Virtual environment
```

---

## 🎯 Usage

### Accessing Flare Panel
1. Open your browser
2. Navigate to `http://your-vps-ip:5000`
3. Login with default credentials
4. Start managing your servers!

### Creating Your First Server
1. Click "Create Flare Panel Server"
2. Choose server type (Flask, Gunicorn, Python HTTP)
3. Set server name and port
4. Click "Create Server"
5. Go to Console to start the server

### Managing Servers
- **Dashboard**: Overview of all servers
- **Console**: Real-time server control and logs
- **Files**: File management for each server
- **Start/Stop**: Control server status

---

## 🖥️ Server Types

### 1. Flare Panel + Python
- **Command**: `python3 app.py`
- **Use Case**: Development and testing
- **Features**: Hot reload, debug mode

### 2. Flare Panel + Gunicorn
- **Command**: `gunicorn --bind 0.0.0.0:port --workers 2 app:app`
- **Use Case**: Production deployment
- **Features**: Multi-worker, load balancing

### 3. Flare Panel HTTP Server
- **Command**: `python3 app.py`
- **Use Case**: Lightweight applications
- **Features**: Socket-based, minimal overhead

---

## 📁 File Management

### Supported File Types
- **Code Files**: `.py`, `.js`, `.html`, `.css`, `.txt`, `.json`, `.xml`, `.md`
- **Scripts**: `.sh`, `.conf`, `.ini`, `.cfg`
- **Archives**: `.zip`, `.tar.gz`, `.rar`

### File Operations
- **Upload**: Drag & drop or click to upload
- **Download**: Direct file download
- **Edit**: Built-in code editor with syntax highlighting
- **Delete**: Secure file deletion with confirmation
- **Rename**: In-place file renaming
- **Move**: File and folder relocation
- **Extract**: Archive extraction

### Code Editor Features
- **Syntax Highlighting**: Support for multiple languages
- **Theme Toggle**: Light/dark theme switching
- **Auto-save**: Automatic file saving
- **Line Numbers**: Code line numbering
- **Search/Replace**: Find and replace functionality

---

## 💻 Console Commands

### Available Commands
```bash
# Python commands
python3 script.py
python3 --version
pip3 install package
pip3 list

# System commands
ls
cd folder
pwd
echo "text"
cat file.txt
nano file.txt

# Package management
sudo apt update
sudo apt install package
sudo apt upgrade

# Process management
ps aux
kill process_id
top
htop

# Network commands
netstat -tulpn
curl url
wget url
ping host
```

### Command Features
- **Real-time Execution**: Commands run immediately
- **Output Capture**: All output captured and displayed
- **Error Handling**: Comprehensive error reporting
- **History Navigation**: Arrow keys for command history
- **Auto-completion**: Tab completion for file paths

---

## 🔒 Security

### Authentication
- **Session-based**: Secure session management
- **Password Protection**: Encrypted password storage
- **Login Required**: All pages require authentication

### File Security
- **Path Validation**: Prevents directory traversal
- **File Type Restrictions**: Limited to safe file types
- **Size Limits**: File upload size restrictions

### Network Security
- **Firewall Ready**: Compatible with UFW firewall
- **Port Management**: Configurable port settings
- **HTTPS Ready**: Supports SSL/TLS configuration

---

## 🛠️ Troubleshooting

### Common Issues

#### 1. Server Won't Start
```bash
# Check Python version
python3 --version

# Install missing packages
pip3 install -r requirements.txt

# Check port availability
netstat -tulpn | grep :5000
```

#### 2. Permission Errors
```bash
# Fix file permissions
chmod +x app.py
chmod -R 755 servers/
chmod -R 755 logs/
```

#### 3. Module Not Found
```bash
# Install missing modules
pip3 install protobuf requests flask gunicorn pycryptodome

# Check Python path
which python3
python3 -c "import sys; print(sys.path)"
```

#### 4. Service Won't Start
```bash
# Check service status
sudo systemctl status flare-panel

# View service logs
sudo journalctl -u flare-panel -f

# Restart service
sudo systemctl restart flare-panel
```

### Log Locations
- **Application Logs**: `logs/` directory
- **System Logs**: `/var/log/syslog`
- **Service Logs**: `sudo journalctl -u flare-panel`

### Performance Optimization
```bash
# Increase file descriptors
ulimit -n 65536

# Optimize Python
export PYTHONOPTIMIZE=1

# Use Gunicorn for production
gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class gevent app:app
```

---

## 📚 API Reference

### Server Management Endpoints
```
GET  /api/server_status/<name>     # Get server status
POST /api/send_command/<name>      # Execute command
GET  /api/console_logs/<name>      # Get console logs
```

### File Management Endpoints
```
GET  /api/read_file               # Read file content
POST /api/save_file               # Save file content
POST /upload                      # Upload file
GET  /delete_file                 # Delete file
```

### Authentication Endpoints
```
GET  /login                       # Login page
POST /login                       # Login action
GET  /logout                      # Logout
```

---

## 🛠️ Management Commands

### Service Management
```bash
# Start Flare Panel
sudo systemctl start flare-panel

# Stop Flare Panel
sudo systemctl stop flare-panel

# Restart Flare Panel
sudo systemctl restart flare-panel

# Check status
sudo systemctl status flare-panel

# View logs
sudo journalctl -u flare-panel -f
```

### Update Flare Panel
```bash
# Navigate to Flare Panel directory
cd /root/Flare-Panel

# Stop service
sudo systemctl stop flare-panel

# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Update dependencies
pip install -r requirements.txt

# Start service
sudo systemctl start flare-panel
```

### Backup and Restore
```bash
# Backup Flare Panel
cd /root
tar -czf flare-panel-backup-$(date +%Y%m%d).tar.gz Flare-Panel/

# Restore Flare Panel
cd /root
tar -xzf flare-panel-backup-YYYYMMDD.tar.gz
```

---

## 📊 System Monitoring

### Check Resource Usage
```bash
# Check CPU and memory usage
htop

# Check disk usage
df -h

# Check Flare Panel logs
tail -f /root/Flare-Panel/logs/*.log
```

### Performance Optimization
```bash
# Increase file descriptors
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# Optimize Python
export PYTHONOPTIMIZE=1
```

---

## ✅ Quick Start Commands

### One-Line Installation
```bash
# Complete installation in one go
cd /root && git clone https://github.com/ff-developer-ff/Flare-Panel.git && cd Flare-Panel && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && mkdir -p logs servers && chmod +x app.py && python3 app.py
```

### Service Setup
```bash
# Create and start service
sudo tee /etc/systemd/system/flare-panel.service > /dev/null << EOF
[Unit]
Description=Flare Panel Server Management
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/Flare-Panel
Environment=PATH=/root/Flare-Panel/venv/bin
ExecStart=/root/Flare-Panel/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload && sudo systemctl enable flare-panel && sudo systemctl start flare-panel
```

### Firewall Setup
```bash
# Quick firewall setup
sudo ufw allow 5000 && sudo ufw allow ssh && sudo ufw enable
```

---

## 🎉 Installation Complete!

Your Flare Panel is now installed and running! 

**Access URL**: `http://your-vps-ip:5000`
**Default Login**: `hxc` / `123`

**Remember to change the default password after first login!**

---

## 📞 Support

### Getting Help
- **Documentation**: Check this guide first
- **Issues**: Create GitHub issue for bugs
- **Discussions**: Use GitHub discussions for questions

### Community
- **GitHub**: [https://github.com/ff-developer-ff/Flare-Panel](https://github.com/ff-developer-ff/Flare-Panel)
- **Repository**: ff-developer-ff/Flare-Panel

---

**🔥 Flare Panel** - Advanced Server Management Platform

*Built with ❤️ for the Python community*

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*Last updated: January 2025* 

## 🔥 **One-Line Flare Panel Installation**

### **📋 Curl Command:**
```bash
<code_block_to_apply_changes_from>
```

### **🚀 With Sudo (Recommended):**
```bash
curl -sSL https://raw.githubusercontent.com/ff-developer-ff/Flare-Panel/main/flare.sh | sudo bash
```

## 📋 **What the Script Does:**

### **1. System Setup**
- ✅ Updates Ubuntu packages
- ✅ Installs Python 3, git, curl, wget, and other tools
- ✅ Verifies Python installation

### **2. Flare Panel Installation**
- ✅ Clones from GitHub: `https://github.com/ff-developer-ff/Flare-Panel.git`
- ✅ Creates Python virtual environment
- ✅ Installs all dependencies
- ✅ Creates logs and servers directories

### **3. Service Setup**
- ✅ Creates systemd service (`flare-panel.service`)
- ✅ Enables and starts the service
- ✅ Configures UFW firewall

### **4. Final Setup**
- ✅ Shows access information
- ✅ Displays management commands
- ✅ Verifies installation success

## ✅ **After Installation:**

### **Access Information:**
- **URL**: `http://your-vps-ip:5000`
- **Username**: `hxc`
- **Password**: `123`

### **Management Commands:**
```bash
# Start Flare Panel
systemctl start flare-panel

# Stop Flare Panel
systemctl stop flare-panel

# Restart Flare Panel
systemctl restart flare-panel

# Check status
systemctl status flare-panel

# View logs
journalctl -u flare-panel -f
```

## 🎯 **Key Features:**

- ✅ **One Command**: Complete installation with single curl command
- ✅ **Automatic Setup**: No manual configuration needed
- ✅ **Service Management**: Systemd service with auto-restart
- ✅ **Firewall Setup**: Automatic UFW configuration
- ✅ **Error Handling**: Comprehensive error checking
- ✅ **Colored Output**: Professional installation feedback
- ✅ **IP Detection**: Automatically detects server IP

## 🚨 **Important Notes:**

1. **Run as Root**: The script must be run with sudo or as root
2. **Internet Required**: Needs internet connection to clone repository
3. **Ubuntu Only**: Designed for Ubuntu VPS systems
4. **Change Password**: Remember to change default password after login

The script is now ready for one-line installation! Just run the curl command and Flare Panel will be installed automatically. 🔥 