#!/usr/bin/env python3
"""
FastAPI HTTP server wrapper for Google Workspace MCP.
This provides HTTP endpoints that can be called by the orchestrator.
"""

import os
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the credential store
from auth.credential_store import get_credential_store

# Create FastAPI app
app = FastAPI(title="Google Workspace MCP", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize credential store
credential_store = get_credential_store()

def get_user_email_from_coach_id(coach_id: str) -> str:
    """Convert coach ID to user email for credential lookup."""
    if "@" in coach_id:
        return coach_id
    else:
        return f"{coach_id}@example.com"


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse({
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


@app.get("/coach/{coach_id}/google-oauth-status")
async def get_oauth_status(coach_id: str):
    """Get OAuth connection status for a coach."""
    try:
        user_email = get_user_email_from_coach_id(coach_id)
        credentials = credential_store.get_credential(user_email)
        
        if credentials and credentials.valid:
            user_info = getattr(credentials, 'id_token', {}) if hasattr(credentials, 'id_token') else {}
            
            return JSONResponse({
                "connected": True,
                "needs_auth": False,
                "coach_id": coach_id,
                "email": user_info.get('email', user_email),
                "name": user_info.get('name'),
                "scopes": getattr(credentials, 'scopes', []),
                "last_sync": credentials.expiry.isoformat() if credentials.expiry else None,
                "mode": "production",
                "message": "Google OAuth connected and active"
            })
        else:
            return JSONResponse({
                "connected": False,
                "needs_auth": True,
                "coach_id": coach_id,
                "last_sync": None,
                "scopes": [],
                "mode": "production",
                "message": "Google OAuth not connected - authorization required"
            })
            
    except Exception as e:
        logger.error(f"OAuth status check failed for coach {coach_id}: {e}")
        return JSONResponse({
            "connected": False,
            "needs_auth": True,
            "coach_id": coach_id,
            "error": str(e),
            "mode": "production",
            "message": "OAuth status check failed"
        }, status_code=500)


@app.post("/coach/{coach_id}/google-oauth-disconnect")
async def disconnect_oauth(coach_id: str):
    """Disconnect Google OAuth for a coach."""
    try:
        user_email = get_user_email_from_coach_id(coach_id)
        revoke_success = credential_store.delete_credential(user_email)
        
        if revoke_success:
            logger.info(f"OAuth disconnected for coach {coach_id}")
            
            return JSONResponse({
                "success": True,
                "disconnected": True,
                "coach_id": coach_id,
                "message": f"Google OAuth successfully disconnected for coach {coach_id}"
            })
        else:
            return JSONResponse({
                "success": False,
                "disconnected": False,
                "coach_id": coach_id,
                "error": "Failed to disconnect OAuth - credentials may not exist",
                "message": "Disconnect operation failed"
            }, status_code=400)
            
    except Exception as e:
        logger.error(f"OAuth disconnect failed for coach {coach_id}: {e}")
        return JSONResponse({
            "success": False,
            "disconnected": False,
            "coach_id": coach_id,
            "error": str(e),
            "message": "OAuth disconnect operation failed"
        }, status_code=500)


@app.get("/coach/{coach_id}/google-contacts")
async def get_google_contacts(coach_id: str):
    """Get Google Contacts for a coach."""
    try:
        user_email = get_user_email_from_coach_id(coach_id)
        credentials = credential_store.get_credential(user_email)
        
        if not credentials or not credentials.valid:
            return JSONResponse({
                "success": False,
                "contacts": [],
                "error": "Coach not authenticated - OAuth required",
                "coach_id": coach_id
            }, status_code=401)
        
        return JSONResponse({
            "success": True,
            "contacts": [],
            "message": "Google Contacts integration - use MCP tools for full functionality",
            "coach_id": coach_id,
            "mode": "production"
        })
        
    except Exception as e:
        logger.error(f"Google Contacts request failed for coach {coach_id}: {e}")
        return JSONResponse({
            "success": False,
            "contacts": [],
            "error": str(e),
            "coach_id": coach_id
        }, status_code=500)


@app.get("/oauth2callback")
async def oauth_callback(code: Optional[str] = None, state: Optional[str] = None):
    """Handle OAuth callback from Google."""
    if not code:
        return JSONResponse({"error": "No authorization code provided"}, status_code=400)
    
    # This would normally process the OAuth callback
    # For now, just acknowledge it
    return JSONResponse({
        "status": "success",
        "message": "OAuth callback received",
        "code": code[:10] + "..." if code else None
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting Google Workspace MCP HTTP server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)