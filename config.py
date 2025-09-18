import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Parse authorized users from comma-separated string
AUTHORIZED_USERS_STR = os.getenv("AUTHORIZED_USERS", "")
AUTHORIZED_USERS = [int(user_id.strip()) for user_id in AUTHORIZED_USERS_STR.split(",") if user_id.strip()]

# File Configuration
LICENSE_FILE = "licenses.json"