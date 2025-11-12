"""
Session management utilities.

Handles chat session creation, retrieval, and cleanup.
"""

import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from database.mongodb import get_db

logger = logging.getLogger(__name__)


async def get_active_session(tg_id: int) -> Optional[Dict[str, Any]]:
    """
    Get active chat session for a user.
    
    Args:
        tg_id: Telegram user ID
        
    Returns:
        Session document or None if no active session
    """
    db = get_db()
    
    session = await db.sessions.find_one({
        "$or": [
            {"user1.tg_id": tg_id, "status": "active"},
            {"user2.tg_id": tg_id, "status": "active"}
        ]
    })
    
    return session


async def create_session(user1: Dict[str, Any], user2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new chat session between two users.
    
    Args:
        user1: First user document
        user2: Second user document
        
    Returns:
        Created session document
    """
    db = get_db()
    
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    
    session_data = {
        "session_id": session_id,
        "user1": {
            "anon_id": user1["anon_id"],
            "tg_id": user1["tg_id"]
        },
        "user2": {
            "anon_id": user2["anon_id"],
            "tg_id": user2["tg_id"]
        },
        "started_at": datetime.now(timezone.utc),
        "status": "active",
        "messages_count": 0
    }
    
    await db.sessions.insert_one(session_data)
    
    logger.info(f"Session created: {session_id}")
    return session_data


async def end_session(session_id: str) -> bool:
    """
    End a chat session.
    
    Args:
        session_id: Session ID to end
        
    Returns:
        True if session was ended successfully
    """
    db = get_db()
    
    result = await db.sessions.update_one(
        {"session_id": session_id},
        {"$set": {"status": "ended"}}
    )
    
    if result.modified_count > 0:
        logger.info(f"Session ended: {session_id}")
        return True
    
    return False


async def get_partner_tg_id(session: Dict[str, Any], user_tg_id: int) -> Optional[int]:
    """
    Get partner's Telegram ID from session.
    
    Args:
        session: Session document
        user_tg_id: Requesting user's Telegram ID
        
    Returns:
        Partner's Telegram ID or None
    """
    if session["user1"]["tg_id"] == user_tg_id:
        return session["user2"]["tg_id"]
    elif session["user2"]["tg_id"] == user_tg_id:
        return session["user1"]["tg_id"]
    
    return None