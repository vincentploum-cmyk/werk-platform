# Event bus - Redis Pub/Sub agent communication

import json
import redis.asyncio as aioredis


class EventBus:
    """Agent collaboration event bus using Redis Pub/Sub."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._pub = None
        self._sub = None

    async def connect(self):
        self._pub = await aioredis.from_url(self.redis_url)
        self._sub = self._pub.pubsub()

    async def publish(self, channel: str, event: dict):
        """Publish an event to a channel."""
        if self._pub:
            await self._pub.publish(channel, json.dumps(event))

    async def subscribe(self, channel: str):
        """Subscribe to a channel."""
        if self._sub:
            await self._sub.subscribe(channel)

    async def get_message(self, timeout: float = 1.0):
        """Get the next message from subscribed channels."""
        if self._sub:
            msg = await self._sub.get_message(timeout=timeout)
            if msg and msg["type"] == "message":
                return json.loads(msg["data"])
        return None

    async def close(self):
        if self._pub:
            await self._pub.close()
        if self._sub:
            await self._sub.close()