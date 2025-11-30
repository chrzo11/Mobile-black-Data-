from pyrogram import Client, filters, enums, errors
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import API_ID, API_HASH, BOT_TOKEN, GROUP_ID, REQUIRED_CHANNEL_ID, REQUIRED_CHANNEL_LINK, GROUP_LINK, OWNER_ID
from database import db
from api_client import get_mobile_info, get_aadhar_info
from ui_components import *
import re
import logging
import asyncio
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Client("info_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Regex for mobile number (10-12 digits)
MOBILE_REGEX = r"^\d{10,12}$"

async def check_subscription(user_id):
    """Check if user is subscribed to required channel"""
    try:
        member = await app.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
        return member.status in [enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
    except errors.UserNotParticipant:
        return False
    except Exception as e:
        logger.error(f"Error checking subscription: {e}")
        return False

# ===== START COMMAND =====

@app.on_message(filters.command("start") & (filters.private | filters.chat(GROUP_ID)))
async def start_command(client, message: Message):
    """Enhanced start command with premium welcome"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"
    
    # Add user to database if new
    is_new = await db.add_user(user_id, user_name)
    
    if message.chat.type == enums.ChatType.PRIVATE:
        # Private chat - send rich welcome
        settings = await db.get_all_settings()
        welcome_bonus = settings.get('welcome_bonus', 3)
        welcome_bonus_enabled = settings.get('welcome_bonus_enabled', True)
        welcome_text = create_welcome_message(user_name, is_new=is_new, welcome_bonus=welcome_bonus, welcome_bonus_enabled=welcome_bonus_enabled)
        keyboard = get_welcome_keyboard(GROUP_LINK, REQUIRED_CHANNEL_LINK)
        
        await message.reply_text(welcome_text, reply_markup=keyboard)
    else:
        # Group chat - fascinating response
        welcome_text = create_group_welcome_message(user_name)
        keyboard = get_group_welcome_keyboard(REQUIRED_CHANNEL_LINK)
        
        await message.reply_text(welcome_text, reply_markup=keyboard)

# ===== NEW MEMBER HANDLER =====

@app.on_message(filters.chat(GROUP_ID) & filters.new_chat_members)
async def on_new_member(client, message: Message):
    """Handle new members with credit rewards"""
    for new_member in message.new_chat_members:
        adder = message.from_user
        if adder and adder.id != new_member.id and not new_member.is_bot:
            new_member_name = new_member.first_name or "User"
            if await db.check_referral(new_member.id, adder.id, new_member_name):
                await message.reply_text(
                    f"{EMOJIS['fire']} Thank you {adder.mention} for adding {new_member.mention}!\n"
                    f"{EMOJIS['credit']} You received **+1 search credit!**"
                )

# ===== SEARCH REQUEST HANDLER =====

@app.on_message(filters.chat(GROUP_ID) & filters.text & filters.regex(MOBILE_REGEX))
async def on_search_request(client, message: Message):
    """Enhanced search handler with animations and beautiful results"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"
    term = message.text.strip()
    
    # Ensure user exists in database
    await db.add_user(user_id, user_name)
    
    # 1. Check Channel Subscription
    if not await check_subscription(user_id):
        await message.reply_text(
            create_error_message('not_subscribed'),
            reply_markup=get_subscription_keyboard(REQUIRED_CHANNEL_LINK)
        )
        return
    
    # 2. Check if user is banned
    if await db.is_user_banned(user_id):
        await message.reply_text(
            f"{EMOJIS['error']} **Account Banned**\n\n"
            f"Your account has been banned and you cannot perform searches.\n\n"
            f"{EMOJIS['info']} Contact the admin if you believe this is an error."
        )
        return

    # 3. Check Credits
    user = await db.get_user(user_id)
    if not user or user['credits'] <= 0:
        settings = await db.get_all_settings()
        daily_bonus_enabled = settings.get('daily_bonus_enabled', True)
        
        await message.reply_text(
            create_error_message('no_credits'),
            reply_markup=get_no_credits_keyboard(GROUP_LINK, daily_bonus_enabled=daily_bonus_enabled)
        )
        return

    # 3. Animated Loading
    loading_messages = create_loading_messages()
    status_msg = await message.reply_text(loading_messages[0])
    
    # Cycle through loading messages
    for idx, loading_text in enumerate(loading_messages[1:], 1):
        await asyncio.sleep(0.5)
        try:
            await status_msg.edit_text(loading_text)
        except:
            pass

    # 4. Perform Search
    search_type = "id_number" if len(term) == 12 else "mobile"
    
    if len(term) == 12:
        result = get_aadhar_info(term)
    else:
        result = get_mobile_info(term)

    # 5. Process Result
    if "error" in result or not result or result.get("message") == "No matching records found":
        # Search failed - refund credit and show error
        await status_msg.edit_text(
            create_error_message('not_found'),
            reply_markup=get_result_keyboard(GROUP_LINK)
        )
        # Record failed search
        await db.add_search_history(user_id, term, search_type, success=False)
    else:
        # Search successful - deduct credit
        await db.deduct_credit(user_id)
        
        # Create beautiful result card
        result_text = create_search_result_card(result, search_type)
        
        # Get updated credits
        updated_user = await db.get_user(user_id)
        credits_left = updated_user.get('credits', 0)
        
        result_text += f"\n\n{create_credit_display(credits_left, with_bar=False)}"
        
        await status_msg.edit_text(
            result_text,
            reply_markup=get_result_keyboard(GROUP_LINK)
        )
        
        # Record successful search
        await db.add_search_history(user_id, term, search_type, success=True, result_data=result)

# ===== PROFILE COMMAND =====

@app.on_message(filters.command("profile"))
async def profile_command(client, message: Message):
    """Show user profile with stats"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"
    
    # Ensure user exists
    await db.add_user(user_id, user_name)
    
    user_data = await db.get_user(user_id)
    stats = await db.get_user_stats(user_id)
    rank = await db.get_user_rank(user_id)
    
    # Add name to user data
    user_data['name'] = user_name
    
    profile_text = create_profile_card(user_data, rank=rank, stats=stats)
    
    await message.reply_text(
        profile_text,
        reply_markup=get_profile_keyboard()
    )

# ===== LEADERBOARD COMMAND =====

@app.on_message(filters.command("leaderboard"))
async def leaderboard_command(client, message: Message):
    """Show top users leaderboard"""
    user_id = message.from_user.id
    
    # Get top 10 users
    top_users = await db.get_leaderboard(limit=10)
    
    # Get user's rank
    user_rank = await db.get_user_rank(user_id)
    
    leaderboard_text = create_leaderboard(top_users, user_rank=user_rank)
    
    await message.reply_text(leaderboard_text)

# ===== HISTORY COMMAND =====

@app.on_message(filters.command("history"))
async def history_command(client, message: Message):
    """Show user's search history"""
    user_id = message.from_user.id
    
    # Get first page of history
    history = await db.get_user_history(user_id, limit=5, skip=0)
    total_count = await db.get_history_count(user_id)
    total_pages = math.ceil(total_count / 5) if total_count > 0 else 1
    
    history_text = create_history_card(history, page=1, total_pages=total_pages)
    
    await message.reply_text(
        history_text,
        reply_markup=get_history_keyboard(1, total_pages)
    )

# ===== DAILY BONUS COMMAND =====

@app.on_message(filters.command("daily"))
async def daily_bonus_command(client, message: Message):
    """Claim daily bonus"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"
    
    # Ensure user exists
    await db.add_user(user_id, user_name)
    
    result = await db.claim_daily_bonus(user_id)
    
    if result['success']:
        bonus_text = f"""
{EMOJIS['bonus']} **Daily Bonus Claimed!**

{EMOJIS['credit']} You received **+{result['amount']} credit(s)**!
{EMOJIS['fire']} Current streak: **{result['streak']} day(s)**

{EMOJIS['info']} Come back tomorrow for more!
"""
    else:
        if result.get('already_claimed'):
            bonus_text = f"""
{EMOJIS['warning']} **Already Claimed!**

{result['message']}

{EMOJIS['rocket']} Keep your streak alive!
"""
        else:
            bonus_text = f"""
{EMOJIS['error']} **Daily Bonus Unavailable**

{result['message']}
"""
    
    await message.reply_text(bonus_text)

# ===== STATS COMMAND =====

@app.on_message(filters.command("stats"))
async def stats_command(client, message: Message):
    """Show detailed user statistics"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"
    
    # Ensure user exists
    await db.add_user(user_id, user_name)
    
    user_data = await db.get_user(user_id)
    stats = await db.get_user_stats(user_id)
    
    total_searches = stats.get('total_searches', 0)
    successful = stats.get('successful_searches', 0)
    failed = stats.get('failed_searches', 0)
    credits_earned = stats.get('credits_earned', 0)
    credits_spent = stats.get('credits_spent', 0)
    current_credits = user_data.get('credits', 0)
    
    success_rate = (successful / total_searches * 100) if total_searches > 0 else 0
    
    stats_text = f"""
{EMOJIS['chart']} **Your Statistics**

**{EMOJIS['search']} Search Stats**
Total Searches: **{total_searches}**
└─ Successful: **{successful}** {EMOJIS['success']}
└─ Failed: **{failed}** {EMOJIS['error']}
"""
    
    if total_searches > 0:
        success_bar = create_progress_bar(successful, total_searches, 12)
        stats_text += f"\nSuccess Rate: {success_bar}\n"
    
    stats_text += f"""

**{EMOJIS['credit']} Credit Stats**
Current Balance: **{current_credits}**
Total Earned: **{credits_earned}**
Total Spent: **{credits_spent}**
Net Gain: **{credits_earned - credits_spent}**
"""
    
    await message.reply_text(stats_text)

# ===== HELP COMMAND =====

@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    """Show help menu"""
    settings = await db.get_all_settings()
    welcome_bonus = settings.get('welcome_bonus', 3)
    welcome_bonus_enabled = settings.get('welcome_bonus_enabled', True)
    daily_bonus_enabled = settings.get('daily_bonus_enabled', True)
    
    help_text = create_help_menu(welcome_bonus=welcome_bonus, welcome_bonus_enabled=welcome_bonus_enabled, daily_bonus_enabled=daily_bonus_enabled)
    await message.reply_text(help_text)

# ===== CALLBACK QUERY HANDLERS =====

@app.on_callback_query(filters.regex("^check_sub$"))
async def on_check_sub(client, callback_query: CallbackQuery):
    """Handle subscription check callback"""
    user_id = callback_query.from_user.id
    if await check_subscription(user_id):
        await callback_query.message.edit_text(
            f"{EMOJIS['success']} Thank you for joining!\n\n"
            f"{EMOJIS['rocket']} You can now search in the group."
        )
    else:
        await callback_query.answer("You have not joined the channel yet!", show_alert=True)

@app.on_callback_query(filters.regex("^daily_bonus$"))
async def on_daily_bonus_callback(client, callback_query: CallbackQuery):
    """Handle daily bonus callback"""
    user_id = callback_query.from_user.id
    user_name = callback_query.from_user.first_name or "User"
    
    await db.add_user(user_id, user_name)
    
    # Check if daily bonus is enabled
    settings = await db.get_all_settings()
    if not settings.get('daily_bonus_enabled', True):
        await callback_query.answer("Daily bonus is currently disabled!", show_alert=True)
        return

    result = await db.claim_daily_bonus(user_id)
    
    if result['success']:
        await callback_query.answer(
            f"✅ +{result['amount']} credit! Streak: {result['streak']} days",
            show_alert=True
        )
    else:
        await callback_query.answer(result['message'], show_alert=True)

@app.on_callback_query(filters.regex("^leaderboard$"))
async def on_leaderboard_callback(client, callback_query: CallbackQuery):
    """Handle leaderboard callback"""
    user_id = callback_query.from_user.id
    
    top_users = await db.get_leaderboard(limit=10)
    user_rank = await db.get_user_rank(user_id)
    
    leaderboard_text = create_leaderboard(top_users, user_rank=user_rank)
    
    await callback_query.message.edit_text(leaderboard_text)

@app.on_callback_query(filters.regex(r"history_(\d+)"))
async def on_history_page_callback(client, callback_query: CallbackQuery):
    """Handle history pagination"""
    user_id = callback_query.from_user.id
    page = int(callback_query.data.split('_')[1])
    
    # Get history for page
    skip = (page - 1) * 5
    history = await db.get_user_history(user_id, limit=5, skip=skip)
    total_count = await db.get_history_count(user_id)
    total_pages = math.ceil(total_count / 5) if total_count > 0 else 1
    
    history_text = create_history_card(history, page=page, total_pages=total_pages)
    
    await callback_query.message.edit_text(
        history_text,
        reply_markup=get_history_keyboard(page, total_pages)
    )

@app.on_callback_query(filters.regex("^close$"))
async def on_close_callback(client, callback_query: CallbackQuery):
    """Handle close button"""
    await callback_query.message.delete()

@app.on_callback_query(filters.regex("^search_help_alert$"))
async def on_search_help_alert(client, callback_query: CallbackQuery):
    """Handle search help alert"""
    await callback_query.answer(
        f"ℹ️ Just type the number in the chat!\n\n"
        f"📱 Mobile: 10 digits\n"
        f"🆔 Aadhar: 12 digits",
        show_alert=True
    )

# ===== ADMIN PANEL =====

@app.on_message(filters.command("admin") & filters.private)
async def admin_panel(client, message: Message):
    """Enhanced admin panel with multiple pages"""
    if message.from_user.id != OWNER_ID:
        return
    
    # Get analytics
    analytics = await db.get_admin_analytics()
    
    overview_text = create_admin_overview(analytics)
    
    await message.reply_text(
        overview_text,
        reply_markup=get_admin_main_keyboard()
    )

@app.on_callback_query(filters.regex("^admin_overview$"))
async def on_admin_overview(client, callback_query: CallbackQuery):
    """Handle admin overview callback"""
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Unauthorized!", show_alert=True)
        return
    
    analytics = await db.get_admin_analytics()
    overview_text = create_admin_overview(analytics)
    
    try:
        await callback_query.message.edit_text(
            overview_text,
            reply_markup=get_admin_main_keyboard()
        )
    except errors.MessageNotModified:
        # Message is already showing this content, just answer the callback
        await callback_query.answer()

@app.on_callback_query(filters.regex("^admin_users$"))
async def on_admin_users(client, callback_query: CallbackQuery):
    """Handle admin users page with full management"""
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Unauthorized!", show_alert=True)
        return
    
    # Get first page of users
    users = await db.get_all_users(skip=0, limit=10)
    total_users = await db.get_total_users()
    total_pages = math.ceil(total_users / 10) if total_users > 0 else 1
    
    users_text = create_user_list(users, page=1, total_pages=total_pages)
    
    try:
        await callback_query.message.edit_text(
            users_text,
            reply_markup=get_user_list_keyboard(1, total_pages)
        )
    except errors.MessageNotModified:
        await callback_query.answer()

@app.on_callback_query(filters.regex(r"users_page_(\d+)"))
async def on_users_page(client, callback_query: CallbackQuery):
    """Handle user list pagination"""
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Unauthorized!", show_alert=True)
        return
    
    page = int(callback_query.data.split('_')[-1])
    skip = (page - 1) * 10
    
    users = await db.get_all_users(skip=skip, limit=10)
    total_users = await db.get_total_users()
    total_pages = math.ceil(total_users / 10) if total_users > 0 else 1
    
    users_text = create_user_list(users, page=page, total_pages=total_pages)
    
    try:
        await callback_query.message.edit_text(
            users_text,
            reply_markup=get_user_list_keyboard(page, total_pages)
        )
    except errors.MessageNotModified:
        await callback_query.answer()

@app.on_callback_query(filters.regex("^user_search$"))
async def on_user_search(client, callback_query: CallbackQuery):
    """Handle user search with interactive input"""
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Unauthorized!", show_alert=True)
        return
    
    await callback_query.answer()
    
    # Ask for user ID or name
    try:
        response = await client.ask(
            chat_id=callback_query.message.chat.id,
            text=f"{EMOJIS['search']} **Search User**\n\n"
                 f"Enter user ID or name to search.\n\n"
                 f"{EMOJIS['info']} Type /cancel to abort.",
            timeout=60
        )
        
        # Check if user wants to cancel
        if response.text and response.text.strip().lower() == '/cancel':
            await response.reply_text(f"{EMOJIS['cross']} Search cancelled.")
            return
        
        query = response.text.strip()
        
        if not query:
            await response.reply_text(f"{EMOJIS['error']} Invalid input. Search cancelled.")
            return
        
        # Search for users
        users = await db.search_users(query, limit=10)
        
        if not users:
            await response.reply_text(
                f"{EMOJIS['info']} No users found matching: `{query}`"
            )
            return
        
        # Display search results
        search_text = create_user_list(users, page=1, total_pages=1, search_query=query)
        
        # If only one user found, offer to view details
        if len(users) == 1:
            user_id = users[0].get('user_id')
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{EMOJIS['user']} View Details", callback_data=f"view_user_{user_id}")],
                [InlineKeyboardButton(f"{EMOJIS['arrow_left']} Back to Users", callback_data="admin_users")]
            ])
        else:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{EMOJIS['arrow_left']} Back to Users", callback_data="admin_users")]
            ])
        
        await response.reply_text(search_text, reply_markup=keyboard)
        
    except asyncio.TimeoutError:
        await callback_query.message.reply_text(f"{EMOJIS['clock']} Search timed out.")
    except Exception as e:
        logger.error(f"Error in user search: {e}")
        await callback_query.message.reply_text(f"{EMOJIS['error']} An error occurred during search.")

