#!/usr/bin/env python3
"""
Minimal FastAPI HTTP server for Google Workspace MCP.
Testing Railway deployment without credential store initialization.
"""

import os
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom middleware to add COOP and COEP headers for OAuth popup support
class OAuthHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Add OAuth-friendly headers to allow popup communication
        response.headers["Cross-Origin-Opener-Policy"] = "unsafe-none"
        response.headers["Cross-Origin-Embedder-Policy"] = "unsafe-none"
        return response

# Create FastAPI app
app = FastAPI(title="Google Workspace MCP", version="1.0.0")

# Add OAuth headers middleware (must be added before CORS)
app.add_middleware(OAuthHeadersMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return JSONResponse({
        "connected": False,
        "needs_auth": True,
        "coach_id": coach_id,
        "last_sync": None,
        "scopes": [],
        "mode": "production",
        "message": "Minimal server - credential store not initialized"
    })

@app.get("/oauth2callback")
async def oauth_callback(code: Optional[str] = None, state: Optional[str] = None):
    """Handle OAuth callback from Google."""
    if not code:
        return JSONResponse({"error": "No authorization code provided"}, status_code=400)
    
    return JSONResponse({
        "status": "success",
        "message": "OAuth callback received - minimal server",
        "code": code[:10] + "..." if code else None
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting Google Workspace MCP HTTP server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)