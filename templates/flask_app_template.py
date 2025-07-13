from flask import Flask, render_template, request, jsonify
import os
import sys
import datetime

app = Flask(__name__)

@app.route('/')
def index():
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Flask Server - Ubuntu VPS</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f0f0f0; }}
            .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #333; }}
            .info {{ background: #e8f4fd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .status {{ color: #28a745; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Flask Server Running on Ubuntu VPS!</h1>
            <div class="info">
                <p><strong>Status:</strong> <span class="status">✅ Running</span></p>
                <p><strong>Server:</strong> Python Flask on Ubuntu</p>
                <p><strong>Port:</strong> {os.environ.get('PORT', '5000')}</p>
                <p><strong>Host:</strong> {os.environ.get('HOST', '0.0.0.0')}</p>
                <p><strong>Python:</strong> {sys.version.split()[0]} (3.10.12)</p>
                <p><strong>Platform:</strong> {sys.platform}</p>
                <p><strong>Server Name:</strong> {os.environ.get('SERVER_NAME', 'Unknown')}</p>
            </div>
            <p>This Flask application is running successfully on Ubuntu VPS. You can modify this file to add your own routes and functionality.</p>
            <p><strong>Current time:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    '''

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'running',
        'server': 'Python Flask on Ubuntu',
        'message': 'Server is running successfully on VPS!'
    })

@app.route('/api/info')
def info():
    return jsonify({
        'server_name': os.environ.get('SERVER_NAME', 'Unknown'),
        'python_version': sys.version,
        'flask_version': '2.0+',
        'working_directory': os.getcwd(),
        'platform': sys.platform,
        'hostname': os.uname().nodename if hasattr(os, 'uname') else 'Unknown'
    })

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 5000))
        host = os.environ.get('HOST', '0.0.0.0')
        
        print(f"Starting Flask server on {host}:{port}")
        print(f"Working directory: {os.getcwd()}")
        print(f"Server started at: {datetime.datetime.now()}")
        print(f"Python version: {sys.version}")
        print(f"Platform: {sys.platform}")
        
        # Use Ubuntu/Linux compatible configuration
        app.run(
            host=host, 
            port=port, 
            debug=False,
            threaded=True
        )
        
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)
