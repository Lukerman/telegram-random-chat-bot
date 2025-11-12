"""
Authentication and user state middleware.

Ensures users are registered and updates last active timestamp.
"""

import logging
from typing import Callable, Dict, Any, Awaitable
from datetime import datetime, timezone

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from database.mongodb import get_db

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Middleware to handle user authentication and state."""
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """
        Process incoming update and update user state.
        
        Args:
            handler: Next handler in chain
            event: Incoming event (Message or CallbackQuery)
            data: Additional data
            
        Returns:
            Handler result
        """
        user = event.from_user
        if not user:
            return await handler(event, data)
        
        db = get_db()
        
        # Update last active for existing users
        try:
            await db.users.update_one(
                {"tg_id": user.id},
                {"$set": {"last_active": datetime.now(timezone.utc)}}
            )
        except Exception as e:
            logger.error(f"Error updating user last_active: {e}")
        
        return await handler(event, data)