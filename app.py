import os
import json
import subprocess
import threading
import time
import socket
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from werkzeug.utils import secure_filename
import zipfile

app = Flask(__name__)

# Secure secret key - use environment variable if available, otherwise use default
import os
app.secret_key = os.environ.get('SECRET_KEY', 'ff_developer_2025_secure_key_8f7d6e5c4b3a2918')

# Server manager class
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
        # Create logs directory for this server
        logs_dir = os.path.join('logs', name)
        os.makedirs(logs_dir, exist_ok=True)
        
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
        
        # Create logs directory for this server
        logs_dir = os.path.join('logs', name)
        os.makedirs(logs_dir, exist_ok=True)
        
        # Set command based on server type
        if server_type == 'gunicorn':
            command = f'gunicorn --bind {host}:{port} --workers 2 {app_file}:app'
        elif server_type == 'python_http':
            command = f'python3 {app_file}'
        else:  # flask
            command = f'python3 {app_file}'
        
        return self.add_server(name, host, port, command, server_type, app_file)
    
    def get_console_logs(self, name, lines=100):
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
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f'[{timestamp}] {message}'
            server['console_logs'].append(log_entry)
            
            # Keep only last 1000 logs
            if len(server['console_logs']) > 1000:
                server['console_logs'] = server['console_logs'][-1000:]
            
            self.save_servers()
    
    def add_welcome_message(self, name):
        """Add welcome message to console"""
        welcome_msg = f"Welcome to {name} console on Ubuntu VPS! You can run any command here."
        self.add_console_log(name, welcome_msg)
        self.add_console_log(name, "Try: python3 --version | ls | pip3 list | pip3 install package | sudo apt update")
    
    def start_server(self, name):
        if name not in self.servers:
            return False, "Server not found"
        
        server = self.servers[name]
        if server['status'] == 'running':
            return False, "Server is already running"
        
        try:
            # Create logs directory
            logs_dir = os.path.join('logs', name)
            os.makedirs(logs_dir, exist_ok=True)
            
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
            
            # Add Python to PATH for Linux/Ubuntu
            if os.name != 'nt':  # Linux/Unix systems
                python_paths = [
                    "/usr/bin",
                    "/usr/local/bin",
                    "/usr/local/sbin",
                    "/opt/python3/bin",
                    "/home/{}/.local/bin".format(os.getenv('USER', '')),
                    "/snap/bin"
                ]
                
                current_path = env.get('PATH', '')
                for python_path in python_paths:
                    if os.path.exists(python_path) and python_path not in current_path:
                        current_path = f"{python_path}:{current_path}"
                
                env['PATH'] = current_path
            
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
                    time.sleep(0.1)
                
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
                
                self.add_console_log(name, f"Server process ended with code {process.returncode}")
                if process.returncode != 0:
                    self.add_console_log(name, "Server failed to start. Check the logs above for errors.")
            
            thread = threading.Thread(target=monitor_logs, daemon=True)
            thread.start()
            
            self.add_console_log(name, f"Server started with PID {process.pid}")
            self.add_console_log(name, f"Working directory: {server_dir_abs}")
            self.add_console_log(name, f"Command: {' '.join(command_parts)}")
            return True, "Server started successfully"
            
        except Exception as e:
            return False, f"Failed to start server: {str(e)}"
    
    def stop_server(self, name):
        if name not in self.servers:
            return False, "Server not found"
        
        server = self.servers[name]
        if server['status'] != 'running':
            return False, "Server is not running"
        
        try:
            if server['pid']:
                # Try graceful shutdown first
                os.kill(server['pid'], 15)  # SIGTERM
                time.sleep(2)
                
                # Force kill if still running
                if self.get_server_status(name)['status'] == 'running':
                    os.kill(server['pid'], 9)  # SIGKILL
            
            server['status'] = 'stopped'
            server['pid'] = None
            self.save_servers()
            self.add_console_log(name, "Server stopped")
            return True, "Server stopped successfully"
            
        except Exception as e:
            return False, f"Failed to stop server: {str(e)}"
    
    def get_server_status(self, name):
        if name not in self.servers:
            return {'status': 'not_found'}
        
        server = self.servers[name]
        if server['status'] == 'running' and server['pid']:
            try:
                # Check if process is still running
                os.kill(server['pid'], 0)
                return {'status': 'running', 'pid': server['pid']}
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

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Simple authentication (in production, use proper password hashing)
        if username == 'hxc' and password == '123':
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', 
                         username=session['username'],
                         servers=server_manager.servers,
                         local_ip=get_local_ip())

