"""
Admin handlers.

Handles admin commands for moderation, monetization control, and statistics.
"""

import logging
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from database.mongodb import get_db
from config.settings import settings

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    """
    Check if user is admin.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        True if user is admin
    """
    return user_id == settings.ADMIN_CHAT_ID


@router.message(Command("ban"))
async def cmd_ban(message: Message) -> None:
    """
    Ban a user from the bot.
    
    Usage: /ban <user_id>
    
    Args:
        message: Incoming message
    """
    if not is_admin(message.from_user.id):
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Usage: /ban <user_id>")
        return
    
    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid user ID")
        return
    
    db = get_db()
    result = await db.users.update_one(
        {"tg_id": target_id},
        {"$set": {"is_banned": True}}
    )
    
    if result.modified_count > 0:
        await message.answer(f"✅ User {target_id} has been banned.")
        
        # Notify user
        try:
            await message.bot.send_message(
                chat_id=target_id,
                text="🚫 <b>You have been banned</b>\n\nYou can no longer use this bot."
            )
        except:
            pass
        
        logger.info(f"Admin {message.from_user.id} banned user {target_id}")
    else:
        await message.answer("❌ User not found or already banned.")


@router.message(Command("unban"))
async def cmd_unban(message: Message) -> None:
    """
    Unban a user.
    
    Usage: /unban <user_id>
    
    Args:
        message: Incoming message
    """
    if not is_admin(message.from_user.id):
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Usage: /unban <user_id>")
        return
    
    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid user ID")
        return
    
    db = get_db()
    result = await db.users.update_one(
        {"tg_id": target_id},
        {"$set": {"is_banned": False}}
    )
    
    if result.modified_count > 0:
        await message.answer(f"✅ User {target_id} has been unbanned.")
        
        # Notify user
        try:
            await message.bot.send_message(
                chat_id=target_id,
                text="✅ <b>You have been unbanned</b>\n\nYou can now use the bot again. Use /start"
            )
        except:
            pass
        
        logger.info(f"Admin {message.from_user.id} unbanned user {target_id}")
    else:
        await message.answer("❌ User not found.")


