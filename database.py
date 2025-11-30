from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI
from datetime import datetime, timedelta

class Database:
    def __init__(self, uri):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client['infobot_dbbb']
        self.users = self.db['users']
        self.search_history = self.db['search_history']
        self.daily_bonuses = self.db['daily_bonuses']
        self.user_stats = self.db['user_stats']
        self.bot_settings = self.db['bot_settings']
    
    async def _init_settings(self):
        """Initialize default bot settings if not present"""
        settings = await self.bot_settings.find_one({'_id': 'main_settings'})
        if not settings:
            default_settings = {
                '_id': 'main_settings',
                'daily_bonus_enabled': True,
                'daily_bonus_amount': 1,
                'result_expiration_enabled': False,
                'result_expire_time': 3600,
                'welcome_bonus': 3,
                'welcome_bonus_enabled': True
            }
            await self.bot_settings.insert_one(default_settings)

    async def add_user(self, user_id, user_name=None, referrer_id=None):
        """Add a new user with welcome bonus"""
        user = await self.users.find_one({'user_id': user_id})
        if not user:
            # Get welcome bonus from settings
            settings = await self.get_all_settings()
            welcome_bonus = settings.get('welcome_bonus', 3)
            if not settings.get('welcome_bonus_enabled', True):
                welcome_bonus = 0
            
            new_user = {
                'user_id': user_id,
                'name': user_name,
                'credits': welcome_bonus,
                'referrer_id': referrer_id,
                'joined_date': datetime.now(),
                'last_active': datetime.now()
            }
            await self.users.insert_one(new_user)
            
            # Initialize user stats
            await self.user_stats.insert_one({
                'user_id': user_id,
                'total_searches': 0,
                'successful_searches': 0,
                'failed_searches': 0,
                'credits_earned': welcome_bonus,
                'credits_spent': 0
            })
            return True
        return False

    async def get_user(self, user_id):
        """Get user data"""
        return await self.users.find_one({'user_id': user_id})

    async def add_credits(self, user_id, amount):
        """Add credits to user"""
        await self.users.update_one(
            {'user_id': user_id},
            {'$inc': {'credits': amount}}
        )
        # Update stats
        await self.user_stats.update_one(
            {'user_id': user_id},
            {'$inc': {'credits_earned': amount}},
            upsert=True
        )

    async def deduct_credit(self, user_id):
        """Deduct one credit from user"""
        await self.users.update_one(
            {'user_id': user_id},
            {'$inc': {'credits': -1}}
        )
        # Update stats
        await self.user_stats.update_one(
            {'user_id': user_id},
            {'$inc': {'credits_spent': 1}},
            upsert=True
        )

    async def check_referral(self, new_member_id, adder_id, new_member_name=None):
        """Check and process referral"""
        is_new = await self.add_user(new_member_id, new_member_name, referrer_id=adder_id)
        
        if is_new:
            # Give 1 credit to the adder
            await self.add_credits(adder_id, 1)
            return True
        return False

    async def get_total_users(self):
        """Get total number of users"""
        return await self.users.count_documents({})

    async def get_total_credits_distributed(self):
        """Get total credits distributed"""
        pipeline = [
            {"$group": {"_id": None, "total_credits": {"$sum": "$credits"}}}
        ]
        result = await self.users.aggregate(pipeline).to_list(length=1)
        return result[0]['total_credits'] if result else 0
    
    # ===== SEARCH HISTORY =====
    
    async def add_search_history(self, user_id, term, search_type, success=True, result_data=None):
        """Record a search in history"""
        search_record = {
            'user_id': user_id,
            'term': term,
            'type': search_type,
            'success': success,
            'result_data': result_data,
            'timestamp': datetime.now()
        }
        await self.search_history.insert_one(search_record)
        
        # Update user stats
        update_fields = {'total_searches': 1}
        if success:
            update_fields['successful_searches'] = 1
        else:
            update_fields['failed_searches'] = 1
        
        await self.user_stats.update_one(
            {'user_id': user_id},
            {'$inc': update_fields},
            upsert=True
        )
        
        # Update last active
        await self.users.update_one(
            {'user_id': user_id},
            {'$set': {'last_active': datetime.now()}}
        )
    
    async def get_user_history(self, user_id, limit=10, skip=0):
        """Get user's search history with pagination"""
        cursor = self.search_history.find(
            {'user_id': user_id}
        ).sort('timestamp', -1).skip(skip).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    async def get_history_count(self, user_id):
        """Get total history count for user"""
        return await self.search_history.count_documents({'user_id': user_id})
    
    # ===== USER STATISTICS =====
    
    async def get_user_stats(self, user_id):
        """Get comprehensive user statistics"""
        stats = await self.user_stats.find_one({'user_id': user_id})
        if not stats:
            # Initialize if not present
            stats = {
                'user_id': user_id,
                'total_searches': 0,
                'successful_searches': 0,
                'failed_searches': 0,
                'credits_earned': 0,
                'credits_spent': 0
            }
            await self.user_stats.insert_one(stats)
        return stats
    
    async def update_user_activity(self, user_id):
        """Update last active timestamp"""
        await self.users.update_one(
            {'user_id': user_id},
            {'$set': {'last_active': datetime.now()}}
        )
    
    # ===== DAILY BONUS =====
    
    async def claim_daily_bonus(self, user_id):
        """Claim daily bonus if eligible"""
        # Check settings
        settings = await self.get_all_settings()
        if not settings.get('daily_bonus_enabled', True):
            return {'success': False, 'message': 'Daily bonus is currently disabled'}
        
        bonus_amount = settings.get('daily_bonus_amount', 1)
        
        # Check last claim
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        last_claim = await self.daily_bonuses.find_one({
            'user_id': user_id,
            'claim_date': {'$gte': today}
        })
        
        if last_claim:
            next_claim_time = today + timedelta(days=1)
            hours_left = (next_claim_time - datetime.now()).seconds // 3600
            return {
                'success': False,
                'message': f'Already claimed today! Come back in {hours_left}h',
                'already_claimed': True
            }
        
        # Add bonus
        await self.add_credits(user_id, bonus_amount)
        
        # Record claim
        await self.daily_bonuses.insert_one({
            'user_id': user_id,
            'claim_date': datetime.now(),
            'amount': bonus_amount
        })
        
        # Calculate streak
        yesterday = today - timedelta(days=1)
        yesterday_claim = await self.daily_bonuses.find_one({
            'user_id': user_id,
            'claim_date': {'$gte': yesterday, '$lt': today}
        })
        
        streak = 1
        if yesterday_claim:
            # User has a streak going
            user_data = await self.users.find_one({'user_id': user_id})
            streak = user_data.get('daily_streak', 0) + 1
            await self.users.update_one(
                {'user_id': user_id},
                {'$set': {'daily_streak': streak}}
            )
        else:
            await self.users.update_one(
                {'user_id': user_id},
                {'$set': {'daily_streak': 1}}
            )
        
        return {
            'success': True,
            'amount': bonus_amount,
            'streak': streak
        }
    
    # ===== LEADERBOARD =====
    
    async def get_leaderboard(self, limit=10, sort_by='credits'):
        """Get top users leaderboard"""
        if sort_by == 'credits':
            cursor = self.users.find().sort('credits', -1).limit(limit)
        elif sort_by == 'searches':
            # Join with stats
            pipeline = [
                {
                    '$lookup': {
                        'from': 'user_stats',
                        'localField': 'user_id',
                        'foreignField': 'user_id',
                        'as': 'stats'
                    }
                },
                {'$unwind': {'path': '$stats', 'preserveNullAndEmptyArrays': True}},
                {'$addFields': {
                    'total_searches': {'$ifNull': ['$stats.total_searches', 0]}
                }},
                {'$sort': {'total_searches': -1}},
                {'$limit': limit}
            ]
            cursor = self.users.aggregate(pipeline)
        else:
            cursor = self.users.find().sort('credits', -1).limit(limit)
        
        users = await cursor.to_list(length=limit)
        
        # Enrich with stats
        for user in users:
            stats = await self.get_user_stats(user['user_id'])
            user['total_searches'] = stats.get('total_searches', 0)
            user['successful'] = stats.get('successful_searches', 0)
        
        return users
    
    async def get_user_rank(self, user_id):
        """Get user's rank by credits"""
        user = await self.users.find_one({'user_id': user_id})
        if not user:
            return None
        
        user_credits = user.get('credits', 0)
        higher_users = await self.users.count_documents({'credits': {'$gt': user_credits}})
        
        return higher_users + 1
    
    # ===== ADMIN ANALYTICS =====
    
    async def get_admin_analytics(self):
        """Get comprehensive platform analytics"""
        total_users = await self.users.count_documents({})
        
        # Active users in last 24h
        yesterday = datetime.now() - timedelta(days=1)
        active_24h = await self.users.count_documents({
            'last_active': {'$gte': yesterday}
        })
        
        # Total searches
        total_searches_pipeline = [
            {'$group': {'_id': None, 'total': {'$sum': '$total_searches'}}}
        ]
        search_result = await self.user_stats.aggregate(total_searches_pipeline).to_list(length=1)
        total_searches = search_result[0]['total'] if search_result else 0
        
        # Successful searches
        successful_pipeline = [
            {'$group': {'_id': None, 'total': {'$sum': '$successful_searches'}}}
        ]
        success_result = await self.user_stats.aggregate(successful_pipeline).to_list(length=1)
        successful_searches = success_result[0]['total'] if success_result else 0
        
        # Total credits
        total_credits = await self.get_total_credits_distributed()
        
        return {
            'total_users': total_users,
            'active_24h': active_24h,
            'total_searches': total_searches,
            'successful_searches': successful_searches,
            'total_credits': total_credits
        }

    async def get_advanced_analytics(self):
        """Get advanced analytics for detailed view"""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)
        
        # 1. User Growth
        new_users_today = await self.users.count_documents({'joined_date': {'$gte': today_start}})
        new_users_week = await self.users.count_documents({'joined_date': {'$gte': week_start}})
        new_users_month = await self.users.count_documents({'joined_date': {'$gte': month_start}})
        
        # 2. Active Users
        active_today = await self.users.count_documents({'last_active': {'$gte': today_start}})
        active_week = await self.users.count_documents({'last_active': {'$gte': week_start}})
        active_month = await self.users.count_documents({'last_active': {'$gte': month_start}})
        
        # 3. Top Referrers
        pipeline = [
            {'$match': {'referrer_id': {'$ne': None}}},
            {'$group': {'_id': '$referrer_id', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 5},
            {'$lookup': {
                'from': 'users',
                'localField': '_id',
                'foreignField': 'user_id',
                'as': 'referrer_info'
            }},
            {'$unwind': '$referrer_info'},
            {'$project': {
                'name': '$referrer_info.name',
                'user_id': '$_id',
                'referrals': '$count'
            }}
        ]
        top_referrers = await self.users.aggregate(pipeline).to_list(length=5)
        
        return {
            'growth': {
                'today': new_users_today,
                'week': new_users_week,
                'month': new_users_month
            },
            'active': {
                'today': active_today,
                'week': active_week,
                'month': active_month
            },
            'top_referrers': top_referrers
        }
    
    # ===== BOT SETTINGS =====
    
    async def get_setting(self, key, default=None):
        """Get a specific bot setting"""
        settings = await self.bot_settings.find_one({'_id': 'main_settings'})
        if settings:
            return settings.get(key, default)
        return default
    
    async def update_setting(self, key, value):
        """Update a bot setting"""
        await self.bot_settings.update_one(
            {'_id': 'main_settings'},
            {'$set': {key: value}},
            upsert=True
        )
    
    async def get_all_settings(self):
        """Get all bot settings"""
        settings = await self.bot_settings.find_one({'_id': 'main_settings'})
        if not settings:
            await self._init_settings()
            settings = await self.bot_settings.find_one({'_id': 'main_settings'})
        return settings
    
    # ===== USER MANAGEMENT =====
    
    async def search_users(self, query, limit=10):
        """Search users by name or ID"""
        try:
            # Try to search by user_id if query is numeric
            if query.isdigit():
                user_id = int(query)
                user = await self.users.find_one({'user_id': user_id})
                return [user] if user else []
            else:
                # Search by name (case-insensitive partial match)
                cursor = self.users.find({
                    'name': {'$regex': query, '$options': 'i'}
                }).limit(limit)
                return await cursor.to_list(length=limit)
        except:
            return []
    
    async def get_all_users(self, skip=0, limit=10):
        """Get all users with pagination"""
        cursor = self.users.find().sort('joined_date', -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def get_user_detailed(self, user_id):
        """Get detailed user information including stats"""
        user = await self.users.find_one({'user_id': user_id})
        if not user:
            return None
        
        # Get stats
        stats = await self.get_user_stats(user_id)
        
        # Get rank
        rank = await self.get_user_rank(user_id)
        
        # Get referrer name if exists
        referrer_name = "None"
        if user.get('referrer_id'):
            referrer = await self.users.find_one({'user_id': user.get('referrer_id')})
            if referrer:
                referrer_name = referrer.get('name', 'Unknown')
                # Append ID for clarity
                referrer_name += f" ({user.get('referrer_id')})"
        
        # Combine all data
        user['stats'] = stats
        user['rank'] = rank
        user['referrer_name'] = referrer_name
        
        return user
    
    async def add_credits_to_user(self, user_id, amount):
        """Add credits to a specific user (admin function)"""
        await self.add_credits(user_id, amount)
    
    async def remove_credits_from_user(self, user_id, amount):
        """Remove credits from a specific user (admin function)"""
        current_user = await self.users.find_one({'user_id': user_id})
        if current_user:
            current_credits = current_user.get('credits', 0)
            new_credits = max(0, current_credits - amount)
            await self.users.update_one(
                {'user_id': user_id},
                {'$set': {'credits': new_credits}}
            )
    
    async def ban_user(self, user_id):
        """Ban a user"""
        await self.users.update_one(
            {'user_id': user_id},
            {'$set': {'banned': True, 'ban_date': datetime.now()}}
        )
    
    async def unban_user(self, user_id):
        """Unban a user"""
        await self.users.update_one(
            {'user_id': user_id},
            {'$set': {'banned': False}, '$unset': {'ban_date': ''}}
        )
    
    async def is_user_banned(self, user_id):
        """Check if a user is banned"""
        user = await self.users.find_one({'user_id': user_id})
        return user.get('banned', False) if user else False

db = Database(MONGO_URI)

