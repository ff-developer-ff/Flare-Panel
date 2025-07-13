import os
import json
import subprocess
import threading
import time
import socket
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
import zipfile

app = Flask(__name__)

# Secure secret key - use environment variable if available, otherwise use default
app.secret_key = os.environ.get('SECRET_KEY', 'ff_developer_2025_secure_key_8f7d6e5c4b3a2918')

# Server manager class - Lightweight version
class ServerManager:
    def __init__(self):
        self.servers = {}
        self.servers_file = 'servers.json'
        self.load_servers()
    
    def load_servers(self):
        if os.path.exists(self.servers_file):
            try:
                with open(self.servers_file, 'r') as f:
                    data = json.load(f)
                    for name, server in data.items():
                        # Ensure console_logs exists for all servers
                        if 'console_logs' not in server:
                            server['console_logs'] = []
                        self.servers[name] = server
            except:
                self.servers = {}
    
    def save_servers(self):
        with open(self.servers_file, 'w') as f:
            json.dump(self.servers, f, indent=2)
    
    def add_server(self, name, host, port, command, server_type='custom', app_file=None):
        server = {
            'name': name,
            'host': host,
            'port': port,
            'command': command,
            'server_type': server_type,
            'status': 'stopped',
            'pid': None,
            'start_time': None,
            'console_logs': [],
            'app_file': app_file
        }
        
        self.servers[name] = server
        self.save_servers()
        return server
    
    def create_flask_server(self, name, host, port, app_file='app.py', server_type='flask'):
        # Create server directory
        server_dir = os.path.join('servers', name)
        os.makedirs(server_dir, exist_ok=True)
        
        # Set command based on server type
        if server_type == 'gunicorn':
            command = f'gunicorn --bind {host}:{port} --workers 1 {app_file}:app'
        elif server_type == 'python_http':
            command = f'python3 {app_file}'
        else:  # flask
            command = f'python3 {app_file}'
        
        return self.add_server(name, host, port, command, server_type, app_file)
    
    def get_console_logs(self, name, lines=50):
        if name in self.servers:
            server = self.servers[name]
            if 'console_logs' not in server:
                server['console_logs'] = []
            return server['console_logs'][-lines:]
        return []
    
    def add_console_log(self, name, message):
        if name in self.servers:
            server = self.servers[name]
            if 'console_logs' not in server:
                server['console_logs'] = []
            
            timestamp = datetime.now().strftime('%H:%M:%S')
            log_entry = f'[{timestamp}] {message}'
            server['console_logs'].append(log_entry)
            
            # Keep only last 100 logs (reduced for lightweight)
            if len(server['console_logs']) > 100:
                server['console_logs'] = server['console_logs'][-100:]
            
            self.save_servers()
    
    def add_welcome_message(self, name):
        """Add welcome message to console"""
        welcome_msg = f"Welcome to {name} console! Type 'help' for commands."
        self.add_console_log(name, welcome_msg)
    
    def start_server(self, name):
        if name not in self.servers:
            return False, "Server not found"
        
        server = self.servers[name]
        if server['status'] == 'running':
            return False, "Server is already running"
        
        try:
            # Create server directory if it doesn't exist
            server_dir = os.path.join('servers', name)
            os.makedirs(server_dir, exist_ok=True)
            
            # Get absolute paths
            server_dir_abs = os.path.abspath(server_dir)
            
            # Modify command to use absolute path for app file and ensure python3 is used
            command_parts = server['command'].split()
            if len(command_parts) >= 2 and command_parts[0] in ['python', 'python3']:
                # Convert python to python3 for Ubuntu compatibility
                if command_parts[0] == 'python':
                    command_parts[0] = 'python3'
                
                # This is a python command, modify the app file path
                app_file = command_parts[1]
                if not os.path.isabs(app_file):
                    app_file = os.path.join(server_dir_abs, app_file)
                command_parts[1] = app_file
            
            # Set environment variables for the Flask app
            env = os.environ.copy()
            env['PORT'] = str(server['port'])
            env['HOST'] = server['host']
            env['SERVER_NAME'] = name
            
            # Start the server process with proper working directory
            process = subprocess.Popen(
                command_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=server_dir_abs,
                env=env
            )
            
            server['pid'] = process.pid
            server['status'] = 'running'
            server['start_time'] = datetime.now().isoformat()
            self.save_servers()
            
            # Start log monitoring thread
            def monitor_logs():
                while process.poll() is None:
                    output = process.stdout.readline()
                    if output:
                        self.add_console_log(name, output.strip())
                    time.sleep(0.2)  # Reduced polling frequency
                
                # Process ended
                server['status'] = 'stopped'
                server['pid'] = None
                self.save_servers()
                
                # Get any remaining output
                remaining_output = process.stdout.read()
                if remaining_output:
                    for line in remaining_output.splitlines():
                        if line.strip():
                            self.add_console_log(name, line.strip())
            
            # Start monitoring in background thread
            monitor_thread = threading.Thread(target=monitor_logs, daemon=True)
            monitor_thread.start()
            
            self.add_console_log(name, f"Server started with PID: {process.pid}")
            return True, "Server started successfully"
            
        except Exception as e:
            self.add_console_log(name, f"Error starting server: {str(e)}")
            return False, str(e)
    
    def stop_server(self, name):
        if name not in self.servers:
            return False, "Server not found"
        
        server = self.servers[name]
        if server['status'] != 'running':
            return False, "Server is not running"
        
        try:
            pid = server['pid']
            if pid:
                # Try graceful shutdown first
                os.kill(pid, 15)  # SIGTERM
                time.sleep(2)
                
                # Force kill if still running
                try:
                    os.kill(pid, 9)  # SIGKILL
                except:
                    pass
            
            server['status'] = 'stopped'
            server['pid'] = None
            self.save_servers()
            
            self.add_console_log(name, "Server stopped")
            return True, "Server stopped successfully"
            
        except Exception as e:
            return False, str(e)
    
    def get_server_status(self, name):
        if name not in self.servers:
            return {'status': 'not_found'}
        
        server = self.servers[name]
        if server['status'] == 'running' and server['pid']:
            try:
                # Check if process is still running
                os.kill(server['pid'], 0)
                return {
                    'status': 'running',
                    'pid': server['pid'],
                    'start_time': server['start_time']
                }
            except OSError:
                # Process is dead
                server['status'] = 'stopped'
                server['pid'] = None
                self.save_servers()
                return {'status': 'stopped'}
        
        return {'status': server['status']}

