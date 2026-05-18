"""
Shared utilities for fleet-kit — credential loading, signing, HTTP helpers, fs utils.
Zero external dependencies. Python 3.8+.
"""
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


# ── Credential loading ─────────────────────────────────────────────────────────

def load_key(name: str) -> str:
    """
    Load an API key from an environment variable, falling back to ~/.credentials_vault.

    The vault file uses KEY_NAME=value lines (one per key, no quoting).

    Args:
        name: Environment variable / vault key name (e.g. "OPENAI_API_KEY").

    Returns:
        The key value, or "" if not found.
    """
    key = os.environ.get(name, "")
    if key:
        return key

    vault = Path.home() / ".credentials_vault"
    if vault.exists():
        for line in vault.read_text().splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return ""


# ── HMAC signing ───────────────────────────────────────────────────────────────

def sign_data(data: dict, secret: str) -> str:
    """
    HMAC-SHA256 sign a dictionary after canonicalizing it with sort_keys=True.

    Args:
        data: Dictionary to sign.
        secret: HMAC secret key.

    Returns:
        Hex-encoded signature string.
    """
    payload = json.dumps(data, sort_keys=True, default=str)
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def json_get(url: str, timeout: int = 5) -> dict:
    """
    Perform a GET request and parse the JSON response.

    Args:
        url: Full URL to request.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON dict on success; ``{"error": "<message>"}`` on failure.
    """
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        return {"error": str(exc)}


def json_post(url: str, data: dict, timeout: int = 10) -> dict:
    """
    POST a JSON-encoded body and parse the JSON response.

    Args:
        url: Full URL to POST to.
        data: Dictionary that will be JSON-serialized as the request body.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON dict on success; ``{"error": "<message>"}`` on failure.
    """
    try:
        body = json.dumps(data, default=str).encode()
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        return {"error": str(exc)}


# ── Filesystem helpers ─────────────────────────────────────────────────────────

def ensure_dir(path: str) -> str:
    """
    Ensure a directory exists (mkdir -p), creating parents as needed.

    Args:
        path: Directory path to create.

    Returns:
        The same path that was passed in.
    """
    Path(path).mkdir(parents=True, exist_ok=True)
    return path
