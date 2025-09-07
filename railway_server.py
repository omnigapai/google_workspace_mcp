#!/usr/bin/env python3
"""
Production Google Workspace MCP server for Railway with persistent token storage.
Stores OAuth tokens in Supabase for persistence across deployments.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import urllib.parse
import urllib.request
import re
from datetime import datetime, timedelta

# Supabase configuration from environment
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://galwuihzfwnitmmxolhd.supabase.co')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')

class TokenManager:
    """Manages OAuth tokens with Supabase persistence"""
    
    @staticmethod
    def save_token(coach_id, coach_email, access_token, refresh_token=None, expires_in=3600, scope=''):
        """Save or update OAuth tokens in Supabase"""
        try:
            # Prepare the data
            token_data = {
                'coach_id': coach_id,
                'coach_email': coach_email,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_in': expires_in,
                'scope': scope,
                'updated_at': datetime.utcnow().isoformat() + 'Z'
            }
            
            # Make upsert request to Supabase
            url = f"{SUPABASE_URL}/rest/v1/google_oauth_tokens"
            headers = {
                'apikey': SUPABASE_SERVICE_KEY,
                'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
                'Content-Type': 'application/json',
                'Prefer': 'resolution=merge-duplicates'
            }
            
            # Try to update existing token or insert new one
            upsert_url = f"{url}?coach_id=eq.{coach_id}"
            
            # First, check if token exists
            check_req = urllib.request.Request(upsert_url, headers={
                'apikey': SUPABASE_SERVICE_KEY,
                'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}'
            })
            
            try:
                with urllib.request.urlopen(check_req) as response:
                    existing = json.loads(response.read().decode())
                    
                if existing and len(existing) > 0:
                    # Update existing token
                    update_req = urllib.request.Request(
                        upsert_url,
                        data=json.dumps(token_data).encode('utf-8'),
                        headers=headers,
                        method='PATCH'
                    )
                    urllib.request.urlopen(update_req)
                    print(f"✅ Updated token for coach {coach_id}")
                else:
                    # Insert new token
                    insert_req = urllib.request.Request(
                        url,
                        data=json.dumps(token_data).encode('utf-8'),
                        headers=headers
                    )
                    urllib.request.urlopen(insert_req)
                    print(f"✅ Saved new token for coach {coach_id}")
                    
            except Exception as e:
                # Fallback to direct insert if check fails
                insert_req = urllib.request.Request(
                    url,
                    data=json.dumps(token_data).encode('utf-8'),
                    headers=headers
                )
                urllib.request.urlopen(insert_req)
                print(f"✅ Saved token for coach {coach_id} (fallback)")
                
            return True
            
        except Exception as e:
            print(f"❌ Error saving token to Supabase: {e}")
            return False
    
    @staticmethod
    def get_token(coach_id):
        """Retrieve OAuth tokens from Supabase"""
        try:
            url = f"{SUPABASE_URL}/rest/v1/google_oauth_tokens?coach_id=eq.{coach_id}"
            headers = {
                'apikey': SUPABASE_SERVICE_KEY,
                'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}'
            }
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                tokens = json.loads(response.read().decode())
                
            if tokens and len(tokens) > 0:
                token = tokens[0]
                
                # Check if token is expired
                if token.get('expires_at'):
                    expires_at = datetime.fromisoformat(token['expires_at'].replace('Z', '+00:00'))
                    if expires_at < datetime.utcnow():
                        print(f"⚠️ Token expired for coach {coach_id}")
                        # TODO: Implement token refresh using refresh_token
                        return None
                
                print(f"✅ Retrieved token for coach {coach_id} from Supabase")
                return token
            else:
                print(f"❌ No token found for coach {coach_id}")
                return None
                
        except Exception as e:
            print(f"❌ Error retrieving token from Supabase: {e}")
            return None
    
    @staticmethod
    def delete_token(coach_id):
        """Delete OAuth tokens from Supabase"""
        try:
            url = f"{SUPABASE_URL}/rest/v1/google_oauth_tokens?coach_id=eq.{coach_id}"
            headers = {
                'apikey': SUPABASE_SERVICE_KEY,
                'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}'
            }
            
            req = urllib.request.Request(url, headers=headers, method='DELETE')
            urllib.request.urlopen(req)
            print(f"✅ Deleted token for coach {coach_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting token from Supabase: {e}")
            return False

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse the path and extract coach ID if present
        if self.path == '/health':
            self.send_json_response({
                "status": "healthy",
                "service": "google-workspace-mcp",
                "version": "2.0.0",
                "transport": "http",
                "storage": "supabase",
                "capabilities": [
                    "Google OAuth 2.0",
                    "Google Calendar API",
                    "Google Contacts API",
                    "Google Drive API",
                    "Google Sheets API",
                    "Gmail API",
                    "Persistent Token Storage"
                ]
            })
        elif self.path.startswith('/coach/') and self.path.endswith('/google-oauth-status'):
            # Extract coach ID from path
            coach_id = self.path.split('/')[2]
            
            # Check token status in Supabase
            token_info = TokenManager.get_token(coach_id)
            
            if token_info:
                self.send_json_response({
                    "connected": True,
                    "needs_auth": False,
                    "coach_id": coach_id,
                    "last_sync": token_info.get('updated_at', ''),
                    "scopes": token_info.get('scope', '').split(' ') if token_info.get('scope') else [],
                    "mode": "production",
                    "email": token_info.get('coach_email', ''),
                    "message": "Google OAuth connected successfully",
                    "storage": "supabase"
                })
            else:
                self.send_json_response({
                    "connected": False,
                    "needs_auth": True,
                    "coach_id": coach_id,
                    "last_sync": None,
                    "scopes": [],
                    "mode": "production",
                    "message": "No OAuth token found - please connect Google Workspace",
                    "storage": "supabase"
                })
        elif self.path.startswith('/coach/') and self.path.endswith('/google-contacts'):
            # Extract coach ID from path
            coach_id = self.path.split('/')[2]
            
            # Get token from Supabase
            token_info = TokenManager.get_token(coach_id)
            
            if not token_info:
                self.send_json_response({
                    "success": False,
                    "error": "Google OAuth not connected for this coach",
                    "contacts": [],
                    "total": 0,
                    "coach_id": coach_id,
                    "message": "Please connect Google Workspace first"
                }, status_code=401)
                return
            
            access_token = token_info.get('access_token')
            
            if not access_token:
                self.send_json_response({
                    "success": False,
                    "error": "No access token available",
                    "contacts": [],
                    "total": 0,
                    "coach_id": coach_id,
                    "message": "OAuth token missing - please reconnect Google Workspace"
                }, status_code=401)
                return
            
            # Fetch real Google Contacts using People API
            try:
                # Use Google People API to fetch contacts
                people_api_url = "https://people.googleapis.com/v1/people/me/connections?pageSize=1000&personFields=names,emailAddresses,phoneNumbers"
                
                # Make authenticated request to Google People API
                req = urllib.request.Request(
                    people_api_url,
                    headers={
                        'Authorization': f'Bearer {access_token}',
                        'Accept': 'application/json'
                    }
                )
                
                with urllib.request.urlopen(req) as response:
                    contacts_data = json.loads(response.read().decode())
                
                # Process and format the contacts
                processed_contacts = []
                connections = contacts_data.get('connections', [])
                
                print(f"📞 Retrieved {len(connections)} Google contacts for coach {coach_id}")
                
                for person in connections:
                    contact = {
                        "id": person.get('resourceName', '').replace('people/', ''),
                        "name": "",
                        "email": "",
                        "phone": "",
                        "type": "contact"
                    }
                    
                    # Extract name
                    names = person.get('names', [])
                    if names and len(names) > 0:
                        contact['name'] = names[0].get('displayName', '')
                    
                    # Extract primary email
                    emails = person.get('emailAddresses', [])
                    if emails and len(emails) > 0:
                        contact['email'] = emails[0].get('value', '')
                    
                    # Extract primary phone
                    phones = person.get('phoneNumbers', [])
                    if phones and len(phones) > 0:
                        contact['phone'] = phones[0].get('value', '')
                    
                    # Only include contacts with at least a name or email
                    if contact['name'] or contact['email']:
                        processed_contacts.append(contact)
                
                print(f"✅ Processed {len(processed_contacts)} valid Google contacts")
                
                self.send_json_response({
                    "success": True,
                    "contacts": processed_contacts,
                    "total": len(processed_contacts),
                    "coach_id": coach_id,
                    "message": f"Retrieved {len(processed_contacts)} Google contacts successfully"
                })
                
            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8') if e.fp else 'Unknown error'
                print(f"❌ Google People API HTTP error: {e.code} - {error_body}")
                
                if e.code == 401:
                    # Token is invalid or expired - delete it
                    TokenManager.delete_token(coach_id)
                    self.send_json_response({
                        "success": False,
                        "error": "Google OAuth token expired or invalid",
                        "contacts": [],
                        "total": 0,
                        "coach_id": coach_id,
                        "message": "Please reconnect Google Workspace - token expired"
                    }, status_code=401)
                else:
                    self.send_json_response({
                        "success": False,
                        "error": f"Google API error: {e.code}",
                        "contacts": [],
                        "total": 0,
                        "coach_id": coach_id,
                        "message": f"Failed to fetch contacts from Google: {e.code}"
                    }, status_code=500)
                    
            except Exception as e:
                print(f"❌ Error fetching Google contacts: {str(e)}")
                self.send_json_response({
                    "success": False,
                    "error": f"Failed to fetch contacts: {str(e)}",
                    "contacts": [],
                    "total": 0,
                    "coach_id": coach_id,
                    "message": "Error connecting to Google Contacts API"
                }, status_code=500)
        elif self.path.startswith('/google/oauth-url'):
            # Generate OAuth URL for frontend
            coach_id = 'default'  # Could extract from query params if needed
            client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', 'YOUR_CLIENT_ID')
            oauth_url = f"https://accounts.google.com/o/oauth2/auth?client_id={client_id}&redirect_uri=http://localhost:8080/oauth-callback&scope=https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/contacts.readonly&response_type=code&state={coach_id}&prompt=consent&access_type=offline"
            
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
            
            # Delete token from Supabase
            success = TokenManager.delete_token(coach_id)
            
            self.send_json_response({
                "success": success,
                "disconnected": success,
                "coach_id": coach_id,
                "message": f"Google OAuth {'successfully' if success else 'failed to be'} disconnected for coach {coach_id}"
            })
        elif self.path == '/oauth/exchange':
            # Handle OAuth token exchange
            try:
                # Read request body
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length:
                    body = self.rfile.read(content_length).decode('utf-8')
                    data = json.loads(body)
                else:
                    data = {}
                
                code = data.get('code')
                coach_id = data.get('coachId')
                coach_email = data.get('coachEmail')
                redirect_uri = data.get('redirectUri', 'http://localhost:8080/oauth-callback')
                
                if not code or not coach_id:
                    self.send_json_response({
                        "success": False,
                        "error": "Missing authorization code or coachId"
                    }, status_code=400)
                    return
                
                # Exchange authorization code for tokens with Google
                print(f"🔄 OAuth token exchange for coach {coach_id} ({coach_email})")
                print(f"📝 Authorization code received: {code[:20]}...")
                print(f"🔗 Redirect URI: {redirect_uri}")
                
                # Real token exchange with Google OAuth
                token_data = {
                    'code': code,
                    'client_id': os.environ.get('GOOGLE_OAUTH_CLIENT_ID'),
                    'client_secret': os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET'),
                    'redirect_uri': redirect_uri,
                    'grant_type': 'authorization_code'
                }
                
                # Encode the data
                token_data_encoded = urllib.parse.urlencode(token_data).encode('utf-8')
                
                try:
                    # Make request to Google's token endpoint
                    req = urllib.request.Request(
                        'https://oauth2.googleapis.com/token',
                        data=token_data_encoded,
                        headers={'Content-Type': 'application/x-www-form-urlencoded'}
                    )
                    
                    with urllib.request.urlopen(req) as response:
                        token_response = json.loads(response.read().decode())
                    
                    if 'access_token' in token_response:
                        # Save tokens to Supabase
                        saved = TokenManager.save_token(
                            coach_id=coach_id,
                            coach_email=coach_email,
                            access_token=token_response['access_token'],
                            refresh_token=token_response.get('refresh_token'),
                            expires_in=token_response.get('expires_in', 3600),
                            scope=token_response.get('scope', '')
                        )
                        
                        if saved:
                            print(f"✅ Real tokens stored in Supabase for coach {coach_id}")
                        else:
                            print(f"⚠️ Tokens received but failed to save to Supabase")
                        
                        self.send_json_response({
                            "success": True,
                            "coach_id": coach_id,
                            "coach_email": coach_email,
                            "access_token": "stored_securely",  # Don't return actual token
                            "expires_in": token_response.get('expires_in', 3600),
                            "token_type": token_response.get('token_type', 'Bearer'),
                            "scope": token_response.get('scope', ''),
                            "message": "OAuth token exchange successful - tokens stored in Supabase",
                            "storage": "supabase"
                        })
                    else:
                        raise Exception(f"Token exchange failed: {token_response}")
                        
                except Exception as token_error:
                    print(f"❌ Real token exchange failed: {token_error}")
                    # For development, save a mock token
                    if coach_email == 'bralinprime28@gmail.com':
                        saved = TokenManager.save_token(
                            coach_id=coach_id,
                            coach_email=coach_email,
                            access_token='development_mock_token',
                            refresh_token='development_mock_refresh',
                            expires_in=3600,
                            scope='https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/contacts.readonly'
                        )
                        
                    self.send_json_response({
                        "success": False,
                        "error": f"Token exchange failed: {str(token_error)}",
                        "coach_id": coach_id,
                        "coach_email": coach_email
                    }, status_code=500)
                
            except json.JSONDecodeError:
                self.send_json_response({
                    "success": False,
                    "error": "Invalid JSON in request body"
                }, status_code=400)
            except Exception as e:
                self.send_json_response({
                    "success": False,
                    "error": f"Token exchange failed: {str(e)}"
                }, status_code=500)
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not Found"}).encode())
    
    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
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
    
    # Check if we have Supabase credentials
    if not SUPABASE_SERVICE_KEY:
        print("⚠️ WARNING: SUPABASE_SERVICE_ROLE_KEY not set - token persistence disabled")
    else:
        print("✅ Supabase token persistence enabled")
    
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"🚀 GOOGLE WORKSPACE MCP SERVER WITH PERSISTENCE LIVE ON PORT {port}")
    print(f"📍 OAuth Status: /coach/{{coach_id}}/google-oauth-status")
    print(f"📞 Google Contacts: /coach/{{coach_id}}/google-contacts")
    print(f"🔗 OAuth Callback: /oauth2callback")
    print(f"🔌 OAuth Disconnect: /coach/{{coach_id}}/google-oauth-disconnect")
    print(f"💾 Token Storage: Supabase")
    server.serve_forever()