# View user details from callback
@app.on_callback_query(filters.regex(r"view_user_(\d+)"))
async def on_view_user_callback(client, callback_query: CallbackQuery):
    """View user details from callback"""
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Unauthorized!", show_alert=True)
        return
    
    user_id = int(callback_query.data.split('_')[2])
    
    # Get user data
    user_data = await db.get_user_detailed(user_id)
    
    if not user_data:
        await callback_query.answer("User not found!", show_alert=True)
        return
    
    user_text = create_user_detail(user_data)
    is_banned = user_data.get('banned', False)
    
    try:
        await callback_query.message.edit_text(
            user_text,
            reply_markup=get_user_detail_keyboard(user_id, is_banned)
        )
    except errors.MessageNotModified:
        await callback_query.answer()

# User detail view (triggered by /viewuser command or inline button)
@app.on_message(filters.command("viewuser") & filters.private)
async def view_user_command(client, message: Message):
    """View detailed user information (owner only)"""
    if message.from_user.id != OWNER_ID:
        return
    
    # Extract user ID from command
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply_text(f"{EMOJIS['warning']} Usage: /viewuser <user_id>")
        return
    
    try:
        user_id = int(parts[1])
    except ValueError:
        await message.reply_text(f"{EMOJIS['error']} Invalid user ID!")
        return
    
    # Get user data
    user_data = await db.get_user_detailed(user_id)
    
    if not user_data:
        await message.reply_text(f"{EMOJIS['error']} User not found!")
        return
    
    user_text = create_user_detail(user_data)
    is_banned = user_data.get('banned', False)
    
    await message.reply_text(
        user_text,
        reply_markup=get_user_detail_keyboard(user_id, is_banned)
    )

