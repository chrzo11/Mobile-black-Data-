"""
Premium UI Components for Telegram Bot
Beautiful, rich message templates with emojis and visual elements
"""

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import math

# Emoji Sets
EMOJIS = {
    'welcome': '👋',
    'search': '🔍',
    'loading': '⏳',
    'success': '✅',
    'error': '❌',
    'credit': '💰',
    'bonus': '🎁',
    'trophy': '🏆',
    'star': '⭐',
    'fire': '🔥',
    'rocket': '🚀',
    'chart': '📊',
    'user': '👤',
    'crown': '👑',
    'medal_1': '🥇',
    'medal_2': '🥈',
    'medal_3': '🥉',
    'calendar': '📅',
    'history': '📜',
    'settings': '⚙️',
    'admin': '🔒',
    'broadcast': '📢',
    'analytics': '📈',
    'group': '👥',
    'channel': '📯',
    'check': '✓',
    'cross': '✗',
    'arrow_right': '→',
    'arrow_left': '←',
    'dot': '•',
    'sparkles': '✨',
    'lightning': '⚡',
    'gem': '💎',
    'warning': '⚠️',
    'info': 'ℹ️',
    'lock': '🔐',
    'unlock': '🔓',
    'globe': '🌐',
    'clock': '🕐',
    'target': '🎯',
    'bell': '🔔'
}

def create_progress_bar(current, total, length=10):
    """Create a visual progress bar"""
    if total == 0:
        return "░" * length
    
    filled = int((current / total) * length)
    bar = "█" * filled + "░" * (length - filled)
    percentage = int((current / total) * 100)
    return f"{bar} {percentage}%"

def format_number(number):
    """Format large numbers with K, M suffixes"""
    if number >= 1_000_000:
        return f"{number/1_000_000:.1f}M"
    elif number >= 1_000:
        return f"{number/1_000:.1f}K"
    return str(number)

def create_welcome_message(user_name, is_new=False, welcome_bonus=3, welcome_bonus_enabled=True):
    """Create premium welcome message"""
    welcome_gift_text = ""
    if welcome_bonus_enabled:
        welcome_gift_text = f"\n{EMOJIS['gem']} **Welcome Gift**: **{welcome_bonus} FREE Credits** {EMOJIS['gem']}\n"

    if is_new:
        message = f"""
{EMOJIS['sparkles']} **Welcome to Advanced Info Bot!** {EMOJIS['sparkles']}

Hey **{user_name}**! {EMOJIS['welcome']}

{EMOJIS['rocket']} You're now part of our premium search platform!
{welcome_gift_text}
**{EMOJIS['target']} What Can You Search?**
{EMOJIS['dot']} Mobile Numbers (10 digits)
{EMOJIS['dot']} Aadhar/ID Numbers (12 digits)
{EMOJIS['dot']} Get detailed information instantly!

**{EMOJIS['fire']} Earn More Credits:**
{EMOJIS['trophy']} Add members: **+1 credit per member**
{EMOJIS['bonus']} Daily bonus: **+1 credit every day**
{EMOJIS['star']} Keep your streak for rewards!

**{EMOJIS['info']} Quick Commands:**
/profile - View your stats & rank
/daily - Claim daily bonus
/help - See all features

{EMOJIS['rocket']} **Ready to start?** Join our channel below and start searching!
"""
    else:
        message = f"""
{EMOJIS['welcome']} **Welcome Back, {user_name}!** {EMOJIS['sparkles']}

{EMOJIS['rocket']} Great to see you again!

**{EMOJIS['target']} What Can You Search?**
{EMOJIS['dot']} Mobile Numbers (10 digits)
{EMOJIS['dot']} Aadhar/ID Numbers (12 digits)
{EMOJIS['dot']} Get detailed information instantly!

**{EMOJIS['search']} Quick Actions:**
{EMOJIS['dot']} Send a number in the group to search
{EMOJIS['dot']} Use /daily to claim your bonus
{EMOJIS['dot']} Check /profile for your stats

**{EMOJIS['trophy']} Keep Earning:**
{EMOJIS['fire']} Invite friends to earn credits
{EMOJIS['calendar']} Daily bonuses available
{EMOJIS['chart']} Climb the leaderboard!

Type /help for all commands {EMOJIS['target']}
"""
    
    return message

