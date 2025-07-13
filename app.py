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
        else:  # flask or python_bot
            command = f'python3 {app_file}'
        
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
    
    def install_server_dependencies(self, name):
        """Install dependencies from requirements.txt for a server"""
        if name not in self.servers:
            return False, "Server not found"
        
        server_dir = os.path.join('servers', name)
        requirements_file = os.path.join(server_dir, 'requirements.txt')
        
        if not os.path.exists(requirements_file):
            return False, "requirements.txt not found"
        
        try:
            # Log the installation start
            self.add_console_log(name, "Installing dependencies from requirements.txt...")
            
            # Run pip install
            process = subprocess.Popen(
                ['pip3', 'install', '-r', 'requirements.txt'],
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
        else:  # python_bot
            app_content = '''import os
import time
import json
import asyncio
import requests
import threading
from datetime import datetime
from typing import Optional

# Discord Bot Support
try:
    import discord
    from discord.ext import commands, tasks
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    print("⚠️ Discord.py not installed. Install with: pip install discord.py")

class PythonBot:
    def __init__(self, name):
        self.name = name
        self.start_time = datetime.now()
        self.is_running = True
        self.discord_bot = None
        self.discord_token = os.environ.get('DISCORD_TOKEN', '')
        
        print(f"🤖 {name} Bot initialized!")
        print(f"🔧 Bot Type: Multi-Purpose Python Bot")
        print(f"📡 Discord Support: {'✅ Available' if DISCORD_AVAILABLE else '❌ Not Available'}")
    
    def start(self):
        print(f"🚀 {self.name} Bot starting...")
        print(f"⏰ Started at: {self.start_time}")
        print(f"📊 Status: Running")
        
        # Start Discord bot if token is available
        if DISCORD_AVAILABLE and self.discord_token:
            self.start_discord_bot()
        
        try:
            while self.is_running:
                # Bot main loop
                current_time = datetime.now()
                uptime = current_time - self.start_time
                
                # Bot logic here
                self.process_tasks()
                
                # Sleep for a bit
                time.sleep(5)
                
        except KeyboardInterrupt:
            print(f"🛑 {self.name} Bot stopped by user")
        except Exception as e:
            print(f"❌ Error in {self.name} Bot: {str(e)}")
        finally:
            self.stop()
    
    def start_discord_bot(self):
        """Start Discord bot in a separate thread"""
        try:
            self.discord_bot = DiscordBot(self.discord_token, self.name)
            discord_thread = threading.Thread(target=self.discord_bot.run, args=(self.discord_token,))
            discord_thread.daemon = True
            discord_thread.start()
            print(f"🎮 Discord Bot started successfully!")
        except Exception as e:
            print(f"❌ Failed to start Discord bot: {str(e)}")
    
    def process_tasks(self):
        """Main bot task processing"""
        current_time = datetime.now()
        uptime = current_time - self.start_time
        
        print(f"[{current_time.strftime('%H:%M:%S')}] {self.name} Bot is running... (Uptime: {str(uptime).split('.')[0]})")
        
        # Add your bot logic here
        # Example: Check for new messages, process data, etc.
        
        # Example: API monitoring
        self.check_api_status()
        
        # Example: Data processing
        self.process_data()
        
    def check_api_status(self):
        """Example: Check API status"""
        try:
            # Example API check
            response = requests.get('https://httpbin.org/status/200', timeout=5)
            if response.status_code == 200:
                print(f"✅ API Status: Healthy")
        except Exception as e:
            print(f"❌ API Status: Error - {str(e)}")
    
    def process_data(self):
        """Example: Data processing task"""
        # Add your data processing logic here
        pass
        
    def stop(self):
        """Stop the bot"""
        self.is_running = False
        if self.discord_bot:
            asyncio.run(self.discord_bot.close())
        print(f"🛑 {self.name} Bot stopping...")

class DiscordBot(commands.Bot):
    def __init__(self, token: str, bot_name: str):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(command_prefix='!', intents=intents)
        self.bot_name = bot_name
        
        # Register commands
        self.setup_commands()
    
    def setup_commands(self):
        """Setup Discord bot commands"""
        
        @self.command(name='ping')
        async def ping(ctx):
            """Check bot latency"""
            latency = round(self.latency * 1000)
            await ctx.send(f'🏓 Pong! Latency: {latency}ms')
        
        @self.command(name='status')
        async def status(ctx):
            """Show bot status"""
            embed = discord.Embed(
                title=f"🤖 {self.bot_name} Status",
                description="Bot is running and healthy!",
                color=discord.Color.green()
            )
            embed.add_field(name="Latency", value=f"{round(self.latency * 1000)}ms", inline=True)
            embed.add_field(name="Servers", value=len(self.guilds), inline=True)
            embed.add_field(name="Users", value=len(self.users), inline=True)
            await ctx.send(embed=embed)
        
        @self.command(name='info')
        async def info(ctx):
            """Show bot information"""
            embed = discord.Embed(
                title=f"ℹ️ {self.bot_name} Information",
                description="Multi-purpose Python Bot with Discord integration",
                color=discord.Color.blue()
            )
            embed.add_field(name="Python Version", value=os.sys.version.split()[0], inline=True)
            embed.add_field(name="Discord.py Version", value=discord.__version__, inline=True)
            embed.add_field(name="Server Count", value=len(self.guilds), inline=True)
            await ctx.send(embed=embed)
        
        @self.command(name='help')
        async def help_cmd(ctx):
            """Show available commands"""
            embed = discord.Embed(
                title="📚 Available Commands",
                description="Here are the available commands:",
                color=discord.Color.gold()
            )
            embed.add_field(name="!ping", value="Check bot latency", inline=False)
            embed.add_field(name="!status", value="Show bot status", inline=False)
            embed.add_field(name="!info", value="Show bot information", inline=False)
            embed.add_field(name="!help", value="Show this help message", inline=False)
            await ctx.send(embed=embed)
    
    async def on_ready(self):
        """Called when bot is ready"""
        print(f"🎮 Discord Bot logged in as {self.user}")
        print(f"📡 Connected to {len(self.guilds)} servers")
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"!help | {self.bot_name}"
            )
        )
    
    async def on_message(self, message):
        """Handle incoming messages"""
        if message.author == self.user:
            return
        
        # Process commands
        await self.process_commands(message)
        
        # Add custom message handling here
        if message.content.lower().startswith('hello'):
            await message.channel.send(f"👋 Hello {message.author.mention}!")

if __name__ == '__main__':
    bot_name = os.environ.get('SERVER_NAME', 'PythonBot')
    bot = PythonBot(bot_name)
    bot.start()
'''
        
        # Write app file
        with open(os.path.join(server_dir, app_file), 'w') as f:
            f.write(app_content)
        
        # Create requirements.txt with basic dependencies
        requirements_content = '''flask>=2.0.0
requests>=2.25.0
'''
        if server_type == 'gunicorn':
            requirements_content += 'gunicorn>=20.0.0\n'
        elif server_type == 'python_bot':
            requirements_content = '''requests>=2.25.0
python-dotenv>=0.19.0
schedule>=1.1.0
discord.py>=2.0.0
aiohttp>=3.8.0
asyncio
threading
datetime
json
os
time
typing
'''
        
        with open(os.path.join(server_dir, 'requirements.txt'), 'w') as f:
            f.write(requirements_content)
        
        # Install packages from requirements.txt
        try:
            self.install_server_dependencies(name)
        except Exception as e:
            flash(f'Warning: Could not install dependencies: {str(e)}', 'warning')
        
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
    
    success, message = server_manager.install_server_dependencies(name)
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 500

# File Manager Routes
@app.route('/file_manager')
@app.route('/file_manager/<path:path>')
def file_manager(path='.'):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Security: prevent directory traversal
    if '..' in path or path.startswith('/'):
        flash('Invalid path', 'error')
        return redirect(url_for('file_manager'))
    
    # Get absolute path
    base_dir = os.path.abspath('.')
    current_path = os.path.abspath(os.path.join(base_dir, path))
    
    # Security: ensure path is within base directory
    if not current_path.startswith(base_dir):
        flash('Access denied', 'error')
        return redirect(url_for('file_manager'))
    
    # Handle actions
    action = request.args.get('action')
    if action == 'download' and os.path.isfile(current_path):
        return send_file(current_path, as_attachment=True)
    
    # Get directory contents
    try:
        if os.path.isdir(current_path):
            files = []
            for item in os.listdir(current_path):
                item_path = os.path.join(current_path, item)
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
            
            return render_template('file_manager.html',
                                 username=session['username'],
                                 current_path=path,
                                 files=files)
        else:
            flash('Not a directory', 'error')
            return redirect(url_for('file_manager'))
            
    except Exception as e:
        flash(f'Error accessing directory: {str(e)}', 'error')
        return redirect(url_for('file_manager'))

# Root File Manager Routes - Full System Access
@app.route('/root_file_manager')
@app.route('/root_file_manager/<path:path>')
def root_file_manager(path='.'):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Get absolute path - allow full system access
    if path == '.':
        current_path = os.path.abspath('.')
    else:
        current_path = os.path.abspath(path)
    
    # Handle actions
    action = request.args.get('action')
    if action == 'download' and os.path.isfile(current_path):
        return send_file(current_path, as_attachment=True)
    
    # Get directory contents
    try:
        if os.path.isdir(current_path):
            files = []
            for item in os.listdir(current_path):
                item_path = os.path.join(current_path, item)
                
                if os.path.isdir(item_path):
                    files.append({
                        'name': item,
                        'path': item_path,
                        'is_dir': True,
                        'size': ''
                    })
                else:
                    try:
                        size = os.path.getsize(item_path)
                        files.append({
                            'name': item,
                            'path': item_path,
                            'is_dir': False,
                            'size': f"{size:,} bytes"
                        })
                    except OSError:
                        # Skip files we can't access
                        continue
            
            # Sort: directories first, then files
            files.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            
            return render_template('root_file_manager.html',
                                 username=session['username'],
                                 current_path=current_path,
                                 files=files)
        else:
            flash('Not a directory', 'error')
            return redirect(url_for('root_file_manager'))
            
    except PermissionError:
        flash('Permission denied accessing directory', 'error')
        return redirect(url_for('root_file_manager'))
    except Exception as e:
        flash(f'Error accessing directory: {str(e)}', 'error')
        return redirect(url_for('root_file_manager'))

@app.route('/api/file_action', methods=['POST'])
def file_action():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    action = data.get('action')
    path = data.get('path')
    
    if not path or '..' in path or path.startswith('/'):
        return jsonify({'error': 'Invalid path'}), 400
    
    try:
        if action == 'delete':
            if os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
            else:
                os.remove(path)
            return jsonify({'success': True})
        
        elif action == 'rename':
            new_name = data.get('new_name')
            if not new_name:
                return jsonify({'error': 'New name required'}), 400
            
            new_path = os.path.join(os.path.dirname(path), new_name)
            os.rename(path, new_path)
            return jsonify({'success': True})
        
        elif action == 'create_folder':
            folder_name = data.get('folder_name')
            if not folder_name:
                return jsonify({'error': 'Folder name required'}), 400
            
            new_folder = os.path.join(path, folder_name)
            os.makedirs(new_folder, exist_ok=True)
            return jsonify({'success': True})
        
        else:
            return jsonify({'error': 'Invalid action'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/root_file_action', methods=['POST'])
def root_file_action():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    action = data.get('action')
    path = data.get('path')
    
    if not path:
        return jsonify({'error': 'Path required'}), 400
    
    try:
        if action == 'delete':
            if os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
            else:
                os.remove(path)
            return jsonify({'success': True})
        
        elif action == 'rename':
            new_name = data.get('new_name')
            if not new_name:
                return jsonify({'error': 'New name required'}), 400
            
            new_path = os.path.join(os.path.dirname(path), new_name)
            os.rename(path, new_path)
            return jsonify({'success': True})
        
        elif action == 'create_folder':
            folder_name = data.get('folder_name')
            if not folder_name:
                return jsonify({'error': 'Folder name required'}), 400
            
            new_folder = os.path.join(path, folder_name)
            os.makedirs(new_folder, exist_ok=True)
            return jsonify({'success': True})
        
        else:
            return jsonify({'error': 'Invalid action'}), 400
            
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Additional File Manager Routes
@app.route('/upload_file', methods=['POST'])
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
        return redirect(url_for('file_manager', path=path))
    
    if file:
        filename = secure_filename(file.filename)
        upload_path = os.path.join(path, filename)
        
        # Security: prevent directory traversal
        if '..' in upload_path or upload_path.startswith('/'):
            flash('Invalid path', 'error')
            return redirect(url_for('file_manager', path=path))
        
        try:
            file.save(upload_path)
            flash(f'File "{filename}" uploaded successfully', 'success')
        except Exception as e:
            flash(f'Error uploading file: {str(e)}', 'error')
    
    return redirect(url_for('file_manager', path=path))

@app.route('/root_upload_file', methods=['POST'])
def root_upload_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('root_file_manager'))
    
    file = request.files['file']
    path = request.form.get('path', '.')
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('root_file_manager', path=path))
    
    if file:
        filename = secure_filename(file.filename)
        upload_path = os.path.join(path, filename)
        
        try:
            file.save(upload_path)
            flash(f'File "{filename}" uploaded successfully', 'success')
        except PermissionError:
            flash('Permission denied uploading file', 'error')
        except Exception as e:
            flash(f'Error uploading file: {str(e)}', 'error')
    
    return redirect(url_for('root_file_manager', path=path))

@app.route('/create_folder', methods=['POST'])
def create_folder():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    folder_name = request.form.get('folder_name')
    path = request.form.get('path', '.')
    
    if not folder_name:
        flash('Folder name required', 'error')
        return redirect(url_for('file_manager', path=path))
    
    # Security: prevent directory traversal
    if '..' in folder_name or '/' in folder_name:
        flash('Invalid folder name', 'error')
        return redirect(url_for('file_manager', path=path))
    
    try:
        new_folder = os.path.join(path, folder_name)
        os.makedirs(new_folder, exist_ok=True)
        flash(f'Folder "{folder_name}" created successfully', 'success')
    except Exception as e:
        flash(f'Error creating folder: {str(e)}', 'error')
    
    return redirect(url_for('file_manager', path=path))

@app.route('/root_create_folder', methods=['POST'])
def root_create_folder():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    folder_name = request.form.get('folder_name')
    path = request.form.get('path', '.')
    
    if not folder_name:
        flash('Folder name required', 'error')
        return redirect(url_for('root_file_manager', path=path))
    
    try:
        new_folder = os.path.join(path, folder_name)
        os.makedirs(new_folder, exist_ok=True)
        flash(f'Folder "{folder_name}" created successfully', 'success')
    except PermissionError:
        flash('Permission denied creating folder', 'error')
    except Exception as e:
        flash(f'Error creating folder: {str(e)}', 'error')
    
    return redirect(url_for('root_file_manager', path=path))

@app.route('/move_file', methods=['POST'])
def move_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    source_path = request.form.get('source_path')
    destination_path = request.form.get('destination_path')
    current_path = request.form.get('current_path', '.')
    
    if not source_path or not destination_path:
        flash('Source and destination paths required', 'error')
        return redirect(url_for('file_manager', path=current_path))
    
    # Security: prevent directory traversal
    if '..' in source_path or '..' in destination_path:
        flash('Invalid path', 'error')
        return redirect(url_for('file_manager', path=current_path))
    
    try:
        import shutil
        shutil.move(source_path, destination_path)
        flash('File moved successfully', 'success')
    except Exception as e:
        flash(f'Error moving file: {str(e)}', 'error')
    
    return redirect(url_for('file_manager', path=current_path))

@app.route('/delete_file')
def delete_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    path = request.args.get('path')
    if not path:
        flash('Path required', 'error')
        return redirect(url_for('file_manager'))
    
    # Security: prevent directory traversal
    if '..' in path or path.startswith('/'):
        flash('Invalid path', 'error')
        return redirect(url_for('file_manager'))
    
    try:
        if os.path.isdir(path):
            import shutil
            shutil.rmtree(path)
            flash('Folder deleted successfully', 'success')
        else:
            os.remove(path)
            flash('File deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting: {str(e)}', 'error')
    
    return redirect(url_for('file_manager'))

@app.route('/root_delete_file')
def root_delete_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    path = request.args.get('path')
    if not path:
        flash('Path required', 'error')
        return redirect(url_for('root_file_manager'))
    
    try:
        if os.path.isdir(path):
            import shutil
            shutil.rmtree(path)
            flash('Folder deleted successfully', 'success')
        else:
            os.remove(path)
            flash('File deleted successfully', 'success')
    except PermissionError:
        flash('Permission denied deleting file/folder', 'error')
    except Exception as e:
        flash(f'Error deleting: {str(e)}', 'error')
    
    return redirect(url_for('root_file_manager'))

@app.route('/rename_file', methods=['POST'])
def rename_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    old_path = request.form.get('old_path')
    new_name = request.form.get('new_name')
    current_path = request.form.get('current_path', '.')
    
    if not old_path or not new_name:
        flash('Old path and new name required', 'error')
        return redirect(url_for('file_manager', path=current_path))
    
    # Security: prevent directory traversal
    if '..' in old_path or '..' in new_name or '/' in new_name:
        flash('Invalid path or name', 'error')
        return redirect(url_for('file_manager', path=current_path))
    
    try:
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        os.rename(old_path, new_path)
        flash('File renamed successfully', 'success')
    except Exception as e:
        flash(f'Error renaming file: {str(e)}', 'error')
    
    return redirect(url_for('file_manager', path=current_path))

@app.route('/unarchive_file')
def unarchive_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    path = request.args.get('path')
    current_path = request.args.get('current_path', '.')
    
    if not path:
        flash('Path required', 'error')
        return redirect(url_for('file_manager', path=current_path))
    
    # Security: prevent directory traversal
    if '..' in path or path.startswith('/'):
        flash('Invalid path', 'error')
        return redirect(url_for('file_manager', path=current_path))
    
    try:
        if path.endswith('.zip'):
            with zipfile.ZipFile(path, 'r') as zip_ref:
                zip_ref.extractall(os.path.dirname(path))
            flash('Archive extracted successfully', 'success')
        elif path.endswith(('.tar.gz', '.tgz')):
            import tarfile
            with tarfile.open(path, 'r:gz') as tar_ref:
                tar_ref.extractall(os.path.dirname(path))
            flash('Archive extracted successfully', 'success')
        else:
            flash('Unsupported archive format', 'error')
    except Exception as e:
        flash(f'Error extracting archive: {str(e)}', 'error')
    
    return redirect(url_for('file_manager', path=current_path))

@app.route('/server_unarchive_file/<name>')
def server_unarchive_file(name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if name not in server_manager.servers:
        flash('Server not found', 'error')
        return redirect(url_for('dashboard'))
    
    path = request.args.get('path')
    current_path = request.args.get('current_path', '.')
    
    if not path:
        flash('Path required', 'error')
        return redirect(url_for('server_file_manager', name=name, path=current_path))
    
    # Security: prevent directory traversal
    if '..' in path or path.startswith('/'):
        flash('Invalid path', 'error')
        return redirect(url_for('server_file_manager', name=name, path=current_path))
    
    try:
        server_dir = os.path.join('servers', name)
        full_path = os.path.join(server_dir, path)
        
        if not full_path.startswith(os.path.abspath(server_dir)):
            flash('Access denied', 'error')
            return redirect(url_for('server_file_manager', name=name, path=current_path))
        
        if path.endswith('.zip'):
            with zipfile.ZipFile(full_path, 'r') as zip_ref:
                zip_ref.extractall(os.path.dirname(full_path))
            flash('Archive extracted successfully', 'success')
        elif path.endswith(('.tar.gz', '.tgz')):
            import tarfile
            with tarfile.open(full_path, 'r:gz') as tar_ref:
                tar_ref.extractall(os.path.dirname(full_path))
            flash('Archive extracted successfully', 'success')
        elif path.endswith('.rar'):
            # For RAR files, we'll use unrar if available, otherwise show a message
            try:
                import subprocess
                result = subprocess.run(['unrar', 'x', full_path, os.path.dirname(full_path)], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    flash('RAR archive extracted successfully', 'success')
                else:
                    flash('Failed to extract RAR file. Make sure unrar is installed.', 'error')
            except FileNotFoundError:
                flash('RAR extraction requires unrar to be installed on the system', 'error')
        else:
            flash('Unsupported archive format. Supported: .zip, .tar.gz, .tgz, .rar', 'error')
    except Exception as e:
        flash(f'Error extracting archive: {str(e)}', 'error')
    
    return redirect(url_for('server_file_manager', name=name, path=current_path))

# Server File Manager Routes
@app.route('/server_file_manager/<name>')
@app.route('/server_file_manager/<name>/<path:path>')
def server_file_manager(name, path='.'):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if name not in server_manager.servers:
        flash('Server not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Security: prevent directory traversal
    if '..' in path or path.startswith('/'):
        flash('Invalid path', 'error')
        return redirect(url_for('server_file_manager', name=name))
    
    # Get server directory
    server_dir = os.path.join('servers', name)
    if not os.path.exists(server_dir):
        flash('Server directory not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Get absolute path within server directory
    base_dir = os.path.abspath(server_dir)
    current_path = os.path.abspath(os.path.join(base_dir, path))
    
    # Security: ensure path is within server directory
    if not current_path.startswith(base_dir):
        flash('Access denied', 'error')
        return redirect(url_for('server_file_manager', name=name))
    
    # Handle actions
    action = request.args.get('action')
    if action == 'download' and os.path.isfile(current_path):
        return send_file(current_path, as_attachment=True)
    
    # Get directory contents
    try:
        if os.path.isdir(current_path):
            files = []
            for item in os.listdir(current_path):
                item_path = os.path.join(current_path, item)
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
            
            return render_template('server_file_manager.html',
                                 username=session['username'],
                                 server_name=name,
                                 current_path=path,
                                 files=files)
        else:
            flash('Not a directory', 'error')
            return redirect(url_for('server_file_manager', name=name))
            
    except Exception as e:
        flash(f'Error accessing directory: {str(e)}', 'error')
        return redirect(url_for('server_file_manager', name=name))

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
        
        # Security: prevent directory traversal
        if '..' in upload_path or not upload_path.startswith(os.path.abspath(server_dir)):
            flash('Invalid path', 'error')
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
        os.makedirs(new_folder, exist_ok=True)
        flash(f'Folder "{folder_name}" created successfully', 'success')
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
        
        if not full_path.startswith(os.path.abspath(server_dir)):
            flash('Access denied', 'error')
            return redirect(url_for('server_file_manager', name=name))
        
        if os.path.isdir(full_path):
            import shutil
            shutil.rmtree(full_path)
            flash('Folder deleted successfully', 'success')
        else:
            os.remove(full_path)
            flash('File deleted successfully', 'success')
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
        
        if not old_full_path.startswith(os.path.abspath(server_dir)):
            flash('Access denied', 'error')
            return redirect(url_for('server_file_manager', name=name, path=current_path))
        
        os.rename(old_full_path, new_full_path)
        flash('File renamed successfully', 'success')
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
        import psutil
        import platform
        
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
        
        # System Info
        system_info = {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'hostname': platform.node(),
            'python_version': platform.python_version(),
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
        }
        
        return jsonify(system_info)
    except ImportError:
        return jsonify({'error': 'psutil not installed'}), 500
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
        return jsonify({'error': 'psutil not installed'}), 500
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
        return jsonify({'error': 'Access denied'}), 403
    except ImportError:
        return jsonify({'error': 'psutil not installed'}), 500
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
                if addr.family == psutil.AF_INET:  # IPv4
                    network_info['interfaces'][interface].append({
                        'type': 'IPv4',
                        'address': addr.address,
                        'netmask': addr.netmask
                    })
                elif addr.family == psutil.AF_INET6:  # IPv6
                    network_info['interfaces'][interface].append({
                        'type': 'IPv6',
                        'address': addr.address,
                        'netmask': addr.netmask
                    })
        
        return jsonify(network_info)
    except ImportError:
        return jsonify({'error': 'psutil not installed'}), 500
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
        
        server_dir = os.path.join('servers', name)
        if not os.path.exists(server_dir):
            return jsonify({'error': 'Server directory not found'}), 404
        
        # Create backup directory
        backup_dir = 'backups'
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'{name}_backup_{timestamp}.zip'
        backup_path = os.path.join(backup_dir, backup_filename)
        
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