# Ban user
@app.on_callback_query(filters.regex(r"^ban_(\d+)$"))
async def on_ban_user(client, callback_query: CallbackQuery):
    """Ban a user"""
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Unauthorized!", show_alert=True)
        return
    
    user_id = int(callback_query.data.split('_')[1])
    
    await db.ban_user(user_id)
    await callback_query.answer(f"User {user_id} banned!", show_alert=True)
    
    # Refresh user detail
    user_data = await db.get_user_detailed(user_id)
    user_text = create_user_detail(user_data)
    is_banned = user_data.get('banned', False)
    
    try:
        await callback_query.message.edit_text(
            user_text,
            reply_markup=get_user_detail_keyboard(user_id, is_banned)
        )
    except errors.MessageNotModified:
        pass

# Unban user
@app.on_callback_query(filters.regex(r"^unban_(\d+)$"))
async def on_unban_user(client, callback_query: CallbackQuery):
    """Unban a user"""
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Unauthorized!", show_alert=True)
        return
    
    user_id = int(callback_query.data.split('_')[1])
    
    await db.unban_user(user_id)
    await callback_query.answer(f"User {user_id} unbanned!", show_alert=True)
    
    # Refresh user detail
    user_data = await db.get_user_detailed(user_id)
    user_text = create_user_detail(user_data)
    is_banned = user_data.get('banned', False)
    
    try:
        await callback_query.message.edit_text(
            user_text,
            reply_markup=get_user_detail_keyboard(user_id, is_banned)
        )
    except errors.MessageNotModified:
        pass

