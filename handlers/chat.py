"""
Chat handlers.

Handles chat matching, message forwarding, and session management.
"""

import logging
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database.mongodb import get_db
from utils.matching import find_match
from utils.session_manager import (
    get_active_session,
    create_session,
    end_session,
    get_partner_tg_id
)
from handlers.monetization import ensure_monetized

logger = logging.getLogger(__name__)
router = Router()


def get_chat_keyboard() -> InlineKeyboardMarkup:
    """
    Get inline keyboard for active chat.
    
    Returns:
        InlineKeyboardMarkup with chat control buttons
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔁 Skip", callback_data="chat_skip"),
            InlineKeyboardButton(text="❌ End", callback_data="chat_end")
        ],
        [
            InlineKeyboardButton(text="🚫 Report", callback_data="chat_report"),
            InlineKeyboardButton(text="🚫 Block", callback_data="chat_block")
        ]
    ])


@router.message(Command("newchat"))
async def cmd_newchat(message: Message) -> None:
    """
    Start searching for a chat partner.
    
    Args:
        message: Incoming message
    """
    db = get_db()
    user = await db.users.find_one({"tg_id": message.from_user.id})
    
    if not user:
        await message.answer("❌ Please use /start to register first.")
        return
    
    if user.get("is_banned"):
        await message.answer("🚫 You are banned from using this bot.")
        return
    
    # Check monetization
    if not await ensure_monetized(user["tg_id"], user["anon_id"], message):
        return
    
    # Check if already in a chat
    active_session = await get_active_session(user["tg_id"])
    if active_session:
        await message.answer(
            "⚠️ You're already in a chat!\n\n"
            "Use /end to end your current chat first.",
            reply_markup=get_chat_keyboard()
        )
        return
    
    # Update last active
    await db.users.update_one(
        {"tg_id": user["tg_id"]},
        {"$set": {"last_active": datetime.now(timezone.utc)}}
    )
    
    # Find a match
    searching_msg = await message.answer("🔍 <b>Searching for a partner...</b>")
    
    partner = await find_match(user)
    
    if not partner:
        await searching_msg.edit_text(
            "😔 <b>No partners available right now.</b>\n\n"
            "Please try again in a few moments.\n\n"
            "Tip: Try changing your preferences in /settings to find more matches!"
        )
        return
    
    # Create session
    session = await create_session(user, partner)
    
    # Notify both users
    await searching_msg.edit_text(
        "✅ <b>Partner Found!</b>\n\n"
        "🎭 Chat started anonymously.\n"
        "💬 Send a message to begin!\n\n"
        "Use the buttons below to control the chat.",
        reply_markup=get_chat_keyboard()
    )
    
    partner_keyboard = get_chat_keyboard()
    await message.bot.send_message(
        chat_id=partner["tg_id"],
        text=(
            "✅ <b>Partner Found!</b>\n\n"
            "🎭 Someone wants to chat with you!\n"
            "💬 Send a message to begin!\n\n"
            "Use the buttons below to control the chat."
        ),
        reply_markup=partner_keyboard
    )
    
    logger.info(f"Chat session created: {session['session_id']}")


@router.message(Command("end"))
async def cmd_end(message: Message) -> None:
    """
    End current chat session.
    
    Args:
        message: Incoming message
    """
    await handle_end_chat(message.from_user.id, message)


async def handle_end_chat(tg_id: int, message: Message) -> None:
    """
    Handle ending a chat session.
    
    Args:
        tg_id: Telegram user ID
        message: Message object
    """
    session = await get_active_session(tg_id)
    
    if not session:
        await message.answer("❌ You're not in an active chat.")
        return
    
    partner_tg_id = await get_partner_tg_id(session, tg_id)
    
    await end_session(session["session_id"])
    
    await message.answer(
        "👋 <b>Chat Ended</b>\n\n"
        "The chat session has been ended.\n\n"
        "Use /newchat to find a new partner!"
    )
    
    if partner_tg_id:
        await message.bot.send_message(
            chat_id=partner_tg_id,
            text=(
                "👋 <b>Chat Ended</b>\n\n"
                "Your partner has left the chat.\n\n"
                "Use /newchat to find a new partner!"
            )
        )
    
    logger.info(f"Chat session ended: {session['session_id']}")


@router.callback_query(F.data == "chat_end")
async def callback_end_chat(callback: CallbackQuery) -> None:
    """Handle end chat button."""
    await handle_end_chat(callback.from_user.id, callback.message)
    await callback.answer("Chat ended")


@router.callback_query(F.data == "chat_skip")
async def callback_skip_chat(callback: CallbackQuery) -> None:
    """Handle skip button - ends current chat and starts new search."""
    await handle_end_chat(callback.from_user.id, callback.message)
    await callback.answer("Finding new partner...")
    
    # Automatically start new search
    await cmd_newchat(callback.message)


@router.callback_query(F.data == "chat_block")
async def callback_block_partner(callback: CallbackQuery) -> None:
    """Handle block button."""
    db = get_db()
    session = await get_active_session(callback.from_user.id)
    
    if not session:
        await callback.answer("❌ No active chat", show_alert=True)
        return
    
    user = await db.users.find_one({"tg_id": callback.from_user.id})
    partner_tg_id = await get_partner_tg_id(session, callback.from_user.id)
    partner = await db.users.find_one({"tg_id": partner_tg_id})
    
    if not partner:
        await callback.answer("❌ Error finding partner", show_alert=True)
        return
    
    # Add partner to blocked list
    await db.users.update_one(
        {"tg_id": callback.from_user.id},
        {"$addToSet": {"blocked_users": partner["anon_id"]}}
    )
    
    # End the chat
    await end_session(session["session_id"])
    
    await callback.message.answer(
        "🚫 <b>Partner Blocked</b>\n\n"
        "You won't be matched with this user again.\n\n"
        "Use /newchat to find a new partner."
    )
    
    await callback.message.bot.send_message(
        chat_id=partner_tg_id,
        text=(
            "👋 <b>Chat Ended</b>\n\n"
            "Your partner has left the chat.\n\n"
            "Use /newchat to find a new partner!"
        )
    )
    
    await callback.answer("✅ Blocked")
    logger.info(f"User {user['anon_id']} blocked {partner['anon_id']}")


@router.message(F.text)
async def handle_message(message: Message) -> None:
    """
    Forward messages between chat partners.
    
    Args:
        message: Incoming message
    """
    # Skip commands
    if message.text.startswith('/'):
        return
    
    db = get_db()
    session = await get_active_session(message.from_user.id)
    
    if not session:
        return  # Not in a chat, ignore
    
    partner_tg_id = await get_partner_tg_id(session, message.from_user.id)
    
    if not partner_tg_id:
        await message.answer("❌ Error: Partner not found. Chat ended.")
        await end_session(session["session_id"])
        return
    
    # Forward message to partner
    try:
        await message.bot.send_message(
            chat_id=partner_tg_id,
            text=f"💬 <b>Partner:</b>\n\n{message.text}"
        )
        
        # Increment message count
        await db.sessions.update_one(
            {"session_id": session["session_id"]},
            {"$inc": {"messages_count": 1}}
        )
        
    except Exception as e:
        logger.error(f"Error forwarding message: {e}")
        await message.answer("❌ Failed to send message. Chat may have ended.")


@router.callback_query(F.data == "chat_report")
async def callback_report(callback: CallbackQuery) -> None:
    """Handle report button - redirect to moderation handler."""
    from handlers.moderation import handle_report_partner
    await handle_report_partner(callback)