def create_group_welcome_message(user_name):
    """Create fascinating group welcome message"""
    message = f"""
{EMOJIS['sparkles']} **Hello {user_name}! Welcome to the Future of Information** {EMOJIS['sparkles']}

{EMOJIS['rocket']} **I am your Advanced Information Assistant!**

I can help you find details instantly. Here is how to use me:

**{EMOJIS['target']} To Search:**
{EMOJIS['dot']} **Mobile Number**: Just type the **10-digit number** (e.g., `9876543210`)
{EMOJIS['dot']} **Aadhar/ID**: Just type the **12-digit number** (e.g., `123456789012`)

**{EMOJIS['credit']} Pricing:**
{EMOJIS['gem']} Each search costs only **1 Credit**!

**{EMOJIS['fire']} Features:**
{EMOJIS['check']} Instant Results
{EMOJIS['check']} 24/7 Availability
{EMOJIS['check']} Secure & Private

{EMOJIS['info']} **Ready? Just send a number in this chat!**
"""
    return message

def get_group_welcome_keyboard(channel_link):
    """Get group welcome keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{EMOJIS['search']} How to Search Here ?", callback_data="search_help_alert")],
        [InlineKeyboardButton(f"{EMOJIS['channel']} Join Channel", url=channel_link)]
    ])

def create_credit_display(credits, with_bar=True):
    """Create visual credit display"""
    if credits <= 0:
        color_emoji = EMOJIS['cross']
        status = "No credits"
    elif credits < 5:
        color_emoji = EMOJIS['warning']
        status = "Low credits"
    elif credits < 20:
        color_emoji = EMOJIS['check']
        status = "Good"
    else:
        color_emoji = EMOJIS['fire']
        status = "Excellent"
    
    display = f"{EMOJIS['credit']} **Credits: {credits}** {color_emoji}\n\n"
    
    if with_bar and credits > 0:
        # Show progress to next tier
        if credits < 5:
            bar = create_progress_bar(credits, 5, 8)
            display += f"└─ {bar} (to 5)\n\n"
        elif credits < 20:
            bar = create_progress_bar(credits, 20, 8)
            display += f"└─ {bar} (to 20)\n\n"
    
    return display

def create_search_result_card(result_data, search_type):
    """Create beautifully formatted search result"""
    import json
    
    # Add search type indicator
    if search_type == "mobile":
        header = f"{EMOJIS['success']} **Mobile Number Search** {EMOJIS['sparkles']}"
    else:
        header = f"{EMOJIS['success']} **Aadhar/ID Search** {EMOJIS['sparkles']}"
    
    # Format the data as JSON
    formatted_json = json.dumps(result_data, indent=2, ensure_ascii=False)
    
    message = f"""
{header}

```json
{formatted_json}
```

{EMOJIS['info']} **Powered by Advanced OSINT**
"""
    
    return message

def create_loading_messages():
    """Return list of animated loading messages"""
    return [
        f"{EMOJIS['loading']} Searching database...",
        f"{EMOJIS['search']} Fetching information...",
        f"{EMOJIS['rocket']} Processing data...",
        f"{EMOJIS['sparkles']} Almost there..."
    ]

def create_profile_card(user_data, rank=None, stats=None):
    """Create user profile card"""
    user_name = user_data.get('name', 'User')
    credits = user_data.get('credits', 0)
    total_searches = stats.get('total_searches', 0) if stats else 0
    successful_searches = stats.get('successful', 0) if stats else 0
    joined_date = user_data.get('joined_date', datetime.now())
    
    # Calculate success rate
    success_rate = (successful_searches / total_searches * 100) if total_searches > 0 else 0
    
    message = f"""
{EMOJIS['user']} **User Profile**

