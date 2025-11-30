import os
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
REQUIRED_CHANNEL_ID = int(os.getenv("REQUIRED_CHANNEL_ID", 0))
REQUIRED_CHANNEL_LINK = os.getenv("REQUIRED_CHANNEL_LINK")
GROUP_ID = int(os.getenv("GROUP_ID", 0))
GROUP_LINK = os.getenv("GROUP_LINK")
AETHER_API_KEY = os.getenv("AETHER_API_KEY", "sherry")
