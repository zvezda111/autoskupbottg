import os
from dotenv import load_dotenv

load_dotenv()

API_KEY        = os.getenv("API_KEY", "")
VALID_DIR      = os.getenv("VALID_DIR", "exported_sessions/valid")
SPAM_DIR       = os.getenv("SPAM_DIR",  "exported_sessions/spam")