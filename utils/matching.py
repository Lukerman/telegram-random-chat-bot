"""
User matching utilities.

Handles finding compatible chat partners based on preferences.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from database.mongodb import get_db

logger = logging.getLogger(__name__)


async def find_match(user: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Find a compatible chat partner for the user.
    
    Args:
        user: User document seeking a match
        
    Returns:
        Matched user document or None if no match found
    """
    db = get_db()
    
    # Build query for potential partners
    query = {
        "tg_id": {"$ne": user["tg_id"]},  # Not the same user
        "is_banned": False,  # Not banned
        "anon_id": {"$nin": user.get("blocked_users", [])}  # Not blocked by requester
    }
    
    # Also ensure the requester is not in partner's blocked list
    query["blocked_users"] = {"$nin": [user["anon_id"]]}
    
    # Apply gender preference matching
    user_gender = user.get("gender")
    user_pref = user.get("preference", "any")
    
    if user_pref == "same":
        query["gender"] = user_gender
        query["preference"] = {"$in": ["any", "same"]}
    elif user_pref == "opposite":
        opposite = {
            "male": "female",
            "female": "male",
            "other": "other"
        }
        query["gender"] = opposite.get(user_gender, "other")
        query["preference"] = {"$in": ["any", "opposite"]}
    elif user_pref == "other":
        query["gender"] = "other"
        query["preference"] = {"$in": ["any", "other"]}
    else:  # any
        query["preference"] = {"$ne": None}  # Any valid preference
    
    # Find users not currently in a session
    active_sessions = await db.sessions.find({"status": "active"}).to_list(length=None)
    active_user_ids = []
    for session in active_sessions:
        active_user_ids.append(session["user1"]["tg_id"])
        active_user_ids.append(session["user2"]["tg_id"])
    
    query["tg_id"] = {"$nin": active_user_ids + [user["tg_id"]]}
    
    # Find potential matches, prioritize recently active users
    potential_matches = await db.users.find(query).sort("last_active", -1).to_list(length=20)
    
    # Validate mutual compatibility
    for partner in potential_matches:
        if is_compatible(user, partner):
            logger.info(f"Match found: {user['anon_id']} <-> {partner['anon_id']}")
            return partner
    
    logger.info(f"No match found for user {user['anon_id']}")
    return None


def is_compatible(user1: Dict[str, Any], user2: Dict[str, Any]) -> bool:
    """
    Check if two users are compatible for matching.
    
    Args:
        user1: First user document
        user2: Second user document
        
    Returns:
        True if users are compatible
    """
    u1_gender = user1.get("gender")
    u1_pref = user1.get("preference", "any")
    u2_gender = user2.get("gender")
    u2_pref = user2.get("preference", "any")
    
    # Check user1's preference against user2's gender
    if u1_pref == "same" and u1_gender != u2_gender:
        return False
    
    if u1_pref == "opposite":
        opposite = {"male": "female", "female": "male", "other": "other"}
        if opposite.get(u1_gender) != u2_gender:
            return False
    
    if u1_pref == "other" and u2_gender != "other":
        return False
    
    # Check user2's preference against user1's gender
    if u2_pref == "same" and u2_gender != u1_gender:
        return False
    
    if u2_pref == "opposite":
        opposite = {"male": "female", "female": "male", "other": "other"}
        if opposite.get(u2_gender) != u1_gender:
            return False
    
    if u2_pref == "other" and u1_gender != "other":
        return False
    
    return True