**Name:** {user_name}
**User ID:** `{user_data.get('user_id', 'N/A')}`
"""
    
    if rank:
        rank_emoji = EMOJIS['medal_1'] if rank <= 3 else EMOJIS['trophy']
        message += f"**Rank:** {rank_emoji} #{rank}\n"
    
    # Credits section
    message += create_credit_display(credits, with_bar=True)
    
    # Statistics
    message += f"**{EMOJIS['chart']} Statistics**\n\n"
    message += f"{EMOJIS['search']} Total Searches: **{total_searches}**\n"
    message += f"{EMOJIS['success']} Successful: **{successful_searches}**\n"
    
    if total_searches > 0:
        success_bar = create_progress_bar(successful_searches, total_searches, 10)
        message += f"└─ Success Rate: {success_bar}\n"
    
    message += f"\n{EMOJIS['calendar']} Joined: {joined_date.strftime('%d %b %Y')}\n"
    
    return message

def create_leaderboard(users_list, user_rank=None):
    """Create leaderboard display"""
    message = f"""
{EMOJIS['trophy']} **Top Users Leaderboard** {EMOJIS['trophy']}

"""
    
    for idx, user in enumerate(users_list, 1):
        # Medal for top 3
        if idx == 1:
            rank_display = EMOJIS['medal_1']
        elif idx == 2:
            rank_display = EMOJIS['medal_2']
        elif idx == 3:
            rank_display = EMOJIS['medal_3']
        else:
            rank_display = f"{idx}."
        
        name = user.get('name', f"User {user.get('user_id', '???')}")
        credits = user.get('credits', 0)
        searches = user.get('total_searches', 0)
        
        message += f"\n{rank_display} **{name}**\n"
        message += f"   {EMOJIS['credit']} {credits} credits  {EMOJIS['dot']}  {EMOJIS['search']} {searches} searches\n"
    
    if user_rank and user_rank > len(users_list):
        message += f"\n{EMOJIS['info']} Your rank: **#{user_rank}**"
    
    return message

def create_history_card(history_list, page=1, total_pages=1):
    """Create search history display"""
    message = f"""
{EMOJIS['history']} **Search History**
"""
    
    if not history_list:
        message += f"\n{EMOJIS['info']} No search history yet.\n"
    else:
        for idx, search in enumerate(history_list, 1):
            term = search.get('term', 'N/A')
            search_type = search.get('type', 'unknown')
            timestamp = search.get('timestamp', datetime.now())
            success = search.get('success', False)
            
            status_emoji = EMOJIS['success'] if success else EMOJIS['error']
            type_emoji = EMOJIS['globe'] if search_type == 'mobile' else EMOJIS['lock']
            
            time_str = timestamp.strftime('%d %b, %H:%M')
            
            message += f"\n{status_emoji} `{term}` {type_emoji}\n"
            message += f"   {EMOJIS['clock']} {time_str}\n"
    
    if total_pages > 1:
        message += f"\nPage {page}/{total_pages}"
    
    return message

def create_admin_overview(stats):
    """Create admin dashboard overview"""
    message = f"""
{EMOJIS['admin']} **Admin Dashboard** {EMOJIS['admin']}

**{EMOJIS['chart']} Platform Statistics**

{EMOJIS['group']} Total Users: **{format_number(stats.get('total_users', 0))}**
{EMOJIS['fire']} Active (24h): **{format_number(stats.get('active_24h', 0))}**
{EMOJIS['search']} Total Searches: **{format_number(stats.get('total_searches', 0))}**
{EMOJIS['success']} Successful: **{format_number(stats.get('successful_searches', 0))}**
{EMOJIS['credit']} Credits Distributed: **{format_number(stats.get('total_credits', 0))}**

**{EMOJIS['analytics']} Success Rate**
"""
    
    total = stats.get('total_searches', 0)
    successful = stats.get('successful_searches', 0)
    
    if total > 0:
        success_bar = create_progress_bar(successful, total, 15)
        message += f"{success_bar}\n"
    else:
        message += "No data yet\n"
    
    return message

def create_admin_analytics_view(basic_stats, advanced_stats):
    """Create detailed analytics view"""
    growth = advanced_stats.get('growth', {})
    active = advanced_stats.get('active', {})
    top_referrers = advanced_stats.get('top_referrers', [])
    
    message = f"""
{EMOJIS['analytics']} **Advanced Analytics** {EMOJIS['chart']}

