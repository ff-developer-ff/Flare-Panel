# Python Server Management System

A web-based Python server management application built with Flask that allows you to start, stop, and monitor multiple Python servers from a beautiful web interface. Perfect for VPS hosting and development environments.

## Features

- 🔐 **Secure Login System** - User authentication with session management
- 🖥️ **Server Management** - Start, stop, and monitor multiple servers
- 🚀 **Quick Server Creation** - Create Python servers with one-click templates
- 🐍 **Gunicorn Support** - Flask applications with Gunicorn WSGI server
- 📁 **File Management** - Upload, create folders, and manage files
- 📊 **Real-time Dashboard** - Beautiful interface with server status cards
- 🌐 **Host & Port Management** - Configure servers with custom host IP and ports
- 📝 **Server Logs** - Track server start/stop events
- 🔄 **Auto-refresh** - Dashboard automatically updates every 30 seconds
- 📱 **Responsive Design** - Works on desktop and mobile devices
- 🗑️ **Server Deletion** - Remove servers with confirmation

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python app.py
   ```

3. **Access the web interface:**
   - Open your browser and go to: `http://localhost:5000`
   - Or use your local IP address: `http://YOUR_IP:5000`

## Default Login

- **Username:** `hxc`
- **Password:** `123`

## How to Use

### 1. Login
- Access the application and login with the default credentials
- You can change the password in the `app.py` file

### 2. Create a Server
- Click "Create Server" button for quick setup
- Choose server type:
  - **Flask + Gunicorn** - Production Python Flask with Gunicorn WSGI
  - **Flask Development** - Python Flask development server
  - **Python HTTP** - Simple Python HTTP server
- Fill in the details and create

### 3. File Management
- Click "File Manager" button to manage files
- Upload files to any directory
- Create new folders
- Delete files and folders
- Navigate through directories with breadcrumbs

### 4. Add Custom Server
- Click "Custom Server" button for advanced setup
- Fill in the details:
  - **Server Name:** A friendly name for your server
  - **Host IP:** The IP address (e.g., 127.0.0.1, 0.0.0.0)
  - **Port:** The port number (1-65535)
  - **Start Command:** The command to start your server (e.g., `python myapp.py`)

### 5. Manage Servers
- **Start Server:** Click the green "Start" button
- **Stop Server:** Click the red "Stop" button
- **Delete Server:** Click the trash icon (server will be stopped first)

### 6. Monitor Status
- Dashboard shows real-time server status
- View running/stopped server counts
- See local IP address
- Auto-refresh every 30 seconds

## Python Server Types

The system supports multiple Python server types with automatic configuration:

### Flask + Gunicorn
- **Command:** `gunicorn --bind 0.0.0.0:8080 --workers 2 app.py:app`
- **Features:** Production-ready WSGI server with multiple workers
- **Best for:** Production Python Flask applications

### Flask Development
- **Command:** `python -m flask run --host=0.0.0.0 --port=8080`
- **Features:** Flask development server with auto-reload
- **Best for:** Development and testing

### Python HTTP
- **Command:** `python -m http.server 9000 --bind 0.0.0.0`
- **Features:** Simple static file server
- **Best for:** Static websites and file sharing

## Example Server Commands

For custom servers, here are some example commands:

### Custom Python Flask Server
```
python -m flask run --host=0.0.0.0 --port=8080
```

### Custom Python Django Server
```
python manage.py runserver 0.0.0.0:8000
```

### Custom Python FastAPI Server
```
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Custom Python Simple HTTP Server
```
python -m http.server 9000
```

## File Structure

```
PYTHON PNL/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── README.md                # This file
├── servers.json             # Server configurations (created automatically)
├── example_flask_app.py     # Example Flask application
└── templates/               # HTML templates (created automatically)
    ├── login.html
    ├── dashboard.html
    ├── create_server.html
    ├── add_server.html
    └── file_manager.html
```

## Security Notes

- Change the default `secret_key` in `app.py`
- Change the default admin password
- Consider adding more users with different roles
- For production use, implement proper user management

## Troubleshooting

### Server won't start?
- Check if the command is correct
- Ensure the server application exists
- Check if the port is already in use
- Verify file paths in the command

### Can't access from other devices?
- Make sure the Flask app is running on `0.0.0.0:5000`
- Check your firewall settings
- Use your computer's local IP address

### Permission errors?
- Run the application with appropriate permissions
- Some commands may require administrator privileges

## Customization

### Adding More Users
Edit the `users` dictionary in `app.py`:
```python
users = {
    'admin': {
        'password': hashlib.sha256('admin123'.encode()).hexdigest(),
        'role': 'admin'
    },
    'user1': {
        'password': hashlib.sha256('password123'.encode()).hexdigest(),
        'role': 'user'
    }
}
```

### Changing Port
Edit the last line in `app.py`:
```python
app.run(host='0.0.0.0', port=YOUR_PORT, debug=True)
```

## License

This project is open source and available under the MIT License. 