# Initialize server manager
server_manager = ServerManager()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# Routes - Lightweight version
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == 'hxc' and password == '123':
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', 
                         username=session['username'],
                         servers=server_manager.servers,
                         local_ip=get_local_ip())

@app.route('/create_server', methods=['GET', 'POST'])
def create_server():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        host = request.form.get('host', '0.0.0.0')  # Default to 0.0.0.0 if not provided
        port = int(request.form['port'])
        server_type = request.form['server_type']
        
        if name in server_manager.servers:
            flash('Server name already exists', 'error')
            return redirect(url_for('create_server'))
        
        # Create server directory
        server_dir = os.path.join('servers', name)
        os.makedirs(server_dir, exist_ok=True)
        
        # Create app file based on server type
        app_file = 'app.py'
        if server_type == 'flask':
            app_content = '''from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "Flask server running!", "server": "''' + name + '''"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', ''' + str(port) + '''))
    host = os.environ.get('HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=False)
'''
        elif server_type == 'gunicorn':
            app_content = '''from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "Gunicorn server running!", "server": "''' + name + '''"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run()
'''
        else:  # python_http
            app_content = '''import http.server
import socketserver
import os
import json

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"message": "Python HTTP server running!", "server": "''' + name + '''"}
            self.wfile.write(json.dumps(response).encode())
        else:
            super().do_GET()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', ''' + str(port) + '''))
    host = os.environ.get('HOST', '0.0.0.0')
    
    with socketserver.TCPServer((host, port), CustomHandler) as httpd:
        print(f"Server running at http://{host}:{port}")
        httpd.serve_forever()
'''
        
        # Write app file
        with open(os.path.join(server_dir, app_file), 'w') as f:
            f.write(app_content)
        
        # Create server
        server_manager.create_flask_server(name, host, port, app_file, server_type)
        flash(f'Server "{name}" created successfully', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('create_server.html', username=session['username'])

@app.route('/start_server/<name>')
def start_server(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    success, message = server_manager.start_server(name)
    if success:
        flash(f'Server "{name}" started successfully', 'success')
    else:
        flash(f'Failed to start server "{name}": {message}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/stop_server/<name>')
def stop_server(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    success, message = server_manager.stop_server(name)
    if success:
        flash(f'Server "{name}" stopped successfully', 'success')
    else:
        flash(f'Failed to stop server "{name}": {message}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/delete_server/<name>')
def delete_server(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if name in server_manager.servers:
        # Stop server if running
        if server_manager.servers[name]['status'] == 'running':
            server_manager.stop_server(name)
        
        # Remove server directory
        server_dir = os.path.join('servers', name)
        if os.path.exists(server_dir):
            import shutil
            shutil.rmtree(server_dir)
        
        # Remove from server manager
        del server_manager.servers[name]
        server_manager.save_servers()
        
        flash(f'Server "{name}" deleted successfully', 'success')
    else:
        flash('Server not found', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/api/server_status/<name>')
def api_server_status(name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    status = server_manager.get_server_status(name)
    return jsonify(status)

@app.route('/console/<name>')
def server_console(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if name not in server_manager.servers:
        flash('Server not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Add welcome message if console is empty
    logs = server_manager.get_console_logs(name)
    if not logs:
        server_manager.add_welcome_message(name)
    
    return render_template('console.html', 
                         username=session['username'],
                         server_name=name)

@app.route('/api/console_logs/<name>')
def api_console_logs(name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    logs = server_manager.get_console_logs(name)
    return jsonify({'logs': logs})

@app.route('/api/send_command/<name>', methods=['POST'])
def send_command(name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    command = data.get('command', '')
    
    if command:
        # Execute the command in the server's directory
        server_dir = os.path.join('servers', name)
        if not os.path.exists(server_dir):
            return jsonify({'success': False, 'error': 'Server directory not found'})
        
        try:
            # Log the command
            server_manager.add_console_log(name, f"$ {command}")
            
            # Set up environment
            env = os.environ.copy()
            
            # Execute the command
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                cwd=server_dir,
                env=env
            )
            
            # Get output with timeout
            try:
                output, _ = process.communicate(timeout=15)  # Reduced timeout
            except subprocess.TimeoutExpired:
                process.kill()
                server_manager.add_console_log(name, "Command timed out after 15 seconds")
                return jsonify({'success': True})
            
            # Log the output
            if output:
                for line in output.splitlines():
                    if line.strip():
                        server_manager.add_console_log(name, line.strip())
            
            # Log completion
            if process.returncode == 0:
                server_manager.add_console_log(name, f"Command completed successfully")
            else:
                server_manager.add_console_log(name, f"Command failed with exit code: {process.returncode}")
            
            return jsonify({'success': True})
            
        except Exception as e:
            server_manager.add_console_log(name, f"Error executing command: {str(e)}")
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': 'No command provided'})

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('servers', exist_ok=True)
    
    print("🚀 Flare Panel (Lightweight) starting...")
    print("Default login: hxc / 123")
    print(f"Local IP: {get_local_ip()}")
    print("Access the web interface at: http://localhost:5010")
    print("For external access: http://YOUR_VPS_IP:5010")
    
    # Run on all interfaces for VPS access
    app.run(host='0.0.0.0', port=5010, debug=False, threaded=True)