**{EMOJIS['group']} User Growth**
{EMOJIS['dot']} Today: **+{growth.get('today', 0)}**
{EMOJIS['dot']} This Week: **+{growth.get('week', 0)}**
{EMOJIS['dot']} This Month: **+{growth.get('month', 0)}**

**{EMOJIS['fire']} Active Users**
{EMOJIS['dot']} Today: **{active.get('today', 0)}**
{EMOJIS['dot']} This Week: **{active.get('week', 0)}**
{EMOJIS['dot']} This Month: **{active.get('month', 0)}**

**{EMOJIS['trophy']} Top Referrers**
"""
    
    if not top_referrers:
        message += f"{EMOJIS['info']} No referral data yet.\n"
    else:
        for idx, ref in enumerate(top_referrers, 1):
            name = ref.get('name', 'Unknown')
            count = ref.get('referrals', 0)
            message += f"{idx}. **{name}**: {count} invites\n"
            
    message += f"""
**{EMOJIS['search']} Search Performance**
Total Searches: **{format_number(basic_stats.get('total_searches', 0))}**
Success Rate: **{basic_stats.get('successful_searches', 0) / basic_stats.get('total_searches', 1) * 100:.1f}%**
"""

    return message

def create_admin_settings_panel(settings):
    """Create admin settings management panel"""
    daily_bonus_enabled = settings.get('daily_bonus_enabled', True)
    daily_bonus_amount = settings.get('daily_bonus_amount', 1)
    welcome_bonus = settings.get('welcome_bonus', 3)
    welcome_bonus_enabled = settings.get('welcome_bonus_enabled', True)
    
    status_on = f"{EMOJIS['success']} Enabled"
    status_off = f"{EMOJIS['error']} Disabled"
    
    message = f"""
{EMOJIS['settings']} **Bot Settings Management**

**{EMOJIS['bonus']} Daily Bonus System**
Status: {status_on if daily_bonus_enabled else status_off}
Amount: **{daily_bonus_amount} credits/day**

**{EMOJIS['gem']} Welcome Bonus**
Status: {status_on if welcome_bonus_enabled else status_off}
Amount: **{welcome_bonus} credits**

{EMOJIS['info']} Use buttons below to modify settings
"""
    
    return message

def create_error_message(error_type, details=None):
    """Create user-friendly error messages"""
    messages = {
        'no_credits': f"""
{EMOJIS['warning']} **Insufficient Credits!**

You need at least 1 credit to perform a search.

**{EMOJIS['fire']} Earn Credits:**
{EMOJIS['dot']} Add members to the group (+1 per member)
{EMOJIS['dot']} Claim daily bonus (/daily)

{EMOJIS['info']} Use /profile to check your balance
""",
        'not_subscribed': f"""
{EMOJIS['channel']} **Channel Subscription Required!**

Please join our channel to use this bot.

{EMOJIS['arrow_right']} Click the button below to join
{EMOJIS['arrow_right']} Click "Refresh" to verify
""",
        'not_found': f"""
{EMOJIS['error']} **No Results Found**

The search returned no data for this number.

**Possible reasons:**
{EMOJIS['dot']} Number not in database
{EMOJIS['dot']} Invalid format
{EMOJIS['dot']} API temporary issue

{EMOJIS['info']} Your credit has been refunded.
""",
        'api_error': f"""
{EMOJIS['warning']} **API Error**

There was an issue fetching the data.

{EMOJIS['info']} Details: {details or 'Unknown error'}

{EMOJIS['rocket']} Please try again later.
Your credit has been refunded.
""",
        'invalid_format': f"""
{EMOJIS['error']} **Invalid Format**

Please send a valid:
{EMOJIS['dot']} 10-digit mobile number
{EMOJIS['dot']} 12-digit Aadhar number

