# 🔐 Security Configuration

## Secret Key Management

### Current Secret Key
- **Default:** `ff_developer_2025_secure_key_8f7d6e5c4b3a2918`
- **Environment Variable:** `SECRET_KEY`

### How to Change Secret Key

#### Method 1: Environment Variable (Recommended)
```bash
# Set environment variable
export SECRET_KEY="your_very_secure_secret_key_here"

# Run application
python3 app.py
```

#### Method 2: Systemd Service (Automatic)
The installation script automatically generates a secure secret key and sets it in the systemd service.

#### Method 3: Manual Change
Edit `app.py` line 13:
```python
app.secret_key = 'your_new_secure_secret_key_here'
```

### Generate Secure Secret Key
```bash
# Using Python
python3 -c "import secrets; print(secrets.token_hex(32))"

# Using OpenSSL
openssl rand -hex 32
```

## Security Best Practices

### 1. Change Default Credentials
- **Default Login:** hxc / 123
- **Change in:** `app.py` lines 200-210

### 2. Use HTTPS in Production
```bash
# Install SSL certificate
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com
```

### 3. Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw allow 8443
sudo ufw allow ssh
sudo ufw enable
```

### 4. Regular Updates
```bash
# Update system
sudo apt update && sudo apt upgrade

# Update application
cd PYTHON-PANEL && git pull origin main
```

### 5. Monitor Logs
```bash
# View application logs
sudo journalctl -u server-manager -f

# View system logs
sudo tail -f /var/log/syslog
```

## Security Checklist

- [ ] Change default secret key
- [ ] Change default login credentials
- [ ] Configure firewall
- [ ] Enable HTTPS (production)
- [ ] Regular system updates
- [ ] Monitor access logs
- [ ] Backup configuration files

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | Auto-generated |
| `PORT` | Server port | 8443 |
| `HOST` | Server host | 0.0.0.0 |

## File Permissions

```bash
# Secure file permissions
chmod 600 app.py
chmod 600 servers.json
chmod 700 logs/
chmod 700 servers/
```

---

**⚠️ Important:** Always change default credentials before production use! 