@app.route('/add_server', methods=['GET', 'POST'])
def add_server():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        host = request.form['host']
        port = int(request.form['port'])
        command = request.form['command']
        
        if name in server_manager.servers:
            flash('Server name already exists', 'error')
        else:
            server_manager.add_server(name, host, port, command)
            flash('Server added successfully', 'success')
            return redirect(url_for('dashboard'))
    
    return render_template('add_server.html', username=session['username'])

@app.route('/create_server', methods=['GET', 'POST'])
def create_server():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        port = int(request.form['port'])
        app_file = request.form['app_file']
        server_type = request.form.get('server_type', 'flask')
        
        if name in server_manager.servers:
            flash('Server name already exists', 'error')
        else:
            # Create the server
            server = server_manager.create_flask_server(name, '0.0.0.0', port, app_file, server_type)
            
            # Create the server app file
            server_dir = os.path.join('servers', name)
            app_path = os.path.join(server_dir, app_file)
            
            # Select template based on server type
            template_name = 'flask_app_template.py'
            if server_type == 'gunicorn':
                template_name = 'gunicorn_app_template.py'
            elif server_type == 'python_http':
                template_name = 'python_http_template.py'
            
            template_path = os.path.join('templates', template_name)
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                
                with open(app_path, 'w', encoding='utf-8') as f:
                    f.write(template_content)
                
                flash(f'{server_type.title()} server created successfully with {app_file}', 'success')
            else:
                flash(f'{server_type.title()} server created but template not found', 'warning')
            
            return redirect(url_for('dashboard'))
    
    return render_template('create_server.html', username=session['username'])

@app.route('/start_server/<name>')
def start_server(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    success, message = server_manager.start_server(name)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('dashboard'))

@app.route('/stop_server/<name>')
def stop_server(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    success, message = server_manager.stop_server(name)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('dashboard'))

