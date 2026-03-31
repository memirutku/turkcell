"""Redis-backed conversation memory management for multi-turn chat."""

import logging

from langchain_core.messages import BaseMessage
from langchain_redis import RedisChatMessageHistory

logger = logging.getLogger(__name__)


class MemoryService:
    """Manages conversation history in Redis with session-scoped TTL.

    Uses langchain-redis RedisChatMessageHistory for message storage,
    serialization, and TTL management.
    """

    def __init__(self, redis_url: str, ttl: int = 3600) -> None:
        self._redis_url = redis_url
        self._ttl = ttl

    def _get_chat_history(self, session_id: str) -> RedisChatMessageHistory:
        """Create a RedisChatMessageHistory instance for a session."""
        return RedisChatMessageHistory(
            session_id=session_id,
            redis_url=self._redis_url,
            ttl=self._ttl,
        )

    def get_history(self, session_id: str) -> list[BaseMessage]:
        """Load conversation history for a session from Redis.

        Args:
            session_id: Unique session identifier.

        Returns:
            List of HumanMessage/AIMessage from conversation history.
        """
        try:
            history = self._get_chat_history(session_id)
            return history.messages
        except Exception as e:
            logger.warning("Failed to load history for session %s: %s", session_id, e)
            return []

    def add_messages(self, session_id: str, user_msg: str, ai_msg: str) -> None:
        """Store a user message and AI response in Redis.

        Args:
            session_id: Unique session identifier.
            user_msg: The user's message text.
            ai_msg: The AI assistant's response text.
        """
        try:
            history = self._get_chat_history(session_id)
            history.add_user_message(user_msg)
            history.add_ai_message(ai_msg)
        except Exception as e:
            logger.error("Failed to save messages for session %s: %s", session_id, e)