Example: `9876543210`
"""
    }
    
    return messages.get(error_type, f"{EMOJIS['error']} An error occurred.")

def create_help_menu(welcome_bonus=3, welcome_bonus_enabled=True, daily_bonus_enabled=True):
    """Create interactive help menu"""
    
    earn_section = f"**{EMOJIS['fire']} Earn Credits**\n{EMOJIS['dot']} Add members: +1 credit each"
    
    if daily_bonus_enabled:
        earn_section += f"\n{EMOJIS['dot']} Daily bonus: +1 credit/day"
        
    if welcome_bonus_enabled:
        earn_section += f"\n{EMOJIS['dot']} New user bonus: +{welcome_bonus} credits"

    message = f"""
{EMOJIS['info']} **Bot Help & Commands**

**{EMOJIS['search']} Search Commands**
/start - Start the bot
/help - Show this help menu

**{EMOJIS['user']} User Commands**
/profile - View your profile & stats
/history - View search history
/daily - Claim daily bonus
/stats - View your statistics

**{EMOJIS['trophy']} Community**
/leaderboard - Top users ranking

**{EMOJIS['target']} How to Search**
Simply send a 10 or 12-digit number in the group!

{earn_section}
"""
    
    return message

# ==== USER MANAGEMENT UI ====

def create_user_list(users, page=1, total_pages=1, search_query=None):
    """Create user list display for admin"""
    header = f"{EMOJIS['group']} **User Management**"
    
    if search_query:
        header += f"\n{EMOJIS['search']} Search: `{search_query}`"
    
    message = f"{header}\n\n"
    
    if not users:
        message += f"{EMOJIS['info']} No users found.\n"
    else:
        for user in users:
            user_id = user.get('user_id', 'N/A')
            name = user.get('name', f'User {user_id}')
            credits = user.get('credits', 0)
            banned = user.get('banned', False)
            
            status = f"{EMOJIS['error']} BANNED" if banned else f"{EMOJIS['success']}"
            
            message += f"\n{status} **{name}**\n"
            message += f"   ID: `{user_id}` | {EMOJIS['credit']} {credits}\n"
    
    if total_pages > 1:
        message += f"\n\nPage {page}/{total_pages}"
    
    return message

def create_user_detail(user_data):
    """Create detailed user view for admin"""
    user_id = user_data.get('user_id', 'N/A')
    name = user_data.get('name', 'Unknown')
    credits = user_data.get('credits', 0)
    banned = user_data.get('banned', False)
    joined_date = user_data.get('joined_date', datetime.now())
    last_active = user_data.get('last_active', datetime.now())
    
    stats = user_data.get('stats', {})
    rank = user_data.get('rank')
    referrer_name = user_data.get('referrer_name', 'None')
    
    status = f"{EMOJIS['error']} **BANNED**" if banned else f"{EMOJIS['success']} **ACTIVE**"
    
    message = f"""
{EMOJIS['user']} **User Details**

**Name:** {name}
**ID:** `{user_id}`
**Status:** {status}
**Referrer:** {referrer_name}

**{EMOJIS['credit']} Credits:** {credits}
**{EMOJIS['trophy']} Rank:** #{rank if rank else 'N/A'}

**{EMOJIS['chart']} Statistics:**
Total Searches: {stats.get('total_searches', 0)}
Successful: {stats.get('successful_searches', 0)}
Failed: {stats.get('failed_searches', 0)}
Credits Earned: {stats.get('credits_earned', 0)}
Credits Spent: {stats.get('credits_spent', 0)}

**{EMOJIS['calendar']} Joined:** {joined_date.strftime('%d %b %Y')}
**{EMOJIS['clock']} Last Active:** {last_active.strftime('%d %b %Y, %H:%M')}
"""
    
    return message

# Keyboard Builders
def get_welcome_keyboard(group_link, channel_link):
    """Get welcome message keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{EMOJIS['group']} Join Group to Search", url=group_link)],
        [InlineKeyboardButton(f"{EMOJIS['channel']} Join Channel", url=channel_link)]
    ])

