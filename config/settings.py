"""
Configuration management for the Random Chat Bot.

Loads settings from environment variables with validation.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # Telegram Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "")
    ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0"))
    
    # MongoDB
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://mongodb:27017/randomchat")
    
    # Monetization
    MONETIZE_ENABLED: bool = os.getenv("MONETIZE_ENABLED", "true").lower() == "true"
    MONETIZE_INTERVAL_HOURS: int = int(os.getenv("MONETIZE_INTERVAL_HOURS", "12"))
    MONETIZE_TOKEN_TTL_MINUTES: int = int(os.getenv("MONETIZE_TOKEN_TTL_MINUTES", "30"))
    MONETIZE_MIN_WAIT_SECONDS: int = int(os.getenv("MONETIZE_MIN_WAIT_SECONDS", "10"))
    SHORT_URL: str = os.getenv("SHORT_URL", "https://example.com")
    
    # Application
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    WARN_THRESHOLD: int = int(os.getenv("WARN_THRESHOLD", "3"))
    
    def validate(self) -> None:
        """
        Validate that all required settings are present.
        
        Raises:
            ValueError: If required settings are missing
        """
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        if not self.BOT_USERNAME:
            raise ValueError("BOT_USERNAME is required")
        if not self.ADMIN_CHAT_ID:
            raise ValueError("ADMIN_CHAT_ID is required")
        if not self.MONGODB_URI:
            raise ValueError("MONGODB_URI is required")


# Create global settings instance
settings = Settings()

# Validate on import
try:
    settings.validate()
except ValueError as e:
    print(f"Configuration error: {e}")
    print("Please check your .env file and ensure all required variables are set.")
    exit(1)