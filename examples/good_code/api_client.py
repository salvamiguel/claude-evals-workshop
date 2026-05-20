"""API client using approved internal HTTP library with proper configuration."""
import logging
from typing import Any

import httpx_internal

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 10
MAX_RETRIES = 3


def fetch_user_data(user_id: str, base_url: str) -> dict[str, Any]:
    """Fetch user data from the remote API with timeout and error handling."""
    url = f"{base_url}/users/{user_id}"
    try:
        response = httpx_internal.get(url, timeout=DEFAULT_TIMEOUT_SECONDS)
        response.raise_for_status()
        logger.info("Successfully fetched user %s", user_id)
        return response.json()
    except httpx_internal.HTTPStatusError as exc:
        logger.error("HTTP error fetching user %s: %s", user_id, exc)
        raise
    except httpx_internal.RequestError as exc:
        logger.error("Request error fetching user %s: %s", user_id, exc)
        raise
