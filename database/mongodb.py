"""
MongoDB connection and database management.

Provides async MongoDB client using Motor and database access functions.
"""

import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from config.settings import settings

logger = logging.getLogger(__name__)

# Global MongoDB client
_mongo_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


async def init_db() -> AsyncIOMotorDatabase:
    """
    Initialize MongoDB connection and create indexes.
    
    Returns:
        AsyncIOMotorDatabase: Database instance
        
    Raises:
        ConnectionFailure: If connection to MongoDB fails
    """
    global _mongo_client, _database
    
    try:
        logger.info(f"Connecting to MongoDB: {settings.MONGODB_URI}")
        
        _mongo_client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000
        )
        
        # Test connection
        await _mongo_client.admin.command('ping')
        
        # Get database
        db_name = settings.MONGODB_URI.split('/')[-1].split('?')[0]
        _database = _mongo_client[db_name]
        
        # Create indexes
        await _create_indexes(_database)
        
        logger.info("MongoDB connected and indexes created")
        return _database
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def _create_indexes(db: AsyncIOMotorDatabase) -> None:
    """
    Create database indexes for optimized queries.
    
    Args:
        db: Database instance
    """
    # Users collection indexes
    await db.users.create_index("tg_id", unique=True)
    await db.users.create_index("anon_id", unique=True)
    await db.users.create_index("is_banned")
    await db.users.create_index("last_active")
    
    # Sessions collection indexes
    await db.sessions.create_index("session_id", unique=True)
    await db.sessions.create_index("user1.tg_id")
    await db.sessions.create_index("user2.tg_id")
    await db.sessions.create_index("status")
    await db.sessions.create_index("started_at")
    
    # Monetize tokens collection indexes
    await db.monetize_tokens.create_index("token", unique=True)
    await db.monetize_tokens.create_index("tg_id")
    await db.monetize_tokens.create_index("expires_at", expireAfterSeconds=0)  # TTL index
    await db.monetize_tokens.create_index("status")
    
    # Reports collection indexes
    await db.reports.create_index("report_id", unique=True)
    await db.reports.create_index("reporter_anon_id")
    await db.reports.create_index("reported_anon_id")
    await db.reports.create_index("created_at")
    await db.reports.create_index("status")
    
    # Settings collection - ensure global settings exist
    await db.settings.update_one(
        {"_id": "global_settings"},
        {
            "$setOnInsert": {
                "monetize_enabled": settings.MONETIZE_ENABLED,
                "monetize_interval_hours": settings.MONETIZE_INTERVAL_HOURS,
                "monetize_token_ttl_minutes": settings.MONETIZE_TOKEN_TTL_MINUTES,
                "monetize_min_wait_seconds": settings.MONETIZE_MIN_WAIT_SECONDS,
                "monetize_blocked_features": ["newchat", "send_file"],
                "short_url": settings.SHORT_URL,
                "admin_chat_id": settings.ADMIN_CHAT_ID,
                "warn_threshold": settings.WARN_THRESHOLD
            }
        },
        upsert=True
    )
    
    logger.info("Database indexes created successfully")


def get_db() -> AsyncIOMotorDatabase:
    """
    Get the database instance.
    
    Returns:
        AsyncIOMotorDatabase: Database instance
        
    Raises:
        RuntimeError: If database is not initialized
    """
    if _database is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _database


async def close_db() -> None:
    """Close MongoDB connection."""
    global _mongo_client, _database
    
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        _database = None
        logger.info("MongoDB connection closed")