@app.route('/delete_server/<name>')
def delete_server(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if name in server_manager.servers:
        # Stop server if running
        if server_manager.servers[name]['status'] == 'running':
            server_manager.stop_server(name)
        
        # Delete server
        del server_manager.servers[name]
        server_manager.save_servers()
        
        # Remove logs directory
        logs_dir = f'logs/{name}'
        if os.path.exists(logs_dir):
            import shutil
            shutil.rmtree(logs_dir)
        
        flash('Server deleted successfully', 'success')
    else:
        flash('Server not found', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/api/server_status/<name>')
def api_server_status(name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    status = server_manager.get_server_status(name)
    return jsonify(status)

@app.route('/files')
def file_manager():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    path = request.args.get('path', '.')
    action = request.args.get('action')
    
    if action == 'download' and os.path.isfile(path):
        return send_file(path, as_attachment=True)
    
    if not os.path.exists(path):
        path = '.'
    
    files = []
    try:
        for item in os.listdir(path):
            # Skip logs directory and other system directories
            if item in ['logs', '__pycache__', '.git', 'venv', 'node_modules']:
                continue
                
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                files.append({
                    'name': item,
                    'path': item_path,
                    'is_dir': True,
                    'size': ''
                })
            else:
                size = os.path.getsize(item_path)
                size_str = f"{size} bytes"
                if size > 1024:
                    size_str = f"{size/1024:.1f} KB"
                if size > 1024*1024:
                    size_str = f"{size/(1024*1024):.1f} MB"
                
                files.append({
                    'name': item,
                    'path': item_path,
                    'is_dir': False,
                    'size': size_str
                })
    except:
        files = []
    
    # Sort files: directories first, then files
    files.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
    
    return render_template('file_manager.html', 
                         username=session['username'],
                         files=files,
                         current_path=path)

@app.route('/server_files/<name>')
def server_file_manager(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if name not in server_manager.servers:
        flash('Server not found', 'error')
        return redirect(url_for('dashboard'))
    
    default_path = os.path.join('servers', name)
    path = request.args.get('path', default_path)
    action = request.args.get('action')
    
    if action == 'download' and os.path.isfile(path):
        return send_file(path, as_attachment=True)
    
    if not os.path.exists(path):
        path = default_path
        os.makedirs(path, exist_ok=True)
    
    files = []
    try:
        for item in os.listdir(path):
            # Skip system directories
            if item in ['__pycache__', '.git', 'venv', 'node_modules']:
                continue
                
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                files.append({
                    'name': item,
                    'path': item_path,
                    'is_dir': True,
                    'size': ''
                })
            else:
                size = os.path.getsize(item_path)
                size_str = f"{size} bytes"
                if size > 1024:
                    size_str = f"{size/1024:.1f} KB"
                if size > 1024*1024:
                    size_str = f"{size/(1024*1024):.1f} MB"
                
                files.append({
                    'name': item,
                    'path': item_path,
                    'is_dir': False,
                    'size': size_str
                })
    except:
        files = []
    
    # Sort files: directories first, then files
    files.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
    
    return render_template('server_file_manager.html', 
                         username=session['username'],
                         server_name=name,
                         files=files,
                         current_path=path)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('file_manager'))
    
    file = request.files['file']
    path = request.form.get('path', '.')
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('file_manager'))
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(path, filename)
        
        try:
            file.save(file_path)
            flash(f'File {filename} uploaded successfully', 'success')
        except Exception as e:
            flash(f'Failed to upload file: {str(e)}', 'error')
    
    return redirect(url_for('file_manager', path=path))

@app.route('/server_upload/<name>', methods=['POST'])
def server_upload_file(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if name not in server_manager.servers:
        flash('Server not found', 'error')
        return redirect(url_for('dashboard'))
    
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('server_file_manager', name=name))
    
    file = request.files['file']
    default_path = os.path.join('servers', name)
    path = request.form.get('path', default_path)
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('server_file_manager', name=name))
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(path, filename)
        
        try:
            file.save(file_path)
            flash(f'File {filename} uploaded successfully to {name}', 'success')
        except Exception as e:
            flash(f'Failed to upload file: {str(e)}', 'error')
    
    return redirect(url_for('server_file_manager', name=name, path=path))

@app.route('/delete_file')
def delete_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    path = request.args.get('path')
    if path and os.path.exists(path):
        try:
            if os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
                flash('Directory deleted successfully', 'success')
            else:
                os.remove(path)
                flash('File deleted successfully', 'success')
        except Exception as e:
            flash(f'Failed to delete: {str(e)}', 'error')
    else:
        flash('File not found', 'error')
    
    return redirect(url_for('file_manager', path=os.path.dirname(path) if path else '.'))

@app.route('/rename_file', methods=['POST'])
def rename_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    old_path = request.form.get('old_path')
    new_name = request.form.get('new_name')
    current_path = request.form.get('current_path', '.')
    
    if old_path and new_name and os.path.exists(old_path):
        try:
            directory = os.path.dirname(old_path)
            new_path = os.path.join(directory, new_name)
            
            if os.path.exists(new_path):
                flash('A file with that name already exists', 'error')
            else:
                os.rename(old_path, new_path)
                flash(f'File renamed successfully to {new_name}', 'success')
        except Exception as e:
            flash(f'Failed to rename file: {str(e)}', 'error')
    else:
        flash('Invalid parameters', 'error')
    
    return redirect(url_for('file_manager', path=current_path))

@app.route('/move_file', methods=['POST'])
def move_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    source_path = request.form.get('source_path')
    destination_path = request.form.get('destination_path')
    current_path = request.form.get('current_path', '.')
    
    if source_path and destination_path and os.path.exists(source_path):
        try:
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            
            if os.path.exists(destination_path):
                flash('A file with that name already exists at destination', 'error')
            else:
                os.rename(source_path, destination_path)
                flash(f'File moved successfully to {destination_path}', 'success')
        except Exception as e:
            flash(f'Failed to move file: {str(e)}', 'error')
    else:
        flash('Invalid parameters', 'error')
    
    return redirect(url_for('file_manager', path=current_path))

@app.route('/unarchive_file')
def unarchive_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    path = request.args.get('path')
    current_path = request.args.get('current_path', '.')
    
    if path and os.path.exists(path) and path.endswith(('.zip', '.tar.gz', '.rar')):
        try:
            directory = os.path.dirname(path)
            filename = os.path.basename(path)
            name_without_ext = os.path.splitext(filename)[0]
            
            if path.endswith('.zip'):
                with zipfile.ZipFile(path, 'r') as zip_ref:
                    extract_path = os.path.join(directory, name_without_ext)
                    zip_ref.extractall(extract_path)
            elif path.endswith('.tar.gz'):
                import tarfile
                with tarfile.open(path, 'r:gz') as tar_ref:
                    extract_path = os.path.join(directory, name_without_ext)
                    tar_ref.extractall(extract_path)
            
            flash(f'File extracted successfully to {name_without_ext}', 'success')
        except Exception as e:
            flash(f'Failed to extract file: {str(e)}', 'error')
    else:
        flash('Invalid file or not an archive', 'error')
    
    return redirect(url_for('file_manager', path=current_path))

@app.route('/create_folder', methods=['POST'])
def create_folder():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    folder_name = request.form.get('folder_name')
    path = request.form.get('path', '.')
    
    if folder_name:
        folder_path = os.path.join(path, folder_name)
        try:
            os.makedirs(folder_path, exist_ok=True)
            flash(f'Folder {folder_name} created successfully', 'success')
        except Exception as e:
            flash(f'Failed to create folder: {str(e)}', 'error')
    else:
        flash('Folder name is required', 'error')
    
    return redirect(url_for('file_manager', path=path))

@app.route('/server_create_folder/<name>', methods=['POST'])
def server_create_folder(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if name not in server_manager.servers:
        flash('Server not found', 'error')
        return redirect(url_for('dashboard'))
    
    folder_name = request.form.get('folder_name')
    default_path = os.path.join('servers', name)
    path = request.form.get('path', default_path)
    
    if folder_name:
        folder_path = os.path.join(path, folder_name)
        try:
            os.makedirs(folder_path, exist_ok=True)
            flash(f'Folder {folder_name} created successfully in {name}', 'success')
        except Exception as e:
            flash(f'Failed to create folder: {str(e)}', 'error')
    else:
        flash('Folder name is required', 'error')
    
    return redirect(url_for('server_file_manager', name=name, path=path))

@app.route('/server_delete_file/<name>')
def server_delete_file(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if name not in server_manager.servers:
        flash('Server not found', 'error')
        return redirect(url_for('dashboard'))
    
    path = request.args.get('path')
    if path and os.path.exists(path):
        try:
            if os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
                flash('Directory deleted successfully', 'success')
            else:
                os.remove(path)
                flash('File deleted successfully', 'success')
        except Exception as e:
            flash(f'Failed to delete: {str(e)}', 'error')
    else:
        flash('File not found', 'error')
    
    default_path = os.path.join('servers', name)
    return redirect(url_for('server_file_manager', name=name, path=os.path.dirname(path) if path else default_path))

@app.route('/server_rename_file/<name>', methods=['POST'])
def server_rename_file(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if name not in server_manager.servers:
        flash('Server not found', 'error')
        return redirect(url_for('dashboard'))
    
    old_path = request.form.get('old_path')
    new_name = request.form.get('new_name')
    default_path = os.path.join('servers', name)
    current_path = request.form.get('current_path', default_path)
    
    if old_path and new_name and os.path.exists(old_path):
        try:
            directory = os.path.dirname(old_path)
            new_path = os.path.join(directory, new_name)
            
            if os.path.exists(new_path):
                flash('A file with that name already exists', 'error')
            else:
                os.rename(old_path, new_path)
                flash(f'File renamed successfully to {new_name}', 'success')
        except Exception as e:
            flash(f'Failed to rename file: {str(e)}', 'error')
    else:
        flash('Invalid parameters', 'error')
    
    return redirect(url_for('server_file_manager', name=name, path=current_path))

@app.route('/server_move_file/<name>', methods=['POST'])
def server_move_file(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if name not in server_manager.servers:
        flash('Server not found', 'error')
        return redirect(url_for('dashboard'))
    
    source_path = request.form.get('source_path')
    destination_path = request.form.get('destination_path')
    default_path = os.path.join('servers', name)
    current_path = request.form.get('current_path', default_path)
    
    if source_path and destination_path and os.path.exists(source_path):
        try:
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            
            if os.path.exists(destination_path):
                flash('A file with that name already exists at destination', 'error')
            else:
                os.rename(source_path, destination_path)
                flash(f'File moved successfully to {destination_path}', 'success')
        except Exception as e:
            flash(f'Failed to move file: {str(e)}', 'error')
    else:
        flash('Invalid parameters', 'error')
    
    return redirect(url_for('server_file_manager', name=name, path=current_path))

@app.route('/server_unarchive_file/<name>')
def server_unarchive_file(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if name not in server_manager.servers:
        flash('Server not found', 'error')
        return redirect(url_for('dashboard'))
    
    path = request.args.get('path')
    default_path = os.path.join('servers', name)
    current_path = request.args.get('current_path', default_path)
    
    if path and os.path.exists(path) and path.endswith(('.zip', '.tar.gz', '.rar')):
        try:
            directory = os.path.dirname(path)
            filename = os.path.basename(path)
            name_without_ext = os.path.splitext(filename)[0]
            
            if path.endswith('.zip'):
                with zipfile.ZipFile(path, 'r') as zip_ref:
                    extract_path = os.path.join(directory, name_without_ext)
                    zip_ref.extractall(extract_path)
            elif path.endswith('.tar.gz'):
                import tarfile
                with tarfile.open(path, 'r:gz') as tar_ref:
                    extract_path = os.path.join(directory, name_without_ext)
                    tar_ref.extractall(extract_path)
            
            flash(f'File extracted successfully to {name_without_ext}', 'success')
        except Exception as e:
            flash(f'Failed to extract file: {str(e)}', 'error')
    else:
        flash('Invalid file or not an archive', 'error')
    
    return redirect(url_for('server_file_manager', name=name, path=current_path))

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
            
            # Set up environment like Linux/Ubuntu terminal
            env = os.environ.copy()
            
            # Add Python to PATH if not already there
            python_paths = [
                "/usr/bin",
                "/usr/local/bin",
                "/usr/local/sbin",
                "/opt/python3/bin",
                "/home/{}/.local/bin".format(os.getenv('USER', '')),
                "/snap/bin"
            ]
            
            current_path = env.get('PATH', '')
            for python_path in python_paths:
                if os.path.exists(python_path) and python_path not in current_path:
                    current_path = f"{python_path}:{current_path}"
            
            env['PATH'] = current_path
            
            # Execute the command with proper Linux shell
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                cwd=server_dir,
                env=env,
                executable='/bin/bash'  # Use bash for better command support
            )
            
            # Get output with timeout
            try:
                output, _ = process.communicate(timeout=30)  # 30 second timeout
            except subprocess.TimeoutExpired:
                process.kill()
                server_manager.add_console_log(name, "Command timed out after 30 seconds")
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

@app.route('/api/read_file')
def api_read_file():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    path = request.args.get('path')
    if not path or not os.path.exists(path):
        return jsonify({'success': False, 'error': 'File not found'})
    
    try:
        # Check if file is readable and not too large (max 1MB)
        if os.path.getsize(path) > 1024 * 1024:
            return jsonify({'success': False, 'error': 'File too large (max 1MB)'})
        
        # Read file content
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({'success': True, 'content': content})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/save_file', methods=['POST'])
def api_save_file():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    path = data.get('path')
    content = data.get('content')
    
    if not path or content is None:
        return jsonify({'success': False, 'error': 'Missing path or content'})
    
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Write file content
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/read_file')
def api_read_file():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    path = request.args.get('path')
    if not path or not os.path.exists(path):
        return jsonify({'success': False, 'error': 'File not found'})
    
    try:
        # Check if file is readable and not too large (max 1MB)
        if os.path.getsize(path) > 1024 * 1024:
            return jsonify({'success': False, 'error': 'File too large (max 1MB)'})
        
        # Read file content
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({'success': True, 'content': content})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('logs', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('servers', exist_ok=True)
    
    print("🚀 Server Manager starting on Ubuntu VPS...")
    print("Default login: hxc / 123")
    print(f"Local IP: {get_local_ip()}")
    print("Access the web interface at: http://localhost:5010")
    print("For external access: http://YOUR_VPS_IP:5010")
    
    # Run on all interfaces for VPS access
    app.run(host='0.0.0.0', port=5010, debug=False, threaded=True)
