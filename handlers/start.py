"""
Start and onboarding handlers.

Handles /start command, user registration, and preference setup.
"""

import logging
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.mongodb import get_db
from utils.anonymizer import generate_anon_id

logger = logging.getLogger(__name__)
router = Router()


class OnboardingStates(StatesGroup):
    """States for user onboarding flow."""
    waiting_for_gender = State()
    waiting_for_preference = State()
    waiting_for_file_consent = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """
    Handle /start command and begin onboarding.
    
    Args:
        message: Incoming message
        state: FSM context
    """
    db = get_db()
    user = await db.users.find_one({"tg_id": message.from_user.id})
    
    if user:
        # User already registered
        await message.answer(
            f"👋 Welcome back, <b>Anonymous User</b>!\n\n"
            f"🎭 Your Anonymous ID: <code>{user['anon_id']}</code>\n\n"
            f"Use /newchat to find a random chat partner.\n"
            f"Use /profile to view your settings.\n"
            f"Use /help for more commands.",
        )
        return
    
    # New user - start onboarding
    await message.answer(
        "👋 <b>Welcome to Random Chat Bot!</b>\n\n"
        "Connect with random people anonymously and chat 1-on-1.\n\n"
        "🔒 <b>Privacy First:</b>\n"
        "• Your identity stays hidden\n"
        "• No usernames shared\n"
        "• Messages forwarded anonymously\n\n"
        "Let's set up your profile!\n\n"
        "<b>What's your gender?</b>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨 Male", callback_data="gender_male")],
        [InlineKeyboardButton(text="👩 Female", callback_data="gender_female")],
        [InlineKeyboardButton(text="🌈 Other", callback_data="gender_other")]
    ])
    
    await message.answer("Please select:", reply_markup=keyboard)
    await state.set_state(OnboardingStates.waiting_for_gender)


@router.callback_query(OnboardingStates.waiting_for_gender, F.data.startswith("gender_"))
async def process_gender(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Process gender selection.
    
    Args:
        callback: Callback query
        state: FSM context
    """
    gender = callback.data.split("_")[1]
    await state.update_data(gender=gender)
    
    await callback.message.edit_text(
        f"✅ Gender set to: <b>{gender.capitalize()}</b>\n\n"
        f"<b>Who would you like to chat with?</b>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌍 Anyone", callback_data="pref_any")],
        [InlineKeyboardButton(text="👥 Same Gender", callback_data="pref_same")],
        [InlineKeyboardButton(text="💑 Opposite Gender", callback_data="pref_opposite")],
        [InlineKeyboardButton(text="🌈 Other Gender", callback_data="pref_other")]
    ])
    
    await callback.message.answer("Choose your preference:", reply_markup=keyboard)
    await state.set_state(OnboardingStates.waiting_for_preference)
    await callback.answer()


@router.callback_query(OnboardingStates.waiting_for_preference, F.data.startswith("pref_"))
async def process_preference(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Process chat preference selection.
    
    Args:
        callback: Callback query
        state: FSM context
    """
    preference = callback.data.split("_")[1]
    await state.update_data(preference=preference)
    
    pref_names = {
        "any": "Anyone",
        "same": "Same Gender",
        "opposite": "Opposite Gender",
        "other": "Other Gender"
    }
    
    await callback.message.edit_text(
        f"✅ Preference set to: <b>{pref_names[preference]}</b>\n\n"
        f"<b>Do you want to receive photos and files from chat partners?</b>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yes, allow files", callback_data="files_yes")],
        [InlineKeyboardButton(text="❌ No, text only", callback_data="files_no")]
    ])
    
    await callback.message.answer("Choose your preference:", reply_markup=keyboard)
    await state.set_state(OnboardingStates.waiting_for_file_consent)
    await callback.answer()


@router.callback_query(OnboardingStates.waiting_for_file_consent, F.data.startswith("files_"))
async def process_file_consent(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Process file consent and complete registration.
    
    Args:
        callback: Callback query
        state: FSM context
    """
    consent = callback.data.split("_")[1] == "yes"
    data = await state.get_data()
    
    # Create user in database
    db = get_db()
    anon_id = generate_anon_id()
    
    user_data = {
        "tg_id": callback.from_user.id,
        "anon_id": anon_id,
        "username": callback.from_user.username,
        "first_name": callback.from_user.first_name,
        "gender": data["gender"],
        "preference": data["preference"],
        "consent_files": consent,
        "blocked_users": [],
        "warnings": 0,
        "is_banned": False,
        "created_at": datetime.now(timezone.utc),
        "last_active": datetime.now(timezone.utc),
        "monetize": {
            "enabled": True,
            "last_completed_at": None,
            "next_due_at": None,
            "fail_count": 0
        }
    }
    
    await db.users.insert_one(user_data)
    
    await callback.message.edit_text(
        f"🎉 <b>Registration Complete!</b>\n\n"
        f"🎭 Your Anonymous ID: <code>{anon_id}</code>\n\n"
        f"<b>Your Settings:</b>\n"
        f"• Gender: {data['gender'].capitalize()}\n"
        f"• Preference: {data['preference'].capitalize()}\n"
        f"• Files: {'Allowed' if consent else 'Blocked'}\n\n"
        f"Ready to chat? Use /newchat to find a partner!"
    )
    
    await state.clear()
    await callback.answer()
    
    logger.info(f"New user registered: {callback.from_user.id} ({anon_id})")


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    """
    Show user profile and settings.
    
    Args:
        message: Incoming message
    """
    db = get_db()
    user = await db.users.find_one({"tg_id": message.from_user.id})
    
    if not user:
        await message.answer("❌ You need to /start first to register.")
        return
    
    monetize_status = "✅ Active"
    if user.get("monetize", {}).get("next_due_at"):
        next_due = user["monetize"]["next_due_at"]
        if datetime.now(timezone.utc) >= next_due:
            monetize_status = "⏰ Required"
    
    await message.answer(
        f"👤 <b>Your Profile</b>\n\n"
        f"🎭 Anonymous ID: <code>{user['anon_id']}</code>\n"
        f"👤 Gender: {user.get('gender', 'Not set').capitalize()}\n"
        f"💑 Preference: {user.get('preference', 'any').capitalize()}\n"
        f"📎 Files: {'Allowed' if user.get('consent_files') else 'Blocked'}\n"
        f"💰 Monetization: {monetize_status}\n"
        f"⚠️ Warnings: {user.get('warnings', 0)}\n\n"
        f"Use /settings to update your preferences."
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    """
    Show settings menu.
    
    Args:
        message: Incoming message
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Change Gender", callback_data="setting_gender")],
        [InlineKeyboardButton(text="💑 Change Preference", callback_data="setting_preference")],
        [InlineKeyboardButton(text="📎 Toggle Files", callback_data="setting_files")],
        [InlineKeyboardButton(text="❌ Close", callback_data="setting_close")]
    ])
    
    await message.answer(
        "<b>⚙️ Settings</b>\n\n"
        "What would you like to change?",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "setting_gender")