def get_subscription_keyboard(channel_link):
    """Get subscription check keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{EMOJIS['channel']} Join Channel", url=channel_link)],
        [InlineKeyboardButton(f"{EMOJIS['check']} Refresh", callback_data="check_sub")]
    ])

def get_no_credits_keyboard(group_link, daily_bonus_enabled=True):
    """Get no credits keyboard"""
    buttons = [
        [InlineKeyboardButton(f"{EMOJIS['fire']} Add Members", url=group_link)]
    ]
    
    if daily_bonus_enabled:
        buttons.append([InlineKeyboardButton(f"{EMOJIS['bonus']} Daily Bonus", callback_data="daily_bonus")])
        
    return InlineKeyboardMarkup(buttons)

def get_result_keyboard(group_link):
    """Get search result keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{EMOJIS['rocket']} Search Again", url=group_link)]
    ])

def get_profile_keyboard():
    """Get profile page keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{EMOJIS['trophy']} Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton(f"{EMOJIS['history']} History", callback_data="history_1")]
    ])

def get_history_keyboard(page, total_pages):
    """Get history pagination keyboard"""
    buttons = []
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(f"{EMOJIS['arrow_left']} Prev", callback_data=f"history_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(f"Next {EMOJIS['arrow_right']}", callback_data=f"history_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(f"{EMOJIS['cross']} Close", callback_data="close")])
    
    return InlineKeyboardMarkup(buttons)

def get_admin_main_keyboard():
    """Get admin dashboard main keyboard"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{EMOJIS['group']} Users", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['analytics']} Analytics", callback_data="admin_analytics"),
            InlineKeyboardButton(f"{EMOJIS['settings']} Settings", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['broadcast']} Broadcast", callback_data="admin_broadcast")
        ]
    ])

def get_admin_settings_keyboard(settings):
    """Get admin settings management keyboard"""
    daily_bonus_enabled = settings.get('daily_bonus_enabled', True)
    welcome_bonus_enabled = settings.get('welcome_bonus_enabled', True)
    
    daily_text = f"{EMOJIS['unlock']} Disable Daily" if daily_bonus_enabled else f"{EMOJIS['lock']} Enable Daily"
    welcome_text = f"{EMOJIS['unlock']} Disable Welcome" if welcome_bonus_enabled else f"{EMOJIS['lock']} Enable Welcome"
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(daily_text, callback_data="toggle_daily_bonus")],
        [InlineKeyboardButton(f"{EMOJIS['credit']} Set Bonus Amount", callback_data="set_bonus_amount")],
        [InlineKeyboardButton(welcome_text, callback_data="toggle_welcome_bonus")],
        [InlineKeyboardButton(f"{EMOJIS['gem']} Set Welcome Bonus", callback_data="set_welcome_bonus")],
        [InlineKeyboardButton(f"{EMOJIS['arrow_left']} Back", callback_data="admin_overview")]
    ])

def get_user_list_keyboard(page, total_pages, has_search=False):
    """Get user list keyboard with pagination and controls"""
    buttons = []
    
    # Search button
    if not has_search:
        buttons.append([InlineKeyboardButton(f"{EMOJIS['search']} Search User", callback_data="user_search")])
    
    # Navigation buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(f"{EMOJIS['arrow_left']} Prev", callback_data=f"users_page_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(f"Next {EMOJIS['arrow_right']}", callback_data=f"users_page_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Back button
    buttons.append([InlineKeyboardButton(f"{EMOJIS['arrow_left']} Back to Admin", callback_data="admin_overview")])
    
    return InlineKeyboardMarkup(buttons)

def get_user_detail_keyboard(user_id, is_banned=False):
    """Get keyboard for user detail actions"""
    ban_text = f"{EMOJIS['unlock']} Unban User" if is_banned else f"{EMOJIS['lock']} Ban User"
    ban_action = f"unban_{user_id}" if is_banned else f"ban_{user_id}"
    
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{EMOJIS['credit']} Add Credits", callback_data=f"add_credits_{user_id}")
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['warning']} Remove Credits", callback_data=f"remove_credits_{user_id}")
        ],
        [InlineKeyboardButton(ban_text, callback_data=ban_action)],
        [InlineKeyboardButton(f"{EMOJIS['arrow_left']} Back to Users", callback_data="admin_users")]
    ])
