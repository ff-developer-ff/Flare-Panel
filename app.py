import os
import json
import subprocess
import threading
import time
import socket
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, send_from_directory, abort
from werkzeug.utils import secure_filename
import zipfile
import shutil
import tarfile

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
        
        # Use alias IP instead of 0.0.0.0 for display
        display_host = '129.151.144.75' if host == '0.0.0.0' else host
        
        # Set command based on server type
        if server_type == 'gunicorn':
            command = f'gunicorn --bind {host}:{port} --workers 1 {app_file}:app'
            template_file = os.path.join('templates', 'gunicorn_app_template.py')
        elif server_type == 'flask':
            command = f'python3 {app_file}'
            template_file = os.path.join('templates', 'flask_app_template.py')
        else:  # python_bot or other
            command = f'python3 {app_file}'
            template_file = os.path.join('templates', 'flask_app_template.py')
        
        # Copy template if app_file does not exist
        app_file_path = os.path.join(server_dir, app_file)
        if not os.path.exists(app_file_path):
            import shutil
            shutil.copy(template_file, app_file_path)
        
        server = self.add_server(name, display_host, port, command, server_type, app_file)
        # Store actual host for internal use
        server['actual_host'] = host
        return server
    
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
    
    def clear_console_logs(self, name):
        """Clear all console logs for a server"""
        if name in self.servers:
            server = self.servers[name]
            server['console_logs'] = []
            self.save_servers()
            return True
        return False
    
    def install_server_dependencies(self, name, requirements_file='requirements.txt'):
        """Install dependencies from requirements.txt for a server"""
        if name not in self.servers:
            return False, "Server not found"
        
        server_dir = os.path.join('servers', name)
        requirements_file = os.path.join(server_dir, requirements_file)
        
        if not os.path.exists(requirements_file):
            return False, f"{requirements_file} not found"
        
        try:
            # Log the installation start
            self.add_console_log(name, f"Installing dependencies from {requirements_file}...")
            
            # Run pip install
            process = subprocess.Popen(
                ['pip3', 'install', '-r', requirements_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=server_dir
            )
            
            # Get output
            output, _ = process.communicate(timeout=60)  # 60 second timeout
            
            # Log the output
            for line in output.splitlines():
                if line.strip():
                    self.add_console_log(name, line.strip())
            
            if process.returncode == 0:
                self.add_console_log(name, "Dependencies installed successfully!")
                return True, "Dependencies installed successfully"
            else:
                self.add_console_log(name, f"Dependency installation failed with exit code: {process.returncode}")
                return False, f"Installation failed with exit code: {process.returncode}"
                
        except subprocess.TimeoutExpired:
            process.kill()
            self.add_console_log(name, "Dependency installation timed out after 60 seconds")
            return False, "Installation timed out"
        except Exception as e:
            self.add_console_log(name, f"Error installing dependencies: {str(e)}")
            return False, str(e)
    
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
            
            # Check for requirements.txt and install dependencies
            requirements_file = os.path.join(server_dir, 'requirements.txt')
            if os.path.exists(requirements_file):
                self.add_console_log(name, "Found requirements.txt, installing dependencies...")
                success, message = self.install_server_dependencies(name)
                if not success:
                    self.add_console_log(name, f"Warning: Failed to install dependencies: {message}")
            
            # Get absolute paths
            server_dir_abs = os.path.abspath(server_dir)
            
            # Use actual host for server startup
            actual_host = server.get('actual_host', server['host'])
            
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
            env['HOST'] = actual_host
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
            self.clear_console_logs(name)
            self.add_console_log(name, "Server marking as stopped")
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

def setup_nginx_and_ssl(domain, backend_port, enable_ssl, enable_both):
    nginx_conf = ""
    conf_path = f"/etc/nginx/sites-available/{domain}"

    # HTTP block (always present)
    nginx_conf += f"""
server {{
    listen 80;
    server_name {domain};
    location / {{
        proxy_pass http://127.0.0.1:{backend_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
"""
    # If SSL is enabled, redirect HTTP to HTTPS
    if enable_ssl:
        nginx_conf += """
    # Redirect all HTTP to HTTPS
    return 301 https://$host$request_uri;
"""
    nginx_conf += "}\n"

    # HTTPS block if SSL is enabled
    if enable_ssl:
        nginx_conf += f"""
server {{
    listen 443 ssl;
    server_name {domain};

    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;

    location / {{
        proxy_pass http://127.0.0.1:{backend_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""

    # Write the config file
    with open(conf_path, "w") as f:
        f.write(nginx_conf)

    # Enable the site
    subprocess.run(["sudo", "ln", "-sf", conf_path, f"/etc/nginx/sites-enabled/{domain}"])
    subprocess.run(["sudo", "nginx", "-t"])
    subprocess.run(["sudo", "systemctl", "reload", "nginx"])

    # Run certbot if SSL is enabled
    certbot_output = ""
    certbot_success = True
    if enable_ssl:
        certbot_cmd = [
            "sudo", "certbot", "--nginx", "-d", domain, "--non-interactive", "--agree-tos", "-m", f"admin@{domain}"
        ]
        result = subprocess.run(certbot_cmd, capture_output=True, text=True, timeout=120)
        certbot_output = result.stdout + '\n' + result.stderr
        certbot_success = (result.returncode == 0)
    return certbot_success, certbot_output

def cleanup_nginx_and_ssl(domain, ssl_enabled):
    import subprocess
    import os
    conf_path = f"/etc/nginx/sites-available/{domain}"
    enabled_path = f"/etc/nginx/sites-enabled/{domain}"
    # Remove Nginx config files
    try:
        if os.path.exists(conf_path):
            os.remove(conf_path)
        if os.path.exists(enabled_path):
            os.remove(enabled_path)
        subprocess.run(["sudo", "nginx", "-t"])
        subprocess.run(["sudo", "systemctl", "reload", "nginx"])
    except Exception as e:
        print(f"Error removing Nginx config: {e}")
    # Remove SSL certificate if enabled
    if ssl_enabled:
        try:
            subprocess.run([
                "sudo", "certbot", "delete", "--cert-name", domain,
                "--non-interactive", "--quiet"
            ])
        except Exception as e:
            print(f"Error removing SSL certificate: {e}")

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
                         local_ip=get_local_ip(),
                         current_server=None)

@app.route('/create_server', methods=['GET', 'POST'])
def create_server():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        host = request.form.get('host', '0.0.0.0')  # Default to 0.0.0.0 if not provided
        port = int(request.form['port'])
        server_type = request.form['server_type']
        domain = request.form.get('domain_name', '').strip()
        enable_ssl = request.form.get('enable_ssl') == 'on'
        enable_both = request.form.get('enable_both') == 'on'
        gunicorn_command = None
        gunicorn_command_https = None
        ssl_cert = ''
        ssl_key = ''
        # Determine app_file
        app_file = request.form.get('app_file', '').strip()
        if not app_file:
            app_file = 'app.py'
        if server_type == 'gunicorn' and domain:
            if enable_ssl:
                ssl_cert = f'/etc/letsencrypt/live/{domain}/fullchain.pem'
                ssl_key = f'/etc/letsencrypt/live/{domain}/privkey.pem'
                gunicorn_command_https = f'gunicorn --bind 0.0.0.0:443 --certfile {ssl_cert} --keyfile {ssl_key} --workers 1 {app_file}:app'
            if enable_both and enable_ssl:
                gunicorn_command = f'gunicorn --bind 0.0.0.0:80 --workers 1 {app_file}:app'
            elif enable_ssl:
                gunicorn_command = gunicorn_command_https
            else:
                gunicorn_command = f'gunicorn --bind {host}:{port} --workers 1 {app_file}:app'
        # Save server with extra info
        server = server_manager.create_flask_server(name, host, port, app_file, server_type)
        # --- NGINX + SSL AUTO SETUP ---
        if server_type == 'gunicorn' and domain:
            try:
                certbot_success, certbot_output = setup_nginx_and_ssl(domain, port, enable_ssl, enable_both)
                if enable_ssl:
                    if certbot_success:
                        flash(f'SSL certificate installed successfully for {domain}!', 'success')
                    else:
                        flash(f'Certbot failed for {domain}: {certbot_output}', 'error')
                elif certbot_output:
                    flash(certbot_output, 'info')
            except Exception as e:
                flash(f'Nginx/SSL setup error: {str(e)}', 'error')
        # --- END NGINX + SSL AUTO SETUP ---
        if server_type == 'gunicorn':
            server['domain'] = domain
            server['ssl_enabled'] = enable_ssl
            server['ssl_cert'] = ssl_cert
            server['ssl_key'] = ssl_key
            server['enable_both'] = enable_both
            if enable_both and enable_ssl:
                server['command_http'] = gunicorn_command
                server['command_https'] = gunicorn_command_https
                server['command'] = gunicorn_command_https
            else:
                server['command'] = gunicorn_command
            server_manager.save_servers()
        flash(f'Server "{name}" created successfully', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('create_server.html', username=session['username'])

@app.route('/start_server/<name>')
def start_server(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    server = server_manager.servers.get(name)
    if not server:
        flash('Server not found', 'error')
        return redirect(url_for('dashboard'))
    server_dir = os.path.join('servers', name)
    requirements_path = os.path.join(server_dir, 'requirements.txt')
    if not os.path.exists(requirements_path):
        flash('requirements.txt not found. Please add dependencies in settings before starting the server.', 'error')
        return redirect(url_for('dashboard'))
    # Install dependencies
    import subprocess
    try:
        subprocess.check_call(['pip', 'install', '-r', requirements_path])
    except Exception as e:
        flash(f'Failed to install dependencies: {e}', 'error')
        return redirect(url_for('dashboard'))
    # Start the server
    try:
        server_manager.start_server(name)
        flash('Server started successfully', 'success')
    except Exception as e:
        flash(f'Failed to start server: {e}', 'error')
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
        
        # Remove Nginx config and SSL if Gunicorn with domain
        server = server_manager.servers[name]
        if server.get('server_type') == 'gunicorn' and server.get('domain'):
            cleanup_nginx_and_ssl(server['domain'], server.get('ssl_enabled', False))
        
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
    
    server = server_manager.servers[name]
    return render_template('console.html', 
                         username=session['username'],
                         server_name=name,
                         server=server,
                         servers=server_manager.servers,
                         current_server=name)

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

@app.route('/api/clear_logs/<name>', methods=['POST'])
def clear_logs(name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if name not in server_manager.servers:
        return jsonify({'error': 'Server not found'}), 404
    
    success = server_manager.clear_console_logs(name)
    if success:
        return jsonify({'success': True, 'message': 'Logs cleared successfully'})
    else:
        return jsonify({'error': 'Failed to clear logs'}), 500

@app.route('/api/install_dependencies/<name>', methods=['POST'])
def install_dependencies(name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if name not in server_manager.servers:
        return jsonify({'error': 'Server not found'}), 404
    
    data = request.get_json()
    requirements_file = data.get('requirements_file', 'requirements.txt')
    
    success, message = server_manager.install_server_dependencies(name, requirements_file)
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 500

@app.route('/server_file_manager/<name>')
@app.route('/server_file_manager/<name>/<path:path>')
def server_file_manager(name, path='.'): 
    return redirect(url_for('file_manager'))

@app.route('/server_upload_file/<name>', methods=['POST'])
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
    path = request.form.get('path', '.')
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('server_file_manager', name=name, path=path))
    
    if file:
        filename = secure_filename(file.filename)
        server_dir = os.path.join('servers', name)
        upload_path = os.path.join(server_dir, path, filename)
        
        # Improved path validation - normalize both paths for comparison
        server_dir_abs = os.path.abspath(server_dir)
        upload_path_abs = os.path.abspath(upload_path)
        
        # Security: prevent directory traversal
        if '..' in upload_path or not upload_path_abs.startswith(server_dir_abs):
            flash('Invalid path - Upload location outside server directory', 'error')
            return redirect(url_for('server_file_manager', name=name, path=path))
        
        try:
            file.save(upload_path)
            flash(f'File "{filename}" uploaded successfully', 'success')
        except Exception as e:
            flash(f'Error uploading file: {str(e)}', 'error')
    
    return redirect(url_for('server_file_manager', name=name, path=path))

@app.route('/server_create_folder/<name>', methods=['POST'])
def server_create_folder(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if name not in server_manager.servers:
        flash('Server not found', 'error')
        return redirect(url_for('dashboard'))
    
    folder_name = request.form.get('folder_name')
    path = request.form.get('path', '.')
    
    if not folder_name:
        flash('Folder name required', 'error')
        return redirect(url_for('server_file_manager', name=name, path=path))
    
    # Security: prevent directory traversal
    if '..' in folder_name or '/' in folder_name:
        flash('Invalid folder name', 'error')
        return redirect(url_for('server_file_manager', name=name, path=path))
    
    try:
        server_dir = os.path.join('servers', name)
        new_folder = os.path.join(server_dir, path, folder_name)
        
        # Improved path validation
        server_dir_abs = os.path.abspath(server_dir)
        new_folder_abs = os.path.abspath(new_folder)
        
        # Check if the new folder would be within the server directory
        if not new_folder_abs.startswith(server_dir_abs):
            flash('Access denied - Folder location outside server directory', 'error')
            return redirect(url_for('server_file_manager', name=name, path=path))
        
        os.makedirs(new_folder_abs, exist_ok=True)
        flash(f'Folder "{folder_name}" created successfully', 'success')
    except PermissionError:
        flash('Permission denied - Cannot create folder', 'error')
    except OSError as e:
        flash(f'OS Error creating folder: {str(e)}', 'error')
    except Exception as e:
        flash(f'Error creating folder: {str(e)}', 'error')
    
    return redirect(url_for('server_file_manager', name=name, path=path))

@app.route('/server_delete_file/<name>')
def server_delete_file(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if name not in server_manager.servers:
        flash('Server not found', 'error')
        return redirect(url_for('dashboard'))
    
    path = request.args.get('path')
    if not path:
        flash('Path required', 'error')
        return redirect(url_for('server_file_manager', name=name))
    
    # Security: prevent directory traversal
    if '..' in path or path.startswith('/'):
        flash('Invalid path', 'error')
        return redirect(url_for('server_file_manager', name=name))
    
    try:
        server_dir = os.path.join('servers', name)
        full_path = os.path.join(server_dir, path)
        
        # Improved path validation - normalize both paths for comparison
        server_dir_abs = os.path.abspath(server_dir)
        full_path_abs = os.path.abspath(full_path)
        
        # Check if the file is within the server directory
        if not full_path_abs.startswith(server_dir_abs):
            flash('Access denied - Path outside server directory', 'error')
            return redirect(url_for('server_file_manager', name=name))
        
        # Check if file/directory exists
        if not os.path.exists(full_path_abs):
            flash('File or directory not found', 'error')
            return redirect(url_for('server_file_manager', name=name))
        
        if os.path.isdir(full_path_abs):
            import shutil
            shutil.rmtree(full_path_abs)
            flash('Folder deleted successfully', 'success')
        else:
            os.remove(full_path_abs)
            flash('File deleted successfully', 'success')
    except PermissionError:
        flash('Permission denied - Cannot delete file/folder', 'error')
    except OSError as e:
        flash(f'OS Error deleting: {str(e)}', 'error')
    except Exception as e:
        flash(f'Error deleting: {str(e)}', 'error')
    
    return redirect(url_for('server_file_manager', name=name))

@app.route('/server_rename_file/<name>', methods=['POST'])
def server_rename_file(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if name not in server_manager.servers:
        flash('Server not found', 'error')
        return redirect(url_for('dashboard'))
    
    old_path = request.form.get('old_path')
    new_name = request.form.get('new_name')
    current_path = request.form.get('current_path', '.')
    
    if not old_path or not new_name:
        flash('Old path and new name required', 'error')
        return redirect(url_for('server_file_manager', name=name, path=current_path))
    
    # Security: prevent directory traversal
    if '..' in old_path or '..' in new_name or '/' in new_name:
        flash('Invalid path or name', 'error')
        return redirect(url_for('server_file_manager', name=name, path=current_path))
    
    try:
        server_dir = os.path.join('servers', name)
        old_full_path = os.path.join(server_dir, old_path)
        new_full_path = os.path.join(server_dir, os.path.dirname(old_path), new_name)
        
        # Improved path validation - normalize both paths for comparison
        server_dir_abs = os.path.abspath(server_dir)
        old_full_path_abs = os.path.abspath(old_full_path)
        new_full_path_abs = os.path.abspath(new_full_path)
        
        # Check if the old file is within the server directory
        if not old_full_path_abs.startswith(server_dir_abs):
            flash('Access denied - Path outside server directory', 'error')
            return redirect(url_for('server_file_manager', name=name, path=current_path))
        
        # Check if the new path would be within the server directory
        if not new_full_path_abs.startswith(server_dir_abs):
            flash('Access denied - New path outside server directory', 'error')
            return redirect(url_for('server_file_manager', name=name, path=current_path))
        
        # Check if old file exists
        if not os.path.exists(old_full_path_abs):
            flash('File not found', 'error')
            return redirect(url_for('server_file_manager', name=name, path=current_path))
        
        os.rename(old_full_path_abs, new_full_path_abs)
        flash('File renamed successfully', 'success')
    except PermissionError:
        flash('Permission denied - Cannot rename file', 'error')
    except OSError as e:
        flash(f'OS Error renaming: {str(e)}', 'error')
    except Exception as e:
        flash(f'Error renaming file: {str(e)}', 'error')
    
    return redirect(url_for('server_file_manager', name=name, path=current_path))

# File reading and editing APIs
@app.route('/api/read_file')
def read_file_api():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    path = request.args.get('path')
    if not path:
        return jsonify({'error': 'Path required'}), 400
    
    # Security: prevent directory traversal
    if '..' in path or path.startswith('/'):
        return jsonify({'error': 'Invalid path'}), 400
    
    try:
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({'success': True, 'content': content})
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/save_file', methods=['POST'])
def save_file_api():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    path = data.get('path')
    content = data.get('content')
    
    if not path or content is None:
        return jsonify({'error': 'Path and content required'}), 400
    
    # Security: prevent directory traversal
    if '..' in path or path.startswith('/'):
        return jsonify({'error': 'Invalid path'}), 400
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# System Information API
@app.route('/api/system_info')
def system_info():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        import platform
        
        # Basic system info (always available)
        system_info = {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'hostname': platform.node(),
            'python_version': platform.python_version(),
        }
        
        # Try to get detailed info with psutil
        try:
            import psutil
            
            # CPU Info
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory Info
            memory = psutil.virtual_memory()
            memory_total = memory.total
            memory_used = memory.used
            memory_percent = memory.percent
            
            # Disk Info
            disk = psutil.disk_usage('/')
            disk_total = disk.total
            disk_used = disk.used
            disk_percent = disk.percent
            
            # Add detailed info
            system_info.update({
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count
                },
                'memory': {
                    'total': memory_total,
                    'used': memory_used,
                    'percent': memory_percent,
                    'total_gb': round(memory_total / (1024**3), 2),
                    'used_gb': round(memory_used / (1024**3), 2)
                },
                'disk': {
                    'total': disk_total,
                    'used': disk_used,
                    'percent': disk_percent,
                    'total_gb': round(disk_total / (1024**3), 2),
                    'used_gb': round(disk_used / (1024**3), 2)
                }
            })
            
        except ImportError:
            # psutil not available, provide basic info
            system_info.update({
                'cpu': {
                    'percent': 0,
                    'count': 'Unknown'
                },
                'memory': {
                    'total': 0,
                    'used': 0,
                    'percent': 0,
                    'total_gb': 0,
                    'used_gb': 0
                },
                'disk': {
                    'total': 0,
                    'used': 0,
                    'percent': 0,
                    'total_gb': 0,
                    'used_gb': 0
                },
                'psutil_available': False
            })
        
        return jsonify(system_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Process Management API
@app.route('/api/processes')
def get_processes():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        import psutil
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                proc_info = proc.info
                processes.append({
                    'pid': proc_info['pid'],
                    'name': proc_info['name'],
                    'cpu_percent': round(proc_info['cpu_percent'], 1),
                    'memory_percent': round(proc_info['memory_percent'], 1),
                    'status': proc_info['status']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        
        return jsonify({'processes': processes[:50]})  # Return top 50 processes
    except ImportError:
        return jsonify({
            'processes': [],
            'error': 'psutil not installed - Install with: pip install psutil',
            'psutil_available': False
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Kill Process API
@app.route('/api/kill_process/<int:pid>', methods=['POST'])
def kill_process(pid):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        import psutil
        
        process = psutil.Process(pid)
        process.terminate()
        
        # Wait a bit, then force kill if still running
        try:
            process.wait(timeout=3)
        except psutil.TimeoutExpired:
            process.kill()
        
        return jsonify({'success': True, 'message': f'Process {pid} killed successfully'})
    except psutil.NoSuchProcess:
        return jsonify({'error': 'Process not found'}), 404
    except psutil.AccessDenied:
        return jsonify({'error': 'Access denied - Cannot kill process'}), 403
    except ImportError:
        return jsonify({'error': 'psutil not installed - Install with: pip install psutil'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Network Information API
@app.route('/api/network_info')
def network_info():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        import psutil
        
        # Network interfaces
        net_io = psutil.net_io_counters()
        net_interfaces = psutil.net_if_addrs()
        
        network_info = {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'interfaces': {}
        }
        
        for interface, addresses in net_interfaces.items():
            network_info['interfaces'][interface] = []
            for addr in addresses:
                if addr.family == socket.AF_INET:  # IPv4
                    network_info['interfaces'][interface].append({
                        'type': 'IPv4',
                        'address': addr.address,
                        'netmask': addr.netmask
                    })
                elif addr.family == socket.AF_INET6:  # IPv6
                    network_info['interfaces'][interface].append({
                        'type': 'IPv6',
                        'address': addr.address,
                        'netmask': addr.netmask
                    })
        
        return jsonify(network_info)
    except ImportError:
        return jsonify({
            'error': 'psutil not installed - Install with: pip install psutil',
            'psutil_available': False,
            'bytes_sent': 0,
            'bytes_recv': 0,
            'packets_sent': 0,
            'packets_recv': 0,
            'interfaces': {}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Backup Server API
@app.route('/api/backup_server/<name>', methods=['POST'])
def backup_server(name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if name not in server_manager.servers:
        return jsonify({'error': 'Server not found'}), 404
    
    try:
        import shutil
        import zipfile
        from datetime import datetime
        data = request.get_json(silent=True) or {}
        custom_name = data.get('backup_name', '').strip() if data else ''
        server_dir = os.path.join('servers', name)
        if not os.path.exists(server_dir):
            return jsonify({'error': 'Server directory not found'}), 404
        # Create backup directory
        backup_dir = 'backups'
        os.makedirs(backup_dir, exist_ok=True)
        # Use custom name if provided and valid
        if custom_name and all(c.isalnum() or c in ('-', '_') for c in custom_name):
            backup_filename = f'{custom_name}.zip'
        else:
            # fallback to default
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'{name}_backup_{timestamp}.zip'
        backup_path = os.path.join(backup_dir, backup_filename)
        # Ensure only one backup is created
        if os.path.exists(backup_path):
            return jsonify({'error': 'A backup with this name already exists.'}), 400
        # Create zip backup
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(server_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, server_dir)
                    zipf.write(file_path, arcname)
        backup_size = os.path.getsize(backup_path)
        return jsonify({
            'success': True,
            'message': f'Server {name} backed up successfully',
            'backup_file': backup_filename,
            'backup_size': backup_size,
            'backup_size_mb': round(backup_size / (1024**2), 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Restore Server API
@app.route('/api/restore_server/<name>', methods=['POST'])
def restore_server(name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    backup_file = data.get('backup_file')
    
    if not backup_file:
        return jsonify({'error': 'Backup file required'}), 400
    
    try:
        import shutil
        import zipfile
        
        backup_path = os.path.join('backups', backup_file)
        if not os.path.exists(backup_path):
            return jsonify({'error': 'Backup file not found'}), 404
        
        server_dir = os.path.join('servers', name)
        
        # Stop server if running
        if name in server_manager.servers and server_manager.servers[name]['status'] == 'running':
            server_manager.stop_server(name)
        
        # Remove existing server directory
        if os.path.exists(server_dir):
            shutil.rmtree(server_dir)
        
        # Create new server directory
        os.makedirs(server_dir, exist_ok=True)
        
        # Extract backup
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            zipf.extractall(server_dir)
        
        return jsonify({
            'success': True,
            'message': f'Server {name} restored successfully from {backup_file}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# List Backups API
@app.route('/api/list_backups')
def list_backups():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        backup_dir = 'backups'
        if not os.path.exists(backup_dir):
            return jsonify({'backups': []})
        
        backups = []
        for file in os.listdir(backup_dir):
            if file.endswith('.zip'):
                file_path = os.path.join(backup_dir, file)
                file_stat = os.stat(file_path)
                backups.append({
                    'filename': file,
                    'size': file_stat.st_size,
                    'size_mb': round(file_stat.st_size / (1024**2), 2),
                    'created': datetime.fromtimestamp(file_stat.st_ctime).isoformat()
                })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({'backups': backups})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Server Logs API
@app.route('/api/server_logs/<name>')
def server_logs(name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if name not in server_manager.servers:
        return jsonify({'error': 'Server not found'}), 404
    
    try:
        server_dir = os.path.join('servers', name)
        log_files = []
        
        if os.path.exists(server_dir):
            for file in os.listdir(server_dir):
                if file.endswith('.log'):
                    file_path = os.path.join(server_dir, file)
                    file_stat = os.stat(file_path)
                    log_files.append({
                        'filename': file,
                        'size': file_stat.st_size,
                        'size_mb': round(file_stat.st_size / (1024**2), 2),
                        'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                    })
        
        return jsonify({'log_files': log_files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Debug Path API (for troubleshooting)
@app.route('/api/debug_path/<name>')
def debug_path(name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if name not in server_manager.servers:
        return jsonify({'error': 'Server not found'}), 404
    
    path = request.args.get('path', '.')
    
    try:
        server_dir = os.path.join('servers', name)
        full_path = os.path.join(server_dir, path)
        
        server_dir_abs = os.path.abspath(server_dir)
        full_path_abs = os.path.abspath(full_path)
        
        return jsonify({
            'server_dir': server_dir,
            'server_dir_abs': server_dir_abs,
            'path': path,
            'full_path': full_path,
            'full_path_abs': full_path_abs,
            'is_within_server': full_path_abs.startswith(server_dir_abs),
            'exists': os.path.exists(full_path_abs),
            'is_dir': os.path.isdir(full_path_abs) if os.path.exists(full_path_abs) else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Read Log File API
@app.route('/api/read_log/<name>/<filename>')
def read_log(name, filename):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if name not in server_manager.servers:
        return jsonify({'error': 'Server not found'}), 404
    
    try:
        log_path = os.path.join('servers', name, filename)
        
        # Security check
        if not log_path.startswith(os.path.abspath(os.path.join('servers', name))):
            return jsonify({'error': 'Access denied'}), 403
        
        if not os.path.exists(log_path):
            return jsonify({'error': 'Log file not found'}), 404
        
        # Read last 1000 lines
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            last_lines = lines[-1000:] if len(lines) > 1000 else lines
        
        return jsonify({
            'success': True,
            'content': ''.join(last_lines),
            'total_lines': len(lines),
            'showing_lines': len(last_lines)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/manage/<name>')
def manage_server(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    if name not in server_manager.servers:
        flash('Server not found', 'error')
        return redirect(url_for('dashboard'))
    server = server_manager.servers[name]
    return render_template('manage_server.html', username=session['username'], server_name=name, server=server, servers=server_manager.servers, current_server=name)

@app.route('/api/files/<name>')
def get_files(name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if name not in server_manager.servers:
        return jsonify({'error': 'Server not found'}), 404
    
    path = request.args.get('path', '/')
    
    # Remove /Root prefix if present
    path = path.replace('/Root', '')
    
    # Security: prevent directory traversal
    if '..' in path:
        return jsonify({'error': 'Invalid path'}), 400
    
    # Get server directory
    server_dir = os.path.join('servers', name)
    if not os.path.exists(server_dir):
        return jsonify({'error': 'Server directory not found'}), 404
    
    # Get absolute path within server directory
    base_dir = os.path.abspath(server_dir)
    
    # Remove /servers/server_name from path if present
    path = path.replace(f'/servers/{name}', '')
    
    # Get the target directory
    target_path = os.path.abspath(os.path.join(base_dir, path.lstrip('/')))
    
    # Security: ensure path is within server directory
    if not target_path.startswith(base_dir):
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        files = []
        for item in os.listdir(target_path):
            item_path = os.path.join(target_path, item)
            rel_path = os.path.relpath(item_path, base_dir)
            
            if os.path.isdir(item_path):
                files.append({
                    'name': item,
                    'path': rel_path,
                    'is_dir': True,
                    'size': ''
                })
            else:
                size = os.path.getsize(item_path)
                files.append({
                    'name': item,
                    'path': rel_path,
                    'is_dir': False,
                    'size': f"{size:,} bytes"
                })
        
        # Sort: directories first, then files
        files.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        
        return jsonify({
            'files': files,
            'current_path': path
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/read_requirements/<name>')
def read_requirements(name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if name not in server_manager.servers:
        return jsonify({'error': 'Server not found'}), 404
    
    filename = request.args.get('filename', 'requirements.txt')
    server_dir = os.path.join('servers', name)
    requirements_file = os.path.join(server_dir, filename)
    
    try:
        if os.path.exists(requirements_file):
            with open(requirements_file, 'r') as f:
                content = f.read()
            return jsonify({'success': True, 'content': content})
        else:
            return jsonify({'success': True, 'content': ''})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/save_settings/<name>', methods=['POST'])
def save_settings(name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if name not in server_manager.servers:
        return jsonify({'error': 'Server not found'}), 404
    
    data = request.get_json()
    new_name = data.get('new_name', name).strip()
    new_port = data.get('new_port')
    startup_command = data.get('startup_command')
    
    try:
        server = server_manager.servers[name]
        reload_needed = False
        # Handle rename
        if new_name and new_name != name:
            # Check if new name already exists
            if new_name in server_manager.servers:
                return jsonify({'error': 'A server with that name already exists.'}), 400
            # Rename server directory
            old_dir = os.path.join('servers', name)
            new_dir = os.path.join('servers', new_name)
            if os.path.exists(old_dir):
                os.rename(old_dir, new_dir)
            # Update server object and key
            server['name'] = new_name
            server_manager.servers[new_name] = server
            del server_manager.servers[name]
            name = new_name
            reload_needed = True
        # Handle port change
        if new_port:
            try:
                server['port'] = int(new_port)
            except Exception:
                return jsonify({'error': 'Invalid port'}), 400
        # Update startup command if provided
        if startup_command:
            server['command'] = startup_command
        server_manager.save_servers()
        return jsonify({'success': True, 'reload': reload_needed})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test_startup/<name>', methods=['POST'])
def test_startup(name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if name not in server_manager.servers:
        return jsonify({'error': 'Server not found'}), 404
    
    data = request.get_json()
    command = data.get('command')
    
    if not command:
        return jsonify({'error': 'No command provided'}), 400
    
    try:
        # Get server directory
        server_dir = os.path.join('servers', name)
        if not os.path.exists(server_dir):
            return jsonify({'error': 'Server directory not found'}), 404
        
        # Set up environment
        env = os.environ.copy()
        env['PORT'] = str(server_manager.servers[name]['port'])
        env['HOST'] = server_manager.servers[name].get('actual_host', '0.0.0.0')
        env['SERVER_NAME'] = name
        
        # Try to run the command with a short timeout
        process = subprocess.Popen(
            command.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=server_dir,
            env=env
        )
        
        try:
            # Wait for a short time to see if the command starts
            output, _ = process.communicate(timeout=2)
            if process.returncode == 0:
                return jsonify({'success': True, 'message': 'Command test successful'})
            else:
                return jsonify({'error': f'Command failed with exit code: {process.returncode}\nOutput: {output}'})
        except subprocess.TimeoutExpired:
            # If we timeout, it might mean the server started successfully
            process.kill()
            return jsonify({'success': True, 'message': 'Command appears to start the server successfully'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete_backup', methods=['POST'])
def delete_backup():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    filename = data.get('filename', '')
    if not filename or not filename.endswith('.zip') or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    backup_path = os.path.join('backups', filename)
    if not os.path.exists(backup_path):
        return jsonify({'error': 'Backup file not found'}), 404
    try:
        os.remove(backup_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/backups', methods=['GET', 'POST'])
def backups():
    if 'username' not in session:
        return redirect(url_for('login'))
    # List backups for the table
    backup_dir = 'backups'
    backups_list = []
    if os.path.exists(backup_dir):
        for file in os.listdir(backup_dir):
            if file.endswith('.zip'):
                file_path = os.path.join(backup_dir, file)
                file_stat = os.stat(file_path)
                backups_list.append({
                    'name': file,
                    'created_at': datetime.fromtimestamp(file_stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                })
    backups_list.sort(key=lambda x: x['created_at'], reverse=True)
    servers_list = list(server_manager.servers.values())
    return render_template('backups.html', username=session['username'], servers=servers_list, current_server=None, backups=backups_list)

@app.route('/create_backup', methods=['POST'], endpoint='create_backup')
def create_backup():
    if 'username' not in session:
        return redirect(url_for('login'))
    backup_name = request.form.get('backup_name', '').strip()
    if not backup_name or not all(c.isalnum() or c in ('-', '_') for c in backup_name):
        flash('Invalid backup name. Use only letters, numbers, - and _.', 'error')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Render only the table and alert
            return render_template('backups_partial.html')
        return redirect(url_for('backups'))
    servers = list(server_manager.servers.keys())
    if not servers:
        flash('No servers to backup.', 'error')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return render_template('backups_partial.html')
        return redirect(url_for('backups'))
    server_name = servers[0]
    from flask import jsonify
    with app.test_request_context():
        resp = app.view_functions['backup_server'](server_name)
        if isinstance(resp, tuple):
            resp = resp[0]
        if hasattr(resp, 'json') and resp.json.get('success'):
            flash(f'Backup "{backup_name}" created successfully.', 'success')
        else:
            error_msg = resp.json.get('error') if hasattr(resp, 'json') else 'Failed to create backup.'
            flash(error_msg, 'error')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('backups_partial.html')
    return redirect(url_for('backups'))

@app.route('/download_backup', endpoint='download_backup')
def download_backup():
    if 'username' not in session:
        return redirect(url_for('login'))
    name = request.args.get('name')
    backup_path = os.path.join('backups', name)
    if not os.path.exists(backup_path):
        flash('Backup not found.', 'error')
        return redirect(url_for('backups'))
    return send_file(backup_path, as_attachment=True)

@app.route('/delete_backup', methods=['POST'], endpoint='delete_backup_html')
def delete_backup_html():
    # ... identical to previous delete_backup, just renamed for HTML form
    if 'username' not in session:
        return redirect(url_for('login'))
    name = request.form.get('backup_name')
    backup_path = os.path.join('backups', name)
    if not os.path.exists(backup_path):
        flash('Backup not found.', 'error')
        return redirect(url_for('backups'))
    try:
        os.remove(backup_path)
        flash('Backup deleted successfully.', 'success')
    except Exception as e:
        flash(f'Failed to delete backup: {e}', 'error')
    return redirect(url_for('backups'))

@app.route('/restore_backup', methods=['POST'], endpoint='restore_backup')
def restore_backup():
    if 'username' not in session:
        return redirect(url_for('login'))
    name = request.form.get('backup_name')
    # Use the first server for restore (or customize as needed)
    servers = list(server_manager.servers.keys())
    if not servers:
        flash('No servers to restore.', 'error')
        return redirect(url_for('backups'))
    server_name = servers[0]
    # Call the API logic directly
    from flask import jsonify
    with app.test_request_context():
        resp = app.view_functions['restore_server'](server_name)
        if isinstance(resp, tuple):
            resp = resp[0]
        if hasattr(resp, 'json') and resp.json.get('success'):
            flash(f'Server restored from backup "{name}".', 'success')
        else:
            error_msg = resp.json.get('error') if hasattr(resp, 'json') else 'Failed to restore backup.'
            flash(error_msg, 'error')
    return redirect(url_for('backups'))

@app.route('/file_manager')
def file_manager():
    if 'username' not in session:
        return redirect(url_for('login'))
    servers_list = list(server_manager.servers.values())
    server_name = request.args.get('server')
    server = None
    if server_name:
        server = next((s for s in servers_list if s['name'] == server_name), None)
    if not server and servers_list:
        server = servers_list[0]
    files = []
    current_path = '.'
    if server:
        server_dir = os.path.join('servers', server['name'])
        base_dir = os.path.abspath(server_dir)
        target_path = base_dir
        try:
            for item in os.listdir(target_path):
                item_path = os.path.join(target_path, item)
                rel_path = os.path.relpath(item_path, base_dir)
                if os.path.isdir(item_path):
                    files.append({
                        'name': item,
                        'path': rel_path,
                        'is_dir': True,
                        'size': ''
                    })
                else:
                    size = os.path.getsize(item_path)
                    files.append({
                        'name': item,
                        'path': rel_path,
                        'is_dir': False,
                        'size': f"{size:,} bytes"
                    })
            files.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        except Exception:
            files = []
    return render_template(
        'file_manager.html',
        username=session['username'],
        servers=servers_list,
        server=server,
        current_server=server['name'] if server else None,
        current_path=current_path,
        files=files
    )

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    path = request.form.get('path', '.')
    file = request.files.get('file')
    if not file:
        flash('No file selected', 'error')
        return redirect(url_for('file_manager'))
    save_path = os.path.abspath(os.path.join('.', path, file.filename))
    if not save_path.startswith(os.path.abspath('.')):
        flash('Invalid path', 'error')
        return redirect(url_for('file_manager'))
    file.save(save_path)
    flash('File uploaded successfully', 'success')
    return redirect(url_for('file_manager'))

@app.route('/create_folder', methods=['POST'])
def create_folder():
    if 'username' not in session:
        return redirect(url_for('login'))
    path = request.form.get('path', '.')
    folder_name = request.form.get('folder_name')
    if not folder_name:
        flash('Folder name required', 'error')
        return redirect(url_for('file_manager'))
    folder_path = os.path.abspath(os.path.join('.', path, folder_name))
    if not folder_path.startswith(os.path.abspath('.')):
        flash('Invalid path', 'error')
        return redirect(url_for('file_manager'))
    try:
        os.makedirs(folder_path, exist_ok=True)
        flash('Folder created successfully', 'success')
    except Exception as e:
        flash(f'Error creating folder: {e}', 'error')
    return redirect(url_for('file_manager'))

@app.route('/delete_file')
def delete_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    path = request.args.get('path')
    if not path:
        flash('Path required', 'error')
        return redirect(url_for('file_manager'))
    abs_path = os.path.abspath(os.path.join('.', path))
    if not abs_path.startswith(os.path.abspath('.')):
        flash('Invalid path', 'error')
        return redirect(url_for('file_manager'))
    try:
        if os.path.isdir(abs_path):
            os.rmdir(abs_path)
        else:
            os.remove(abs_path)
        flash('Deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting: {e}', 'error')
    return redirect(url_for('file_manager'))

@app.route('/rename_file', methods=['POST'])
def rename_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    old_path = request.form.get('old_path')
    new_name = request.form.get('new_name')
    current_path = request.form.get('current_path', '.')
    if not old_path or not new_name:
        flash('Missing data', 'error')
        return redirect(url_for('file_manager'))
    abs_old = os.path.abspath(os.path.join('.', old_path))
    abs_new = os.path.abspath(os.path.join('.', os.path.dirname(old_path), new_name))
    if not abs_old.startswith(os.path.abspath('.')) or not abs_new.startswith(os.path.abspath('.')):
        flash('Invalid path', 'error')
        return redirect(url_for('file_manager'))
    try:
        os.rename(abs_old, abs_new)
        flash('Renamed successfully', 'success')
    except Exception as e:
        flash(f'Error renaming: {e}', 'error')
    return redirect(url_for('file_manager'))

@app.route('/move_file', methods=['POST'])
def move_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    source_path = request.form.get('source_path')
    destination_path = request.form.get('destination_path')
    if not source_path or not destination_path:
        flash('Missing data', 'error')
        return redirect(url_for('file_manager'))
    abs_source = os.path.abspath(os.path.join('.', source_path))
    abs_dest = os.path.abspath(os.path.join('.', destination_path))
    if not abs_source.startswith(os.path.abspath('.')) or not abs_dest.startswith(os.path.abspath('.')):
        flash('Invalid path', 'error')
        return redirect(url_for('file_manager'))
    try:
        os.rename(abs_source, abs_dest)
        flash('Moved successfully', 'success')
    except Exception as e:
        flash(f'Error moving: {e}', 'error')
    return redirect(url_for('file_manager'))

@app.route('/unarchive_file')
def unarchive_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    path = request.args.get('path')
    current_path = request.args.get('current_path', '.')
    if not path:
        flash('Path required', 'error')
        return redirect(url_for('file_manager'))
    abs_path = os.path.abspath(os.path.join('.', path))
    extract_to = os.path.abspath(os.path.join('.', current_path))
    if not abs_path.startswith(os.path.abspath('.')) or not extract_to.startswith(os.path.abspath('.')):
        flash('Invalid path', 'error')
        return redirect(url_for('file_manager'))
    try:
        if abs_path.endswith('.zip'):
            with zipfile.ZipFile(abs_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
        # Add more archive types if needed
        flash('Archive extracted successfully', 'success')
    except Exception as e:
        flash(f'Error extracting archive: {e}', 'error')
    return redirect(url_for('file_manager'))

@app.route('/api/servers/<name>/files/upload', methods=['POST'])
def api_upload_file(name):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    if name not in server_manager.servers:
        return jsonify({'success': False, 'error': 'Server not found'}), 404
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    file = request.files['file']
    path = request.form.get('path', '.')
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    filename = secure_filename(file.filename)
    server_dir = os.path.join('servers', name)
    upload_path = os.path.join(server_dir, path, filename)
    server_dir_abs = os.path.abspath(server_dir)
    upload_path_abs = os.path.abspath(upload_path)
    if '..' in upload_path or not upload_path_abs.startswith(server_dir_abs):
        return jsonify({'success': False, 'error': 'Invalid path'}), 400
    try:
        os.makedirs(os.path.dirname(upload_path_abs), exist_ok=True)
        file.save(upload_path_abs)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/servers/<name>/files/create_folder', methods=['POST'])
def api_create_folder(name):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    if name not in server_manager.servers:
        return jsonify({'success': False, 'error': 'Server not found'}), 404
    folder_name = request.form.get('folder_name')
    path = request.form.get('path', '.')
    if not folder_name:
        return jsonify({'success': False, 'error': 'Folder name required'}), 400
    if '..' in folder_name or '/' in folder_name:
        return jsonify({'success': False, 'error': 'Invalid folder name'}), 400
    server_dir = os.path.join('servers', name)
    new_folder = os.path.join(server_dir, path, folder_name)
    server_dir_abs = os.path.abspath(server_dir)
    new_folder_abs = os.path.abspath(new_folder)
    if not new_folder_abs.startswith(server_dir_abs):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    try:
        os.makedirs(new_folder_abs, exist_ok=True)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/servers/<name>/files', methods=['DELETE'])
def api_delete_file(name):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    if name not in server_manager.servers:
        return jsonify({'success': False, 'error': 'Server not found'}), 404
    path = request.args.get('path')
    if not path:
        return jsonify({'success': False, 'error': 'Path required'}), 400
    server_dir = os.path.join('servers', name)
    full_path = os.path.join(server_dir, path)
    server_dir_abs = os.path.abspath(server_dir)
    full_path_abs = os.path.abspath(full_path)
    if not full_path_abs.startswith(server_dir_abs):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    try:
        if os.path.isdir(full_path_abs):
            import shutil
            shutil.rmtree(full_path_abs)
        else:
            os.remove(full_path_abs)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/servers/<name>/files/rename', methods=['PATCH'])
def api_rename_file(name):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    if name not in server_manager.servers:
        return jsonify({'success': False, 'error': 'Server not found'}), 404
    data = request.get_json()
    old_path = data.get('old_path')
    new_name = data.get('new_name')
    if not old_path or not new_name:
        return jsonify({'success': False, 'error': 'Missing data'}), 400
    server_dir = os.path.join('servers', name)
    abs_old = os.path.abspath(os.path.join(server_dir, old_path))
    abs_new = os.path.abspath(os.path.join(server_dir, os.path.dirname(old_path), new_name))
    server_dir_abs = os.path.abspath(server_dir)
    if not abs_old.startswith(server_dir_abs) or not abs_new.startswith(server_dir_abs):
        return jsonify({'success': False, 'error': 'Invalid path'}), 400
    try:
        os.rename(abs_old, abs_new)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/servers/<name>/files/save', methods=['POST'])
def api_save_file(name):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    if name not in server_manager.servers:
        return jsonify({'success': False, 'error': 'Server not found'}), 404
    data = request.get_json()
    path = data.get('path')
    content = data.get('content')
    if not path or content is None:
        return jsonify({'success': False, 'error': 'Path and content required'}), 400
    server_dir = os.path.join('servers', name)
    abs_path = os.path.abspath(os.path.join(server_dir, path))
    server_dir_abs = os.path.abspath(server_dir)
    if not abs_path.startswith(server_dir_abs):
        return jsonify({'success': False, 'error': 'Invalid path'}), 400
    try:
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/servers/<name>/files', methods=['GET'])
def api_list_files(name):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    if name not in server_manager.servers:
        return jsonify({'success': False, 'error': 'Server not found'}), 404
    path = request.args.get('path', '/')
    path = path.replace('/Root', '')
    if '..' in path:
        return jsonify({'success': False, 'error': 'Invalid path'}), 400
    server_dir = os.path.join('servers', name)
    if not os.path.exists(server_dir):
        return jsonify({'success': False, 'error': 'Server directory not found'}), 404
    base_dir = os.path.abspath(server_dir)
    path = path.replace(f'/servers/{name}', '')
    target_path = os.path.abspath(os.path.join(base_dir, path.lstrip('/')))
    if not target_path.startswith(base_dir):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    try:
        files = []
        for item in os.listdir(target_path):
            item_path = os.path.join(target_path, item)
            rel_path = os.path.relpath(item_path, base_dir)
            if os.path.isdir(item_path):
                files.append({
                    'name': item,
                    'path': rel_path,
                    'is_dir': True,
                    'size': ''
                })
            else:
                size = os.path.getsize(item_path)
                files.append({
                    'name': item,
                    'path': rel_path,
                    'is_dir': False,
                    'size': f"{size:,} bytes"
                })
        files.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        return jsonify({'success': True, 'files': files, 'current_path': path})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/servers/<name>/files/extract', methods=['POST'])
def api_extract_file(name):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    if name not in server_manager.servers:
        return jsonify({'success': False, 'error': 'Server not found'}), 404
    data = request.get_json()
    path = data.get('path')
    if not path:
        return jsonify({'success': False, 'error': 'Path required'}), 400
    server_dir = os.path.join('servers', name)
    abs_path = os.path.abspath(os.path.join(server_dir, path))
    server_dir_abs = os.path.abspath(server_dir)
    if not abs_path.startswith(server_dir_abs):
        return jsonify({'success': False, 'error': 'Invalid path'}), 400
    try:
        if abs_path.endswith('.zip'):
            with zipfile.ZipFile(abs_path, 'r') as zip_ref:
                zip_ref.extractall(os.path.dirname(abs_path))
        elif abs_path.endswith('.tar.gz') or abs_path.endswith('.tgz'):
            with tarfile.open(abs_path, 'r:gz') as tar_ref:
                tar_ref.extractall(os.path.dirname(abs_path))
        elif abs_path.endswith('.rar'):
            return jsonify({'success': False, 'error': 'RAR extraction not supported'}), 400
        else:
            return jsonify({'success': False, 'error': 'Unsupported archive type'}), 400
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/servers/<name>/files/copy', methods=['POST'])
def api_copy_file(name):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    if name not in server_manager.servers:
        return jsonify({'success': False, 'error': 'Server not found'}), 404
    data = request.get_json()
    source = data.get('source')
    destination = data.get('destination')
    if not source or not destination:
        return jsonify({'success': False, 'error': 'Source and destination required'}), 400
    server_dir = os.path.join('servers', name)
    abs_source = os.path.abspath(os.path.join(server_dir, source))
    abs_dest = os.path.abspath(os.path.join(server_dir, destination))
    server_dir_abs = os.path.abspath(server_dir)
    if not abs_source.startswith(server_dir_abs) or not abs_dest.startswith(server_dir_abs):
        return jsonify({'success': False, 'error': 'Invalid path'}), 400
    try:
        if os.path.isdir(abs_source):
            shutil.copytree(abs_source, abs_dest)
        else:
            shutil.copy2(abs_source, abs_dest)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/servers/<name>/files/move', methods=['PATCH'])
def api_move_file(name):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    if name not in server_manager.servers:
        return jsonify({'success': False, 'error': 'Server not found'}), 404
    data = request.get_json()
    source = data.get('source')
    destination = data.get('destination')
    if not source or not destination:
        return jsonify({'success': False, 'error': 'Source and destination required'}), 400
    server_dir = os.path.join('servers', name)
    abs_source = os.path.abspath(os.path.join(server_dir, source))
    abs_dest = os.path.abspath(os.path.join(server_dir, destination))
    server_dir_abs = os.path.abspath(server_dir)
    if not abs_source.startswith(server_dir_abs) or not abs_dest.startswith(server_dir_abs):
        return jsonify({'success': False, 'error': 'Invalid path'}), 400
    try:
        shutil.move(abs_source, abs_dest)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/servers/<name>/files/read', methods=['GET'])
def api_read_file_content(name):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    if name not in server_manager.servers:
        return jsonify({'success': False, 'error': 'Server not found'}), 404
    path = request.args.get('path')
    if not path:
        return jsonify({'success': False, 'error': 'Path required'}), 400
    server_dir = os.path.join('servers', name)
    abs_path = os.path.abspath(os.path.join(server_dir, path))
    server_dir_abs = os.path.abspath(server_dir)
    if not abs_path.startswith(server_dir_abs):
        return jsonify({'success': False, 'error': 'Invalid path'}), 400
    try:
        if os.path.isfile(abs_path):
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({'success': True, 'content': content})
        else:
            return jsonify({'success': False, 'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/servers/<name>/resource_usage')
def api_server_resource_usage(name):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    if name not in server_manager.servers:
        return jsonify({'success': False, 'error': 'Server not found'}), 404
    try:
        import psutil
        server = server_manager.servers[name]
        pid = server.get('pid')
        if server['status'] == 'running' and pid:
            try:
                p = psutil.Process(pid)
                ram_mb = int(p.memory_info().rss / 1024 / 1024)
                ram_percent = p.memory_percent()
                cpu = p.cpu_percent(interval=0.5)
                # Disk usage: sum of all open files by this process (approximate)
                # For simplicity, use server dir disk usage as before
                server_dir = os.path.join('servers', name)
                if os.path.exists(server_dir):
                    disk = psutil.disk_usage(server_dir)
                else:
                    disk = psutil.disk_usage('/')
                disk_percent = disk.percent
                disk_mb = int(disk.used / 1024 / 1024)
            except Exception:
                ram_mb = 0
                ram_percent = 0
                cpu = 0
                disk_percent = 0
                disk_mb = 0
        else:
            ram_mb = 0
            ram_percent = 0
            cpu = 0
            disk_percent = 0
            disk_mb = 0
        return jsonify({
            'success': True,
            'ram_percent': round(ram_percent, 1),
            'ram_mb': ram_mb,
            'cpu': round(cpu, 1),
            'disk_percent': disk_percent,
            'disk_mb': disk_mb
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/settings/<name>', methods=['GET', 'POST'])
def save_settings_form(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    server = server_manager.servers.get(name)
    server_dir = os.path.join('servers', name)
    requirements_path = os.path.join(server_dir, 'requirements.txt')
    if request.method == 'POST':
        if not server:
            flash('Server not found', 'error')
            return redirect(url_for('dashboard'))
        new_name = request.form.get('server_name', '').strip()
        new_host = request.form.get('host', '').strip()
        new_port = request.form.get('port', '').strip()
        dependencies = request.form.get('dependencies', '').strip()
        # Validate
        if not new_name or not new_host or not new_port:
            flash('All fields are required', 'error')
            return redirect(url_for('save_settings_form', name=name))
        # Rename server if needed
        if new_name != name:
            if new_name in server_manager.servers:
                flash('A server with that name already exists.', 'error')
                return redirect(url_for('save_settings_form', name=name))
            old_dir = os.path.join('servers', name)
            new_dir = os.path.join('servers', new_name)
            if os.path.exists(old_dir):
                os.rename(old_dir, new_dir)
            server['name'] = new_name
            server_manager.servers[new_name] = server
            del server_manager.servers[name]
            name = new_name
            server_dir = new_dir
            requirements_path = os.path.join(server_dir, 'requirements.txt')
        # Update host and port
        server['host'] = new_host
        try:
            server['port'] = int(new_port)
        except Exception:
            flash('Invalid port', 'error')
            return redirect(url_for('save_settings_form', name=name))
        # Save requirements.txt
        os.makedirs(server_dir, exist_ok=True)
        with open(requirements_path, 'w', encoding='utf-8') as f:
            f.write(dependencies)
        server_manager.save_servers()
        flash('Settings saved successfully', 'success')
        return redirect(url_for('save_settings_form', name=name))
    # GET: show form
    requirements_content = ''
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            requirements_content = f.read()
    return render_template('settings.html', server=server, server_id=name, username=session['username'], servers=server_manager.servers, current_server=name, requirements_content=requirements_content)

@app.route('/settings/<name>/delete', methods=['POST'])
def delete_server_form(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    if name in server_manager.servers:
        # Stop server if running
        if server_manager.servers[name]['status'] == 'running':
            server_manager.stop_server(name)
        # Remove Nginx config and SSL if Gunicorn with domain
        server = server_manager.servers[name]
        if server.get('server_type') == 'gunicorn' and server.get('domain'):
            cleanup_nginx_and_ssl(server['domain'], server.get('ssl_enabled', False))
        # Remove server directory
        server_dir = os.path.join('servers', name)
        if os.path.exists(server_dir):
            shutil.rmtree(server_dir)
        # Remove from server manager
        del server_manager.servers[name]
        server_manager.save_servers()
        flash(f'Server "{name}" deleted successfully', 'success')
    else:
        flash('Server not found', 'error')
    return redirect(url_for('dashboard'))

# --- NEW BACKUP API ---
from flask import Blueprint

# Remove all old backup routes (API and HTML)
# --- NEW BACKUP ROUTES ---

@app.route('/api/servers/<name>/backups', methods=['GET'])
def api_list_backups(name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    server_dir = os.path.join('servers', name)
    backup_dir = os.path.join(server_dir, 'backups')
    if not os.path.exists(backup_dir):
        return jsonify({'backups': []})
    backups = []
    for file in os.listdir(backup_dir):
        if file.endswith('.zip'):
            file_path = os.path.join(backup_dir, file)
            stat = os.stat(file_path)
            backups.append({
                'filename': file,
                'size': stat.st_size,
                'size_mb': round(stat.st_size / (1024**2), 2),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat()
            })
    backups.sort(key=lambda x: x['created'], reverse=True)
    return jsonify({'backups': backups})

@app.route('/api/servers/<name>/backups', methods=['POST'])
def api_create_backup(name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    if name not in server_manager.servers:
        return jsonify({'error': 'Server not found'}), 404
    data = request.get_json(silent=True) or {}
    custom_name = data.get('backup_name', '').strip()
    server_dir = os.path.join('servers', name)
    backup_dir = os.path.join(server_dir, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    if custom_name and all(c.isalnum() or c in ('-', '_') for c in custom_name):
        backup_filename = f'{custom_name}.zip'
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'{name}_backup_{timestamp}.zip'
    backup_path = os.path.join(backup_dir, backup_filename)
    if os.path.exists(backup_path):
        return jsonify({'error': 'A backup with this name already exists.'}), 400
    try:
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(server_dir):
                # Skip the backups directory itself
                if os.path.abspath(root) == os.path.abspath(backup_dir):
                    continue
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, server_dir)
                    zipf.write(file_path, arcname)
        backup_size = os.path.getsize(backup_path)
        return jsonify({
            'success': True,
            'message': f'Server {name} backed up successfully',
            'backup_file': backup_filename,
            'backup_size': backup_size,
            'backup_size_mb': round(backup_size / (1024**2), 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/servers/<name>/backups/<backup_name>/download', methods=['GET'])
def api_download_backup(name, backup_name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    backup_dir = os.path.join('servers', name, 'backups')
    backup_path = os.path.join(backup_dir, backup_name)
    if not os.path.exists(backup_path):
        return jsonify({'error': 'Backup not found'}), 404
    return send_file(backup_path, as_attachment=True)

@app.route('/api/servers/<name>/backups/<backup_name>', methods=['DELETE'])
def api_delete_backup(name, backup_name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    backup_dir = os.path.join('servers', name, 'backups')
    backup_path = os.path.join(backup_dir, backup_name)
    if not os.path.exists(backup_path):
        return jsonify({'error': 'Backup not found'}), 404
    try:
        os.remove(backup_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/servers/<name>/backups/restore', methods=['POST'])
def api_restore_backup(name):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    if name not in server_manager.servers:
        return jsonify({'error': 'Server not found'}), 404
    data = request.get_json()
    backup_file = data.get('backup_file')
    if not backup_file:
        return jsonify({'error': 'Backup file required'}), 400
    backup_dir = os.path.join('servers', name, 'backups')
    backup_path = os.path.join(backup_dir, backup_file)
    if not os.path.exists(backup_path):
        return jsonify({'error': 'Backup file not found'}), 404
    server_dir = os.path.join('servers', name)
    try:
        # Stop server if running
        if name in server_manager.servers and server_manager.servers[name]['status'] == 'running':
            server_manager.stop_server(name)
        # Remove everything except backups dir
        for item in os.listdir(server_dir):
            item_path = os.path.join(server_dir, item)
            if item == 'backups':
                continue
            if os.path.isdir(item_path):
                import shutil
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        # Extract backup
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            zipf.extractall(server_dir)
        return jsonify({'success': True, 'message': f'Server {name} restored from {backup_file}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