async def setting_change_gender(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle gender change request."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨 Male", callback_data="update_gender_male")],
        [InlineKeyboardButton(text="👩 Female", callback_data="update_gender_female")],
        [InlineKeyboardButton(text="🌈 Other", callback_data="update_gender_other")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="setting_back")]
    ])
    
    await callback.message.edit_text(
        "<b>Select your gender:</b>",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("update_gender_"))
async def update_gender(callback: CallbackQuery) -> None:
    """Update user gender."""
    gender = callback.data.split("_")[2]
    db = get_db()
    
    await db.users.update_one(
        {"tg_id": callback.from_user.id},
        {"$set": {"gender": gender, "last_active": datetime.now(timezone.utc)}}
    )
    
    await callback.message.edit_text(
        f"✅ Gender updated to: <b>{gender.capitalize()}</b>\n\n"
        f"Use /settings to change more options."
    )
    await callback.answer("✅ Updated!")


@router.callback_query(F.data == "setting_preference")
async def setting_change_preference(callback: CallbackQuery) -> None:
    """Handle preference change request."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌍 Anyone", callback_data="update_pref_any")],
        [InlineKeyboardButton(text="👥 Same Gender", callback_data="update_pref_same")],
        [InlineKeyboardButton(text="💑 Opposite Gender", callback_data="update_pref_opposite")],
        [InlineKeyboardButton(text="🌈 Other Gender", callback_data="update_pref_other")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="setting_back")]
    ])
    
    await callback.message.edit_text(
        "<b>Who would you like to chat with?</b>",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("update_pref_"))
async def update_preference(callback: CallbackQuery) -> None:
    """Update user chat preference."""
    preference = callback.data.split("_")[2]
    db = get_db()
    
    await db.users.update_one(
        {"tg_id": callback.from_user.id},
        {"$set": {"preference": preference, "last_active": datetime.now(timezone.utc)}}
    )
    
    pref_names = {
        "any": "Anyone",
        "same": "Same Gender",
        "opposite": "Opposite Gender",
        "other": "Other Gender"
    }
    
    await callback.message.edit_text(
        f"✅ Preference updated to: <b>{pref_names[preference]}</b>\n\n"
        f"Use /settings to change more options."
    )
    await callback.answer("✅ Updated!")


@router.callback_query(F.data == "setting_files")
async def setting_toggle_files(callback: CallbackQuery) -> None:
    """Toggle file consent."""
    db = get_db()
    user = await db.users.find_one({"tg_id": callback.from_user.id})
    
    new_consent = not user.get("consent_files", False)
    
    await db.users.update_one(
        {"tg_id": callback.from_user.id},
        {"$set": {"consent_files": new_consent, "last_active": datetime.now(timezone.utc)}}
    )
    
    await callback.message.edit_text(
        f"✅ File consent updated to: <b>{'Allowed' if new_consent else 'Blocked'}</b>\n\n"
        f"Use /settings to change more options."
    )
    await callback.answer("✅ Updated!")


@router.callback_query(F.data == "setting_close")
async def setting_close(callback: CallbackQuery) -> None:
    """Close settings menu."""
    await callback.message.delete()
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """
    Show help message with available commands.
    
    Args:
        message: Incoming message
    """
    help_text = (
        "<b>🤖 Random Chat Bot - Help</b>\n\n"
        "<b>👤 User Commands:</b>\n"
        "/start - Start the bot and register\n"
        "/newchat - Find a random chat partner\n"
        "/end - End current chat session\n"
        "/profile - View your profile\n"
        "/settings - Update your preferences\n"
        "/help - Show this help message\n\n"
        "<b>💬 During Chat:</b>\n"
        "• Send any message to chat with partner\n"
        "• Use inline buttons to Skip, End, or Report\n"
        "• Block button to block current partner\n\n"
        "<b>🔒 Privacy:</b>\n"
        "• Your identity is completely anonymous\n"
        "• No personal info is shared\n"
        "• Messages are forwarded in real-time\n"
        "• No chat history is stored\n\n"
        "<b>💰 Monetization:</b>\n"
        "• Complete sponsor visit every 12 hours\n"
        "• Required to access chat features\n"
        "• Takes less than a minute\n\n"
        "<b>Need support?</b>\n"
        "Contact admin or use /report during chat."
    )
    
    await message.answer(help_text)