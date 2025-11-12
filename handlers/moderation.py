"""
Moderation handlers.

Handles user reports, blocking, and moderation actions.
"""

import logging
import uuid
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from database.mongodb import get_db
from utils.session_manager import get_active_session, get_partner_tg_id, end_session
from config.settings import settings

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "chat_report")
async def handle_report_partner(callback: CallbackQuery) -> None:
    """
    Handle report button press.
    
    Args:
        callback: Callback query from report button
    """
    db = get_db()
    session = await get_active_session(callback.from_user.id)
    
    if not session:
        await callback.answer("❌ No active chat", show_alert=True)
        return
    
    # Get reporter and reported users
    reporter = await db.users.find_one({"tg_id": callback.from_user.id})
    partner_tg_id = await get_partner_tg_id(session, callback.from_user.id)
    reported = await db.users.find_one({"tg_id": partner_tg_id})
    
    if not reporter or not reported:
        await callback.answer("❌ Error creating report", show_alert=True)
        return
    
    # Create report
    report_id = f"report_{uuid.uuid4().hex[:12]}"
    report_data = {
        "report_id": report_id,
        "reporter_anon_id": reporter["anon_id"],
        "reported_anon_id": reported["anon_id"],
        "session_id": session["session_id"],
        "reason": "User reported via chat button",
        "created_at": datetime.now(timezone.utc),
        "status": "pending",
        "admin_notes": None
    }
    
    await db.reports.insert_one(report_data)
    
    # Send report to admin
    admin_text = (
        f"🚨 <b>New Report</b>\n\n"
        f"📋 Report ID: <code>{report_id}</code>\n"
        f"👤 Reporter: <code>{reporter['anon_id']}</code>\n"
        f"🎯 Reported: <code>{reported['anon_id']}</code>\n"
        f"💬 Session: <code>{session['session_id']}</code>\n"
        f"⏰ Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
        f"Use /ban {reported['tg_id']} to ban this user"
    )
    
    try:
        await callback.message.bot.send_message(
            chat_id=settings.ADMIN_CHAT_ID,
            text=admin_text
        )
    except Exception as e:
        logger.error(f"Failed to send report to admin: {e}")
    
    await callback.message.answer(
        "✅ <b>Report Submitted</b>\n\n"
        "Your report has been sent to the moderators.\n"
        "Thank you for helping keep the community safe!"
    )
    
    await callback.answer("✅ Report submitted")
    logger.info(f"Report created: {report_id}")


@router.message(Command("report"))
async def cmd_report(message: Message) -> None:
    """
    Handle /report command with reason.
    
    Args:
        message: Incoming message
    """
    db = get_db()
    session = await get_active_session(message.from_user.id)
    
    if not session:
        await message.answer("❌ You need to be in an active chat to report someone.")
        return
    
    # Extract reason
    parts = message.text.split(maxsplit=1)
    reason = parts[1] if len(parts) > 1 else "No reason provided"
    
    # Get reporter and reported users
    reporter = await db.users.find_one({"tg_id": message.from_user.id})
    partner_tg_id = await get_partner_tg_id(session, message.from_user.id)
    reported = await db.users.find_one({"tg_id": partner_tg_id})
    
    if not reporter or not reported:
        await message.answer("❌ Error creating report.")
        return
    
    # Create report
    report_id = f"report_{uuid.uuid4().hex[:12]}"
    report_data = {
        "report_id": report_id,
        "reporter_anon_id": reporter["anon_id"],
        "reported_anon_id": reported["anon_id"],
        "session_id": session["session_id"],
        "reason": reason,
        "created_at": datetime.now(timezone.utc),
        "status": "pending",
        "admin_notes": None
    }
    
    await db.reports.insert_one(report_data)
    
    # Send to admin
    admin_text = (
        f"🚨 <b>New Report</b>\n\n"
        f"📋 Report ID: <code>{report_id}</code>\n"
        f"👤 Reporter: <code>{reporter['anon_id']}</code>\n"
        f"🎯 Reported: <code>{reported['anon_id']}</code>\n"
        f"💬 Session: <code>{session['session_id']}</code>\n"
        f"📝 Reason: {reason}\n"
        f"⏰ Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
        f"Use /ban {reported['tg_id']} to ban this user"
    )
    
    try:
        await message.bot.send_message(
            chat_id=settings.ADMIN_CHAT_ID,
            text=admin_text
        )
    except Exception as e:
        logger.error(f"Failed to send report to admin: {e}")
    
    await message.answer(
        "✅ <b>Report Submitted</b>\n\n"
        "Your report has been sent to the moderators.\n"
        "Thank you for helping keep the community safe!"
    )
    
    logger.info(f"Report created: {report_id} - {reason}")


@router.message(Command("block"))
async def cmd_block(message: Message) -> None:
    """
    Handle /block command to block current partner.
    
    Args:
        message: Incoming message
    """
    db = get_db()
    session = await get_active_session(message.from_user.id)
    
    if not session:
        await message.answer("❌ You need to be in an active chat to block someone.")
        return
    
    user = await db.users.find_one({"tg_id": message.from_user.id})
    partner_tg_id = await get_partner_tg_id(session, message.from_user.id)
    partner = await db.users.find_one({"tg_id": partner_tg_id})
    
    if not partner:
        await message.answer("❌ Error finding partner.")
        return
    
    # Add to blocked list
    await db.users.update_one(
        {"tg_id": message.from_user.id},
        {"$addToSet": {"blocked_users": partner["anon_id"]}}
    )
    
    # End session
    await end_session(session["session_id"])
    
    await message.answer(
        "🚫 <b>Partner Blocked</b>\n\n"
        "You won't be matched with this user again.\n\n"
        "Use /newchat to find a new partner."
    )
    
    await message.bot.send_message(
        chat_id=partner_tg_id,
        text=(
            "👋 <b>Chat Ended</b>\n\n"
            "Your partner has left the chat.\n\n"
            "Use /newchat to find a new partner!"
        )
    )
    
    logger.info(f"User {user['anon_id']} blocked {partner['anon_id']}")


@router.message(Command("unblock"))
async def cmd_unblock(message: Message) -> None:
    """
    Handle /unblock command to view and manage blocked users.
    
    Args:
        message: Incoming message
    """
    db = get_db()
    user = await db.users.find_one({"tg_id": message.from_user.id})
    
    if not user:
        await message.answer("❌ User not found.")
        return
    
    blocked = user.get("blocked_users", [])
    
    if not blocked:
        await message.answer("✅ You haven't blocked anyone.")
        return
    
    blocked_list = "\n".join([f"• <code>{anon_id}</code>" for anon_id in blocked])
    
    await message.answer(
        f"🚫 <b>Blocked Users ({len(blocked)}):</b>\n\n"
        f"{blocked_list}\n\n"
        f"To unblock someone, contact admin."
    )