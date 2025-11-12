"""
Input validation utilities.

Validates user inputs and data.
"""

from typing import Optional


def validate_gender(gender: str) -> bool:
    """
    Validate gender value.
    
    Args:
        gender: Gender string to validate
        
    Returns:
        True if valid
    """
    return gender in ["male", "female", "other"]


def validate_preference(preference: str) -> bool:
    """
    Validate chat preference value.
    
    Args:
        preference: Preference string to validate
        
    Returns:
        True if valid
    """
    return preference in ["any", "same", "opposite", "other"]