# Add credits
@app.on_callback_query(filters.regex(r"add_credits_(\d+)"))
async def on_add_credits(client, callback_query: CallbackQuery):
    """Add credits to user with manual input"""
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Unauthorized!", show_alert=True)
        return
    
    user_id = int(callback_query.data.split('_')[2])
    
    await callback_query.answer()
    
    try:
        response = await client.ask(
            chat_id=callback_query.message.chat.id,
            text=f"{EMOJIS['credit']} **Add Credits**\n\n"
                 f"Enter amount to add for User `{user_id}`.\n\n"
                 f"{EMOJIS['info']} Type /cancel to abort.",
            timeout=60
        )
        
        if response.text and response.text.strip().lower() == '/cancel':
            await response.reply_text(f"{EMOJIS['cross']} Operation cancelled.")
            return
            
        if not response.text.isdigit():
            await response.reply_text(f"{EMOJIS['error']} Invalid amount. Please enter a number.")
            return
            
        amount = int(response.text)
        
        # Add credits
        await db.add_credits_to_user(user_id, amount)
        await response.reply_text(f"{EMOJIS['success']} Added **{amount}** credits to user `{user_id}`!")
        
        # Refresh user detail if possible (might need to resend message if original is too far up)
        # For now, just let the user navigate back or refresh manually
        
    except asyncio.TimeoutError:
        await callback_query.message.reply_text(f"{EMOJIS['clock']} Operation timed out.")
    except Exception as e:
        logger.error(f"Error adding credits: {e}")
        await callback_query.message.reply_text(f"{EMOJIS['error']} An error occurred.")

