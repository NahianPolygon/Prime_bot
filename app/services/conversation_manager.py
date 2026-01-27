import json
import redis.asyncio as redis
from app.models.state import ConversationState


class ConversationManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.prefix = "conversation:"

    async def get_state(self, session_id: str) -> ConversationState:
        key = f"{self.prefix}{session_id}"
        data = await self.redis.get(key)

        if not data:
            return ConversationState(session_id=session_id)

        return ConversationState(**json.loads(data))

    async def save_state(self, state: ConversationState):
        key = f"{self.prefix}{state.session_id}"
        await self.redis.setex(
            key,
            86400,
            state.model_dump_json()
        )

    async def update_domain(self, session_id: str, domain: str):
        state = await self.get_state(session_id)
        state.domain = domain
        await self.save_state(state)

    async def update_vertical(self, session_id: str, vertical: str):
        state = await self.get_state(session_id)
        state.vertical = vertical
        await self.save_state(state)

    async def add_message(self, session_id: str, role: str, content: str):
        state = await self.get_state(session_id)
        state.messages.append({
            "role": role,
            "content": content
        })
        await self.save_state(state)

    async def clear_state(self, session_id: str):
        key = f"{self.prefix}{session_id}"
        await self.redis.delete(key)
