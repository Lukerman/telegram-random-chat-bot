"""
Data models and schemas for MongoDB documents.

Defines the structure of documents stored in MongoDB collections.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict


@dataclass
class MonetizeInfo:
    """Monetization information for a user."""
    enabled: bool = True
    last_completed_at: Optional[datetime] = None
    next_due_at: Optional[datetime] = None
    fail_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB."""
        return {
            "enabled": self.enabled,
            "last_completed_at": self.last_completed_at,
            "next_due_at": self.next_due_at,
            "fail_count": self.fail_count
        }


@dataclass
class User:
    """User model representing a Telegram user."""
    tg_id: int
    anon_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    gender: Optional[str] = None  # male, female, other
    preference: str = "any"  # any, same, opposite, other
    consent_files: bool = False
    blocked_users: List[str] = field(default_factory=list)
    warnings: int = 0
    is_banned: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    monetize: MonetizeInfo = field(default_factory=MonetizeInfo)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB."""
        data = asdict(self)
        data['monetize'] = self.monetize.to_dict()
        return data


@dataclass
class SessionUser:
    """User information within a chat session."""
    anon_id: str
    tg_id: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {"anon_id": self.anon_id, "tg_id": self.tg_id}


@dataclass
class Session:
    """Chat session between two users."""
    session_id: str
    user1: SessionUser
    user2: SessionUser
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "active"  # active, ended
    messages_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB."""
        return {
            "session_id": self.session_id,
            "user1": self.user1.to_dict(),
            "user2": self.user2.to_dict(),
            "started_at": self.started_at,
            "status": self.status,
            "messages_count": self.messages_count
        }


@dataclass
class MonetizeToken:
    """Monetization verification token."""
    token: str
    anon_id: str
    tg_id: int
    created_at: datetime
    expires_at: datetime
    status: str = "pending"  # pending, completed, expired
    short_url: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB."""
        return asdict(self)


@dataclass
class Report:
    """User report for moderation."""
    report_id: str
    reporter_anon_id: str
    reported_anon_id: str
    session_id: str
    reason: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"  # pending, reviewed, actioned
    admin_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB."""
        return asdict(self)