@router.message(Command("warn"))
async def cmd_warn(message: Message) -> None:
    """
    Warn a user.
    
    Usage: /warn <user_id> <reason>
    
    Args:
        message: Incoming message
    """
    if not is_admin(message.from_user.id):
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("❌ Usage: /warn <user_id> <reason>")
        return
    
    try:
        target_id = int(parts[1])
        reason = parts[2]
    except (ValueError, IndexError):
        await message.answer("❌ Invalid format")
        return
    
    db = get_db()
    settings_doc = await db.settings.find_one({"_id": "global_settings"})
    warn_threshold = settings_doc.get("warn_threshold", 3)
    
    result = await db.users.find_one_and_update(
        {"tg_id": target_id},
        {"$inc": {"warnings": 1}},
        return_document=True
    )
    
    if result:
        warnings = result.get("warnings", 0)
        
        # Auto-ban if threshold reached
        if warnings >= warn_threshold:
            await db.users.update_one(
                {"tg_id": target_id},
                {"$set": {"is_banned": True}}
            )
            
            await message.answer(
                f"⚠️ User {target_id} warned (Total: {warnings})\n"
                f"🚫 Auto-banned for reaching {warn_threshold} warnings!"
            )
            
            try:
                await message.bot.send_message(
                    chat_id=target_id,
                    text=(
                        f"🚫 <b>Auto-Banned</b>\n\n"
                        f"You have been automatically banned for receiving {warn_threshold} warnings.\n\n"
                        f"Last warning reason: {reason}"
                    )
                )
            except:
                pass
        else:
            await message.answer(f"⚠️ User {target_id} warned. Total warnings: {warnings}/{warn_threshold}")
            
            try:
                await message.bot.send_message(
                    chat_id=target_id,
                    text=(
                        f"⚠️ <b>Warning Issued</b>\n\n"
                        f"Reason: {reason}\n\n"
                        f"Total warnings: {warnings}/{warn_threshold}\n"
                        f"You will be auto-banned at {warn_threshold} warnings."
                    )
                )
            except:
                pass
        
        logger.info(f"Admin {message.from_user.id} warned user {target_id}: {reason}")
    else:
        await message.answer("❌ User not found.")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message) -> None:
    """
    Broadcast message to all users.
    
    Usage: /broadcast <message>
    
    Args:
        message: Incoming message
    """
    if not is_admin(message.from_user.id):
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Usage: /broadcast <message>")
        return
    
    broadcast_text = parts[1]
    
    db = get_db()
    users = await db.users.find({"is_banned": False}).to_list(length=None)
    
    success = 0
    failed = 0
    
    status_msg = await message.answer(f"📡 Broadcasting to {len(users)} users...")
    
    for user in users:
        try:
            await message.bot.send_message(
                chat_id=user["tg_id"],
                text=f"📢 <b>Announcement</b>\n\n{broadcast_text}"
            )
            success += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Failed to broadcast to {user['tg_id']}: {e}")
    
    await status_msg.edit_text(
        f"✅ <b>Broadcast Complete</b>\n\n"
        f"✅ Sent: {success}\n"
        f"❌ Failed: {failed}\n"
        f"📊 Total: {len(users)}"
    )
    
    logger.info(f"Admin {message.from_user.id} broadcast message to {success} users")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """
    Show bot statistics.
    
    Args:
        message: Incoming message
    """
    if not is_admin(message.from_user.id):
        return
    
    db = get_db()
    
    # Count users
    total_users = await db.users.count_documents({})
    banned_users = await db.users.count_documents({"is_banned": True})
    active_users = await db.users.count_documents({
        "last_active": {"$gte": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)}
    })
    
    # Count sessions
    active_sessions = await db.sessions.count_documents({"status": "active"})
    total_sessions = await db.sessions.count_documents({})
    
    # Count reports
    pending_reports = await db.reports.count_documents({"status": "pending"})
    total_reports = await db.reports.count_documents({})
    
    # Monetization stats
    monetize_completed = await db.users.count_documents({
        "monetize.next_due_at": {"$gte": datetime.now(timezone.utc)}
    })
    monetize_required = await db.users.count_documents({
        "monetize.next_due_at": {"$lt": datetime.now(timezone.utc)}
    })
    
    stats_text = (
        f"📊 <b>Bot Statistics</b>\n\n"
        f"👥 <b>Users:</b>\n"
        f"• Total: {total_users}\n"
        f"• Active Today: {active_users}\n"
        f"• Banned: {banned_users}\n\n"
        f"💬 <b>Sessions:</b>\n"
        f"• Active Now: {active_sessions}\n"
        f"• Total: {total_sessions}\n\n"
        f"🚨 <b>Reports:</b>\n"
        f"• Pending: {pending_reports}\n"
        f"• Total: {total_reports}\n\n"
        f"💰 <b>Monetization:</b>\n"
        f"• ✅ Completed: {monetize_completed}\n"
        f"• ⏰ Required: {monetize_required}\n\n"
        f"⏰ Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    
    await message.answer(stats_text)


@router.message(Command("monetize_on"))
async def cmd_monetize_on(message: Message) -> None:
    """Enable global monetization."""
    if not is_admin(message.from_user.id):
        return
    
    db = get_db()
    await db.settings.update_one(
        {"_id": "global_settings"},
        {"$set": {"monetize_enabled": True}}
    )
    
    await message.answer("✅ Global monetization <b>ENABLED</b>")
    logger.info(f"Admin {message.from_user.id} enabled global monetization")


@router.message(Command("monetize_off"))
async def cmd_monetize_off(message: Message) -> None:
    """Disable global monetization."""
    if not is_admin(message.from_user.id):
        return
    
    db = get_db()
    await db.settings.update_one(
        {"_id": "global_settings"},
        {"$set": {"monetize_enabled": False}}
    )
    
    await message.answer("✅ Global monetization <b>DISABLED</b>")
    logger.info(f"Admin {message.from_user.id} disabled global monetization")


@router.message(Command("monetize_user_on"))
async def cmd_monetize_user_on(message: Message) -> None:
    """
    Enable monetization for specific user.
    
    Usage: /monetize_user_on <user_id>
    """
    if not is_admin(message.from_user.id):
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Usage: /monetize_user_on <user_id>")
        return
    
    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid user ID")
        return
    
    db = get_db()
    result = await db.users.update_one(
        {"tg_id": target_id},
        {"$set": {"monetize.enabled": True}}
    )
    
    if result.modified_count > 0:
        await message.answer(f"✅ Monetization enabled for user {target_id}")
    else:
        await message.answer("❌ User not found.")


@router.message(Command("monetize_user_off"))
async def cmd_monetize_user_off(message: Message) -> None:
    """
    Disable monetization for specific user.
    
    Usage: /monetize_user_off <user_id>
    """
    if not is_admin(message.from_user.id):
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Usage: /monetize_user_off <user_id>")
        return
    
    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid user ID")
        return
    
    db = get_db()
    result = await db.users.update_one(
        {"tg_id": target_id},
        {"$set": {"monetize.enabled": False}}
    )
    
    if result.modified_count > 0:
        await message.answer(f"✅ Monetization disabled for user {target_id}")
    else:
        await message.answer("❌ User not found.")


@router.message(Command("monetize_stats"))
async def cmd_monetize_stats(message: Message) -> None:
    """Show detailed monetization statistics."""
    if not is_admin(message.from_user.id):
        return
    
    db = get_db()
    
    # Global settings
    settings_doc = await db.settings.find_one({"_id": "global_settings"})
    global_enabled = settings_doc.get("monetize_enabled", False)
    
    # User stats
    total_users = await db.users.count_documents({})
    enabled_users = await db.users.count_documents({"monetize.enabled": True})
    completed = await db.users.count_documents({
        "monetize.next_due_at": {"$gte": datetime.now(timezone.utc)}
    })
    required = await db.users.count_documents({
        "$or": [
            {"monetize.next_due_at": {"$lt": datetime.now(timezone.utc)}},
            {"monetize.next_due_at": None}
        ]
    })
    
    # Token stats
    pending_tokens = await db.monetize_tokens.count_documents({"status": "pending"})
    completed_tokens = await db.monetize_tokens.count_documents({"status": "completed"})
    expired_tokens = await db.monetize_tokens.count_documents({"status": "expired"})
    
    stats_text = (
        f"💰 <b>Monetization Statistics</b>\n\n"
        f"🌐 <b>Global Status:</b> {'✅ Enabled' if global_enabled else '❌ Disabled'}\n\n"
        f"👥 <b>Users:</b>\n"
        f"• Total: {total_users}\n"
        f"• Monetization Enabled: {enabled_users}\n"
        f"• ✅ Completed: {completed}\n"
        f"• ⏰ Required: {required}\n\n"
        f"🎫 <b>Tokens:</b>\n"
        f"• ⏳ Pending: {pending_tokens}\n"
        f"• ✅ Completed: {completed_tokens}\n"
        f"• ❌ Expired: {expired_tokens}\n\n"
        f"📈 <b>Completion Rate:</b> {(completed/total_users*100):.1f}%\n\n"
        f"⏰ Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    
    await message.answer(stats_text)