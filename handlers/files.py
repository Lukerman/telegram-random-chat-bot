"""
File and media handlers.

Handles photo, video, document, and other media forwarding.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message

from database.mongodb import get_db
from utils.session_manager import get_active_session, get_partner_tg_id, end_session

logger = logging.getLogger(__name__)
router = Router()


async def forward_media(message: Message, media_type: str) -> None:
    """
    Forward media to chat partner.
    
    Args:
        message: Incoming message with media
        media_type: Type of media (photo, video, document, etc.)
    """
    db = get_db()
    session = await get_active_session(message.from_user.id)
    
    if not session:
        await message.answer("❌ You're not in an active chat. Use /newchat to start!")
        return
    
    # Get partner
    partner_tg_id = await get_partner_tg_id(session, message.from_user.id)
    if not partner_tg_id:
        await message.answer("❌ Partner not found. Chat ended.")
        await end_session(session["session_id"])
        return
    
    # Check partner's file consent
    partner = await db.users.find_one({"tg_id": partner_tg_id})
    if not partner.get("consent_files", False):
        await message.answer(
            "🚫 <b>File Blocked</b>\n\n"
            "Your partner has disabled file receiving.\n"
            "You can only send text messages."
        )
        return
    
    # Forward the media
    try:
        caption = f"📎 <b>Partner sent a {media_type}:</b>"
        if message.caption:
            caption += f"\n\n{message.caption}"
        
        if media_type == "photo":
            await message.bot.send_photo(
                chat_id=partner_tg_id,
                photo=message.photo[-1].file_id,
                caption=caption
            )
        elif media_type == "video":
            await message.bot.send_video(
                chat_id=partner_tg_id,
                video=message.video.file_id,
                caption=caption
            )
        elif media_type == "document":
            await message.bot.send_document(
                chat_id=partner_tg_id,
                document=message.document.file_id,
                caption=caption
            )
        elif media_type == "audio":
            await message.bot.send_audio(
                chat_id=partner_tg_id,
                audio=message.audio.file_id,
                caption=caption
            )
        elif media_type == "voice":
            await message.bot.send_voice(
                chat_id=partner_tg_id,
                voice=message.voice.file_id,
                caption=caption
            )
        elif media_type == "video_note":
            await message.bot.send_video_note(
                chat_id=partner_tg_id,
                video_note=message.video_note.file_id
            )
        elif media_type == "sticker":
            await message.bot.send_sticker(
                chat_id=partner_tg_id,
                sticker=message.sticker.file_id
            )
        
        await message.answer("✅ File sent!")
        
        # Increment message count
        await db.sessions.update_one(
            {"session_id": session["session_id"]},
            {"$inc": {"messages_count": 1}}
        )
        
        logger.info(f"Media forwarded: {media_type} in session {session['session_id']}")
        
    except Exception as e:
        logger.error(f"Error forwarding media: {e}")
        await message.answer("❌ Failed to send file.")


@router.message(F.photo)
async def handle_photo(message: Message) -> None:
    """Handle photo messages."""
    await forward_media(message, "photo")


@router.message(F.video)
async def handle_video(message: Message) -> None:
    """Handle video messages."""
    await forward_media(message, "video")


@router.message(F.document)
async def handle_document(message: Message) -> None:
    """Handle document messages."""
    await forward_media(message, "document")


@router.message(F.audio)
async def handle_audio(message: Message) -> None:
    """Handle audio messages."""
    await forward_media(message, "audio")


@router.message(F.voice)
async def handle_voice(message: Message) -> None:
    """Handle voice messages."""
    await forward_media(message, "voice")


@router.message(F.video_note)
async def handle_video_note(message: Message) -> None:
    """Handle video note messages."""
    await forward_media(message, "video_note")


@router.message(F.sticker)
async def handle_sticker(message: Message) -> None:
    """Handle sticker messages."""
    await forward_media(message, "sticker")