# Remove credits
@app.on_callback_query(filters.regex(r"remove_credits_(\d+)"))
async def on_remove_credits(client, callback_query: CallbackQuery):
    """Remove credits from user with manual input"""
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Unauthorized!", show_alert=True)
        return
    
    user_id = int(callback_query.data.split('_')[2])
    
    await callback_query.answer()
    
    try:
        response = await client.ask(
            chat_id=callback_query.message.chat.id,
            text=f"{EMOJIS['warning']} **Remove Credits**\n\n"
                 f"Enter amount to remove from User `{user_id}`.\n\n"
                 f"{EMOJIS['info']} Type /cancel to abort.",
            timeout=60
        )
        
        if response.text and response.text.strip().lower() == '/cancel':
            await response.reply_text(f"{EMOJIS['cross']} Operation cancelled.")
            return
            
        if not response.text.isdigit():
            await response.reply_text(f"{EMOJIS['error']} Invalid amount. Please enter a number.")
            return
            
        amount = int(response.text)
        
        # Remove credits
        await db.remove_credits_from_user(user_id, amount)
        await response.reply_text(f"{EMOJIS['success']} Removed **{amount}** credits from user `{user_id}`!")
        
    except asyncio.TimeoutError:
        await callback_query.message.reply_text(f"{EMOJIS['clock']} Operation timed out.")
    except Exception as e:
        logger.error(f"Error removing credits: {e}")
        await callback_query.message.reply_text(f"{EMOJIS['error']} An error occurred.")

