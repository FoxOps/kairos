"""
Token management utilities for Leviia Schedule.

This module provides functions for generating and validating tokens
used for ICS exports and other features.
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional


def generate_token(length: int = 32) -> str:
    """
    Generate a secure random token.
    
    Args:
        length: Length of the token in bytes (default: 32)
        
    Returns:
        URL-safe token string
    """
    return secrets.token_urlsafe(length)


def validate_token(token: str, expected_token: str) -> bool:
    """
    Validate a token against an expected value.
    
    Args:
        token: Token to validate
        expected_token: Expected token value
        
    Returns:
        True if tokens match, False otherwise
    """
    return secrets.compare_digest(token, expected_token)


def hash_token(token: str) -> str:
    """
    Hash a token for storage.
    
    Args:
        token: Token to hash
        
    Returns:
        SHA-256 hash of the token
    """
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def generate_expiring_token(length: int = 32, expires_in: int = 86400) -> dict:
    """
    Generate a token with an expiration time.
    
    Args:
        length: Length of the token in bytes (default: 32)
        expires_in: Token expiration time in seconds (default: 86400 = 24 hours)
        
    Returns:
        Dictionary with 'token' and 'expires_at' keys
    """
    token = generate_token(length)
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    
    return {
        'token': token,
        'expires_at': expires_at,
        'created_at': datetime.utcnow()
    }


def is_token_expired(expires_at: datetime) -> bool:
    """
    Check if a token has expired.
    
    Args:
        expires_at: Expiration datetime of the token
        
    Returns:
        True if token has expired, False otherwise
    """
    return datetime.utcnow() > expires_at
