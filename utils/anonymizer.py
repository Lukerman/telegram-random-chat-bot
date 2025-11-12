"""
Anonymization utilities.

Handles generation of anonymous user identifiers.
"""

import secrets
import string


def generate_anon_id(length: int = 8) -> str:
    """
    Generate a unique anonymous identifier.
    
    Args:
        length: Length of the random part (default: 8)
        
    Returns:
        Anonymous ID in format 'u_XXXXXXXX'
    """
    chars = string.ascii_lowercase + string.digits
    random_part = ''.join(secrets.choice(chars) for _ in range(length))
    return f"u_{random_part}"