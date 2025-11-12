"""
Monetization handlers.

Handles monetization challenges, token verification, and deep-link activation.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from database.mongodb import get_db
from config.settings import settings

logger = logging.getLogger(__name__)
router = Router()


async def monetization_required(user: dict, global_settings: dict) -> bool:
    """
    Check if user needs to complete monetization challenge.
    
    Args:
        user: User document from database
        global_settings: Global settings document
        
    Returns:
        True if monetization is required, False otherwise
    """
    # Check if monetization is enabled
    enabled = global_settings.get("monetize_enabled", False)
    
    # User-specific override
    if user.get("monetize", {}).get("enabled") is not None:
        enabled = user["monetize"]["enabled"]
    
    if not enabled:
        return False
    
    # Check if next_due_at has passed
    next_due = user.get("monetize", {}).get("next_due_at")
    if not next_due:
        return True  # Never completed before
    
    return datetime.now(timezone.utc) >= next_due


async def send_monetization_challenge(
    tg_id: int,
    anon_id: str,
    message: Message
) -> bool:
    """
    Send monetization challenge to user.
    
    Args:
        tg_id: Telegram user ID
        anon_id: Anonymous user ID
        message: Message object to reply to
        
    Returns:
        False (indicating feature access is blocked)
    """
    db = get_db()
    settings_doc = await db.settings.find_one({"_id": "global_settings"})
    
    now = datetime.now(timezone.utc)
    ttl_minutes = settings_doc.get("monetize_token_ttl_minutes", 30)
    
    # Generate token
    token = str(uuid.uuid4())
    short_url = settings_doc.get("short_url", settings.SHORT_URL)
    
    # Store token in database
    token_data = {
        "token": token,
        "anon_id": anon_id,
        "tg_id": tg_id,
        "created_at": now,
        "expires_at": now + timedelta(minutes=ttl_minutes),
        "status": "pending",
        "short_url": short_url
    }
    
    await db.monetize_tokens.insert_one(token_data)
    
    # Create deep link
    deep_link = f"https://t.me/{settings.BOT_USERNAME}?start=monetize_{token}"
    
    # Create inline keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Open Sponsor Link", url=short_url)],
        [InlineKeyboardButton(text="✅ I've Completed", url=deep_link)]
    ])
    
    text = (
        "⚡ <b>Monetization Required</b>\n\n"
        "To continue using the bot, please complete a quick sponsor visit.\n\n"
        "<b>How it works:</b>\n"
        "1️⃣ Tap <b>Open Sponsor Link</b> below\n"
        "2️⃣ Wait a few seconds on the page\n"
        "3️⃣ Come back and tap <b>I've Completed</b>\n\n"
        f"⏱️ This unlocks the bot for {settings.MONETIZE_INTERVAL_HOURS} hours.\n"
        f"⏰ Token expires in {ttl_minutes} minutes."
    )
    
    await message.answer(text, reply_markup=keyboard)
    
    logger.info(f"Monetization challenge sent to user {tg_id} ({anon_id})")
    return False


@router.message(CommandStart(deep_link=True, magic=F.args.startswith("monetize_")))
async def handle_monetize_deeplink(message: Message) -> None:
    """
    Handle deep link monetization confirmation.
    
    Args:
        message: Incoming message with deep link payload
    """
    # Extract token from deep link
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Invalid confirmation link.")
        return
    
    payload = args[1]
    if not payload.startswith("monetize_"):
        return
    
    token = payload.replace("monetize_", "")
    
    await handle_monetize_confirm(token, message)


async def handle_monetize_confirm(token: str, message: Message) -> None:
    """
    Validate monetization token and unlock features.
    
    Args:
        token: UUID token from deep link
        message: Message object
    """
    db = get_db()
    
    # Find token in database
    token_doc = await db.monetize_tokens.find_one({"token": token})
    
    if not token_doc:
        await message.answer(
            "❌ <b>Invalid Token</b>\n\n"
            "This confirmation link is invalid or has already been used.\n\n"
            "Use /newchat to request a new link."
        )
        return
    
    if token_doc["status"] != "pending":
        await message.answer(
            "❌ <b>Token Already Used</b>\n\n"
            "This confirmation link has already been used.\n\n"
            "Use /newchat if you need to complete monetization again."
        )
        return
    
    # Verify token belongs to this user
    if token_doc["tg_id"] != message.from_user.id:
        await message.answer(
            "❌ <b>Wrong User</b>\n\n"
            "This confirmation link doesn't belong to you."
        )
        return
    
    now = datetime.now(timezone.utc)
    
    # Check if token expired
    if token_doc["expires_at"] < now:
        await db.monetize_tokens.update_one(
            {"token": token},
            {"$set": {"status": "expired"}}
        )
        await message.answer(
            "⏰ <b>Token Expired</b>\n\n"
            "This confirmation link has expired.\n\n"
            "Use /newchat to get a new link."
        )
        return
    
    # Get global settings for minimum wait time
    settings_doc = await db.settings.find_one({"_id": "global_settings"})
    min_wait_seconds = settings_doc.get("monetize_min_wait_seconds", 10)
    
    # Check minimum wait time (anti-spam)
    time_elapsed = (now - token_doc["created_at"]).total_seconds()
    if time_elapsed < min_wait_seconds:
        remaining = int(min_wait_seconds - time_elapsed)
        await message.answer(
            f"⏳ <b>Please Wait</b>\n\n"
            f"Wait {remaining} more seconds before confirming.\n\n"
            f"This ensures you actually visited the sponsor page."
        )
        return
    
    # All checks passed - mark as completed
    interval_hours = settings_doc.get("monetize_interval_hours", 12)
    next_due = now + timedelta(hours=interval_hours)
    
    # Update token status
    await db.monetize_tokens.update_one(
        {"token": token},
        {"$set": {"status": "completed"}}
    )
    
    # Update user's monetization info
    await db.users.update_one(
        {"tg_id": message.from_user.id},
        {
            "$set": {
                "monetize.last_completed_at": now,
                "monetize.next_due_at": next_due,
                "monetize.fail_count": 0,
                "last_active": now
            }
        }
    )
    
    await message.answer(
        f"✅ <b>Monetization Completed!</b>\n\n"
        f"Thank you for supporting the bot!\n\n"
        f"🎉 Features unlocked for <b>{interval_hours} hours</b>.\n\n"
        f"You can now use /newchat to find a partner!"
    )
    
    logger.info(f"Monetization completed for user {message.from_user.id} (token: {token})")


async def ensure_monetized(tg_id: int, anon_id: str, message: Message) -> bool:
    """
    Ensure user has completed monetization or send challenge.
    
    Args:
        tg_id: Telegram user ID
        anon_id: Anonymous user ID
        message: Message object
        
    Returns:
        True if monetization is complete, False otherwise
    """
    db = get_db()
    
    user = await db.users.find_one({"tg_id": tg_id})
    settings_doc = await db.settings.find_one({"_id": "global_settings"})
    
    if not await monetization_required(user, settings_doc):
        return True
    
    # Send challenge
    await send_monetization_challenge(tg_id, anon_id, message)
    return False