# Check if user is banned before allowing searches
async def check_user_status(user_id):
    """Check if user is banned"""
    return not await db.is_user_banned(user_id)

@app.on_callback_query(filters.regex("^admin_analytics$"))
async def on_admin_analytics(client, callback_query: CallbackQuery):
    """Handle admin analytics page"""
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Unauthorized!", show_alert=True)
        return
    
    # Get analytics
    basic_stats = await db.get_admin_analytics()
    advanced_stats = await db.get_advanced_analytics()
    
    analytics_text = create_admin_analytics_view(basic_stats, advanced_stats)
    
    try:
        await callback_query.message.edit_text(
            analytics_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{EMOJIS['arrow_left']} Back", callback_data="admin_overview")]
            ])
        )
    except errors.MessageNotModified:
        await callback_query.answer()

@app.on_callback_query(filters.regex("^admin_broadcast$"))
async def on_admin_broadcast(client, callback_query: CallbackQuery):
    """Handle admin broadcast"""
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Unauthorized!", show_alert=True)
        return
    
    await callback_query.answer()
    
    try:
        # Ask for broadcast message
        response = await client.ask(
            chat_id=callback_query.message.chat.id,
            text=f"{EMOJIS['broadcast']} **Broadcast Message**\n\n"
                 f"Send the message you want to broadcast to all users.\n"
                 f"You can send text, photos, or any other media.\n\n"
                 f"{EMOJIS['info']} Type /cancel to abort.",
            timeout=300
        )
        
        if response.text and response.text.strip().lower() == '/cancel':
            await response.reply_text(f"{EMOJIS['cross']} Broadcast cancelled.")
            return
        
        # Confirm broadcast
        confirm_msg = await response.reply_text(
            f"{EMOJIS['warning']} **Confirm Broadcast**\n\n"
            f"Are you sure you want to send this message to ALL users?\n"
            f"This process might take some time.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"{EMOJIS['check']} Yes, Send", callback_data="confirm_broadcast"),
                    InlineKeyboardButton(f"{EMOJIS['cross']} Cancel", callback_data="cancel_broadcast")
                ]
            ])
        )
        
        # Store message to broadcast in a temporary way (e.g., global variable or just pass it)
        # For simplicity, we'll use a simple global dict or similar mechanism if needed, 
        # but since we can't easily pass data to the next callback without a state machine or DB,
        # we'll implement a simple wait_for_click approach here or just do it directly if confirmed.
        
        # Actually, let's just do it directly here to avoid complex state management
        # We'll use a specific callback handler for the confirmation that we'll register dynamically or just use a unique ID
        
        # Better approach: Use client.ask again for confirmation? No, buttons are better.
        # Let's use a simple trick: We'll store the message ID in the callback data if it fits, 
        # or we'll just ask for text confirmation "yes".
        
        # Let's stick to buttons but we need to handle the callback. 
        # Since we can't easily add a new handler dynamically, let's use a text confirmation for now to keep it robust in one function.
        
        await confirm_msg.delete()
        
        confirm_response = await client.ask(
            chat_id=callback_query.message.chat.id,
            text=f"{EMOJIS['warning']} **Confirm Broadcast**\n\n"
                 f"Type `yes` to confirm sending this message to all users.\n"
                 f"Type anything else to cancel.",
            timeout=60
        )
        
        if not confirm_response.text or confirm_response.text.lower() != 'yes':
            await confirm_response.reply_text(f"{EMOJIS['cross']} Broadcast cancelled.")
            return
            
        # Start broadcast
        status_msg = await confirm_response.reply_text(f"{EMOJIS['rocket']} Starting broadcast...")
        
        users = await db.get_all_users(limit=10000) # Get all users (limit high enough)
        total = len(users)
        sent = 0
        failed = 0
        
        for user in users:
            try:
                user_id = user['user_id']
                await response.copy(chat_id=user_id)
                sent += 1
            except errors.FloodWait as e:
                await asyncio.sleep(e.value)
                try:
                    await response.copy(chat_id=user_id)
                    sent += 1
                except:
                    failed += 1
            except:
                failed += 1
            
            # Update status every 10 users
            if (sent + failed) % 10 == 0:
                try:
                    await status_msg.edit_text(
                        f"{EMOJIS['broadcast']} **Broadcasting...**\n\n"
                        f"Progress: {sent + failed}/{total}\n"
                        f"Sent: {sent} {EMOJIS['success']}\n"
                        f"Failed: {failed} {EMOJIS['error']}"
                    )
                except:
                    pass
                    
        await status_msg.edit_text(
            f"{EMOJIS['success']} **Broadcast Complete!**\n\n"
            f"Total Users: {total}\n"
            f"Successfully Sent: {sent}\n"
            f"Failed: {failed}"
        )
        
    except asyncio.TimeoutError:
        await callback_query.message.reply_text(f"{EMOJIS['clock']} Broadcast timed out.")
    except Exception as e:
        logger.error(f"Error in broadcast: {e}")
        await callback_query.message.reply_text(f"{EMOJIS['error']} An error occurred during broadcast.")

