from pydantic import BaseModel


class ConversationState(BaseModel):
    session_id: str
    messages: list = []
    domain: str = None
    vertical: str = None
    user_profile: dict = {}
    last_intent: dict = {}
