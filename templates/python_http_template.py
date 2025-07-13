import os
import sys
import datetime
import http.server
import socketserver
import json
import urllib.parse

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html_content = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Python HTTP Server - Flare Panel</title>
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
                    <h1>🚀 Python HTTP Server Running on Flare Panel!</h1>
                    <div class="info">
                        <p><strong>Status:</strong> <span class="status">✅ Running</span></p>
                        <p><strong>Server:</strong> Python HTTP Server on Flare Panel</p>
                        <p><strong>Port:</strong> {os.environ.get('PORT', '5000')}</p>
                        <p><strong>Host:</strong> {os.environ.get('HOST', '0.0.0.0')}</p>
                        <p><strong>Python:</strong> {sys.version.split()[0]} (3.10.12)</p>
                        <p><strong>Platform:</strong> {sys.platform}</p>
                        <p><strong>Server Name:</strong> {os.environ.get('SERVER_NAME', 'Unknown')}</p>
                        <p><strong>Server Type:</strong> Python HTTP Server</p>
                    </div>
                    <p>This Python HTTP server is running successfully on Flare Panel using socket connections.</p>
                    <p><strong>Current time:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </body>
            </html>
            '''
            self.wfile.write(html_content.encode())
            
        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                'status': 'running',
                'server': 'Python HTTP Server on Flare Panel',
                'message': 'Server is running successfully on Flare Panel!'
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif self.path == '/api/info':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                'server_name': os.environ.get('SERVER_NAME', 'Unknown'),
                'python_version': sys.version,
                'server_type': 'Python HTTP Server',
                'working_directory': os.getcwd(),
                'platform': sys.platform,
                'hostname': os.uname().nodename if hasattr(os, 'uname') else 'Unknown'
            }
            self.wfile.write(json.dumps(response).encode())
            
        else:
            # Serve static files
            super().do_GET()

def start_server(host, port):
    try:
        with socketserver.TCPServer((host, port), CustomHTTPRequestHandler) as httpd:
            print(f"Starting Python HTTP server on {host}:{port}")
            print(f"Working directory: {os.getcwd()}")
            print(f"Server started at: {datetime.datetime.now()}")
            print(f"Python version: {sys.version}")
            print(f"Platform: {sys.platform}")
            print(f"Server type: Python HTTP Server")
            httpd.serve_forever()
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 5000))
        host = os.environ.get('HOST', '0.0.0.0')
        
        # Start server with socket support
        start_server(host, port)
        
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1) 