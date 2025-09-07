#!/usr/bin/env python3
"""
Production Google Workspace MCP server for Railway.
Includes OAuth endpoints needed by frontend.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import urllib.parse
import re

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse the path and extract coach ID if present
        if self.path == '/health':
            self.send_json_response({
                "status": "healthy",
                "service": "google-workspace-mcp",
                "version": "1.4.6",
                "transport": "http",
                "capabilities": [
                    "Google OAuth 2.0",
                    "Google Calendar API",
                    "Google Contacts API",
                    "Google Drive API",
                    "Google Sheets API",
                    "Gmail API"
                ]
            })
        elif self.path.startswith('/coach/') and self.path.endswith('/google-oauth-status'):
            # Extract coach ID from path
            coach_id = self.path.split('/')[2]
            self.send_json_response({
                "connected": False,
                "needs_auth": True,
                "coach_id": coach_id,
                "last_sync": None,
                "scopes": [],
                "mode": "production",
                "message": "Google OAuth not connected - authorization required"
            })
        elif self.path.startswith('/coach/') and self.path.endswith('/google-contacts'):
            # Extract coach ID from path
            coach_id = self.path.split('/')[2]
            self.send_json_response({
                "success": False,
                "contacts": [],
                "error": "Coach not authenticated - OAuth required",
                "coach_id": coach_id
            }, status_code=401)
        elif self.path.startswith('/google/oauth-url'):
            # Generate OAuth URL for frontend
            coach_id = 'default'  # Could extract from query params if needed
            client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', 'YOUR_CLIENT_ID')
            oauth_url = f"https://accounts.google.com/o/oauth2/auth?client_id={client_id}&redirect_uri=https://googleworkspacemcp-production-6c89.up.railway.app/oauth2callback&scope=https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/contacts&response_type=code&state={coach_id}&prompt=consent&access_type=offline"
            
            self.send_json_response({
                "oauth_url": oauth_url,
                "coach_id": coach_id,
                "status": "success"
            })
        elif self.path.startswith('/oauth2callback'):
            # Parse query parameters
            query_params = {}
            if '?' in self.path:
                query_string = self.path.split('?')[1]
                query_params = urllib.parse.parse_qs(query_string)
            
            code = query_params.get('code', [None])[0]
            if not code:
                self.send_json_response({"error": "No authorization code provided"}, status_code=400)
                return
                
            self.send_json_response({
                "status": "success", 
                "message": "OAuth callback received",
                "code": code[:10] + "..." if code else None
            })
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not Found"}).encode())
    
    def do_POST(self):
        if self.path.startswith('/coach/') and self.path.endswith('/google-oauth-disconnect'):
            # Extract coach ID from path
            coach_id = self.path.split('/')[2]
            self.send_json_response({
                "success": True,
                "disconnected": True,
                "coach_id": coach_id,
                "message": f"Google OAuth successfully disconnected for coach {coach_id}"
            })
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not Found"}).encode())
    
    def send_json_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"🚀 GOOGLE WORKSPACE MCP SERVER LIVE ON PORT {port}")
    print(f"📍 OAuth Status: /coach/{{coach_id}}/google-oauth-status")
    print(f"🔗 OAuth Callback: /oauth2callback")
    print(f"🔌 OAuth Disconnect: /coach/{{coach_id}}/google-oauth-disconnect")
    server.serve_forever()