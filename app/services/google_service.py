# app/services/google_service.py
"""
Google ID token verification.
The frontend (Next.js) uses Google Identity Services to get an ID token,
then POSTs it to /auth/google. We verify it here.
"""

import logging
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from fastapi import HTTPException, status

from app.config.settings import GOOGLE_CLIENT_ID

logger = logging.getLogger(__name__)


async def verify_google_id_token(token: str) -> dict:
    """
    Verify a Google ID token and return its payload.

    Runs in a thread because `id_token.verify_oauth2_token` makes a network
    call to fetch Google's public keys (cached after first call).
    """
    try:
        # Note: verify_oauth2_token is sync + does network I/O on first call
        payload = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except ValueError as e:
        logger.warning(f"Google token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )

    # Verify the issuer
    if payload.get("iss") not in (
        "accounts.google.com",
        "https://accounts.google.com",
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token issuer",
        )

    if not payload.get("email"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account has no email",
        )

    return payload