@app.on_callback_query(filters.regex("^admin_settings$"))
async def on_admin_settings(client, callback_query: CallbackQuery):
    """Handle admin settings page"""
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Unauthorized!", show_alert=True)
        return
    
    settings = await db.get_all_settings()
    settings_text = create_admin_settings_panel(settings)
    
    await callback_query.message.edit_text(
        settings_text,
        reply_markup=get_admin_settings_keyboard(settings)
    )

@app.on_callback_query(filters.regex("^toggle_daily_bonus$"))
async def on_toggle_daily_bonus(client, callback_query: CallbackQuery):
    """Toggle daily bonus on/off"""
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Unauthorized!", show_alert=True)
        return
    
    settings = await db.get_all_settings()
    current = settings.get('daily_bonus_enabled', True)
    new_value = not current
    
    await db.update_setting('daily_bonus_enabled', new_value)
    
    status = "enabled" if new_value else "disabled"
    await callback_query.answer(f"Daily bonus {status}!", show_alert=True)
    
    # Refresh settings page
    settings = await db.get_all_settings()
    settings_text = create_admin_settings_panel(settings)
    await callback_query.message.edit_text(
        settings_text,
        reply_markup=get_admin_settings_keyboard(settings)
    )

@app.on_callback_query(filters.regex("^toggle_welcome_bonus$"))
async def on_toggle_welcome_bonus(client, callback_query: CallbackQuery):
    """Toggle welcome bonus on/off"""
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Unauthorized!", show_alert=True)
        return
    
    settings = await db.get_all_settings()
    current = settings.get('welcome_bonus_enabled', True)
    new_value = not current
    
    await db.update_setting('welcome_bonus_enabled', new_value)
    
    status = "enabled" if new_value else "disabled"
    await callback_query.answer(f"Welcome bonus {status}!", show_alert=True)
    
    # Refresh settings page
    settings = await db.get_all_settings()
    settings_text = create_admin_settings_panel(settings)
    await callback_query.message.edit_text(
        settings_text,
        reply_markup=get_admin_settings_keyboard(settings)
    )


