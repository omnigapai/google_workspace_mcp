#!/usr/bin/env python3
"""
Ultra-minimal Railway deployment server.
Just to get SOMETHING working on Railway.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "status": "healthy",
                "service": "google-workspace-mcp",
                "version": "1.4.6",
                "transport": "http"
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"🚀 RAILWAY SERVER STARTING ON PORT {port}")
    server.serve_forever()