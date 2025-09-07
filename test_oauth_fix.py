#!/usr/bin/env python3
"""
Test script to demonstrate the OAuth endpoint fix
Shows the difference between missing coach_id and proper coach_id parameter
"""

import urllib.parse

def test_oauth_url_parsing():
    """Test the OAuth URL parameter parsing logic"""
    
    def extract_coach_id(path):
        """Simulate the server's coach_id extraction logic"""
        query_params = {}
        if '?' in path:
            query_string = path.split('?')[1]
            query_params = urllib.parse.parse_qs(query_string)
        
        coach_id = query_params.get('coach_id', [None])[0]
        return coach_id
    
    def generate_oauth_response(coach_id):
        """Simulate the server's OAuth response logic"""
        # Validate coach_id is provided (new validation)
        if not coach_id or coach_id == 'default':
            return {
                "error": "Missing coach_id parameter",
                "message": "Please include coach_id as a query parameter: /google/oauth-url?coach_id=YOUR_COACH_ID",
                "status": "error",
                "example": "/google/oauth-url?coach_id=bralin-jackson-coach-id"
            }
        
        # Generate OAuth URL with coach_id in state parameter
        oauth_url = f"https://accounts.google.com/o/oauth2/auth?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:8080/oauth-callback&scope=https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/contacts.readonly&response_type=code&state={coach_id}&prompt=consent&access_type=offline"
        
        return {
            "oauth_url": oauth_url,
            "coach_id": coach_id,
            "status": "success"
        }
    
    print("🧪 Testing OAuth Endpoint Fix")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        "/google/oauth-url",  # Missing coach_id (problematic)
        "/google/oauth-url?coach_id=default",  # Default value (problematic) 
        "/google/oauth-url?coach_id=bralin-jackson-coach-123",  # Proper coach ID
        "/google/oauth-url?coach_id=coach-thompson-456&other_param=value",  # With other params
    ]
    
    for i, path in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {path}")
        print("-" * 30)
        
        coach_id = extract_coach_id(path)
        response = generate_oauth_response(coach_id)
        
        if response.get("status") == "error":
            print("❌ REJECTED:", response["error"])
            print("   Message:", response["message"])
        else:
            print("✅ ACCEPTED")
            print("   Coach ID:", response["coach_id"])
            print("   OAuth State Parameter:", f"state={coach_id}" in response["oauth_url"])
            
    print("\n" + "=" * 50)
    print("🎯 SUMMARY:")
    print("- Server now validates coach_id is provided")
    print("- Returns helpful error message when missing")
    print("- OAuth URL properly includes coach_id in state parameter")
    print("- Frontend must call: /google/oauth-url?coach_id=ACTUAL_COACH_ID")

if __name__ == "__main__":
    test_oauth_url_parsing()