@app.on_callback_query(filters.regex("^set_bonus_amount$"))
async def on_set_bonus_amount(client, callback_query: CallbackQuery):
    """Set daily bonus amount with interactive input"""
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Unauthorized!", show_alert=True)
        return
    
    await callback_query.answer()
    
    settings = await db.get_all_settings()
    current_amount = settings.get('daily_bonus_amount', 1)
    
    try:
        response = await client.ask(
            chat_id=callback_query.message.chat.id,
            text=f"{EMOJIS['bonus']} **Set Daily Bonus Amount**\n\n"
                 f"Current amount: **{current_amount}**\n\n"
                 f"Enter new amount (1-50):\n"
                 f"{EMOJIS['info']} Type /cancel to abort.",
            timeout=60
        )
        
        if response.text and response.text.strip().lower() == '/cancel':
            await response.reply_text(f"{EMOJIS['cross']} Operation cancelled.")
            return
            
        try:
            amount = int(response.text.strip())
            if 1 <= amount <= 50:
                await db.update_setting('daily_bonus_amount', amount)
                await response.reply_text(f"{EMOJIS['success']} Daily bonus set to **{amount}** credits!")
                
                # Refresh settings page
                settings = await db.get_all_settings()
                settings_text = create_admin_settings_panel(settings)
                try:
                    await callback_query.message.edit_text(
                        settings_text,
                        reply_markup=get_admin_settings_keyboard(settings)
                    )
                except:
                    pass
            else:
                await response.reply_text(f"{EMOJIS['error']} Please enter a number between 1 and 50.")
        except ValueError:
            await response.reply_text(f"{EMOJIS['error']} Invalid number.")
            
    except asyncio.TimeoutError:
        await callback_query.message.reply_text(f"{EMOJIS['clock']} Operation timed out.")

@app.on_callback_query(filters.regex("^set_welcome_bonus$"))
async def on_set_welcome_bonus(client, callback_query: CallbackQuery):
    """Set welcome bonus amount with interactive input"""
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Unauthorized!", show_alert=True)
        return
    
    await callback_query.answer()
    
    settings = await db.get_all_settings()
    current_bonus = settings.get('welcome_bonus', 3)
    
    try:
        response = await client.ask(
            chat_id=callback_query.message.chat.id,
            text=f"{EMOJIS['gem']} **Set Welcome Bonus**\n\n"
                 f"Current bonus: **{current_bonus}**\n\n"
                 f"Enter new bonus amount (1-50):\n"
                 f"{EMOJIS['info']} Type /cancel to abort.",
            timeout=60
        )
        
        if response.text and response.text.strip().lower() == '/cancel':
            await response.reply_text(f"{EMOJIS['cross']} Operation cancelled.")
            return
            
        try:
            amount = int(response.text.strip())
            if 1 <= amount <= 50:
                await db.update_setting('welcome_bonus', amount)
                await response.reply_text(f"{EMOJIS['success']} Welcome bonus set to **{amount}** credits!")
                
                # Refresh settings page
                settings = await db.get_all_settings()
                settings_text = create_admin_settings_panel(settings)
                try:
                    await callback_query.message.edit_text(
                        settings_text,
                        reply_markup=get_admin_settings_keyboard(settings)
                    )
                except:
                    pass
            else:
                await response.reply_text(f"{EMOJIS['error']} Please enter a number between 1 and 50.")
        except ValueError:
            await response.reply_text(f"{EMOJIS['error']} Invalid number.")
            
    except asyncio.TimeoutError:
        await callback_query.message.reply_text(f"{EMOJIS['clock']} Operation timed out.")
    



if __name__ == "__main__":
    print(f"{EMOJIS['rocket']} Bot Starting...")
    print(f"{EMOJIS['sparkles']} Premium UI Loaded!")
    app.run()
