"""
Paestro-specific OAuth endpoints for frontend compatibility.
These endpoints bridge the sophisticated OAuth 2.1 system with the frontend expectations.
"""

import logging
from typing import Dict, Any
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from core.server import server
from auth.credential_store import get_credential_store

logger = logging.getLogger(__name__)

# Initialize credential store
credential_store = get_credential_store()


def get_user_email_from_coach_id(coach_id: str) -> str:
    """
    Convert coach ID to user email for credential lookup.
    For now, we"ll assume the coach_id IS the email or derive it.
    In production, this would lookup the coach"s email from your user database.
    """
    # Temporary: assume coach_id is email format or derive email
    if "@" in coach_id:
        return coach_id
    else:
        # For now, return a placeholder - in production, lookup from your user DB
        return f"{coach_id}@example.com"


@server.custom_route("/coach/{coach_id}/google-oauth-status", methods=["GET"])
async def get_oauth_status(coach_id: str) -> JSONResponse:
    """
    Get OAuth connection status for a coach (Paestro frontend compatibility).
    
    Args:
        coach_id: The coach identifier from frontend
        
    Returns:
        JSON response with connection status
    """
    try:
        user_email = get_user_email_from_coach_id(coach_id)
        
        # Check if credentials exist and are valid
        credentials = credential_store.get_credential(user_email)
        
        if credentials and credentials.valid:
            # Get user info if available
            user_info = getattr(credentials, "id_token", {}) if hasattr(credentials, "id_token") else {}
            
            return JSONResponse({
                "connected": True,
                "needs_auth": False,
                "coach_id": coach_id,
                "email": user_info.get("email", user_email),
                "name": user_info.get("name"),
                "scopes": getattr(credentials, "scopes", []),
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


@server.custom_route("/coach/{coach_id}/google-oauth-disconnect", methods=["POST"])
async def disconnect_oauth(coach_id: str) -> JSONResponse:
    """
    Disconnect Google OAuth for a coach (Paestro frontend compatibility).
    
    Args:
        coach_id: The coach identifier from frontend
        
    Returns:
        JSON response confirming disconnection
    """
    try:
        user_email = get_user_email_from_coach_id(coach_id)
        
        # Remove credentials from store
        revoke_success = credential_store.delete_credential(user_email)
        
        if revoke_success:
            logger.info(f"🔓 OAuth disconnected for coach {coach_id} (email: {user_email})")
            
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


@server.custom_route("/health", methods=["GET"])
async def health_check() -> JSONResponse:
    """
    Enhanced health check with OAuth-specific information.
    """
    try:
        return JSONResponse({
            "service": "google-workspace-mcp",
            "status": "healthy",
            "version": "1.4.6-paestro",
            "oauth_endpoints": {
                "oauth_status": "/coach/{coachId}/google-oauth-status",
                "oauth_disconnect": "/coach/{coachId}/google-oauth-disconnect",
                "oauth_callback": "/oauth2callback"
            },
            "capabilities": [
                "Google OAuth 2.1",
                "Google Calendar API",
                "Google Contacts API", 
                "Google Drive API",
                "Google Sheets API",
                "Persistent credential storage",
                "Token refresh"
            ],
            "timestamp": "2025-01-01T00:00:00Z"
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse({
            "service": "google-workspace-mcp",
            "status": "unhealthy",
            "error": str(e)
        }, status_code=500)


# Additional endpoint for contact integration (used by SMS components)
@server.custom_route("/coach/{coach_id}/google-contacts", methods=["GET"])
async def get_google_contacts(coach_id: str) -> JSONResponse:
    """
    Get Google Contacts for a coach (frontend compatibility).
    
    Args:
        coach_id: The coach identifier from frontend
        
    Returns:
        JSON response with contacts data
    """
    try:
        user_email = get_user_email_from_coach_id(coach_id) 
        
        # Check if credentials exist
        credentials = credential_store.get_credential(user_email)
        
        if not credentials or not credentials.valid:
            return JSONResponse({
                "success": False,
                "contacts": [],
                "error": "Coach not authenticated - OAuth required",
                "coach_id": coach_id
            }, status_code=401)
        
        # For now, return a placeholder response
        # In production, this would call the actual Google Contacts API
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