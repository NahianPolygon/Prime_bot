from datetime import datetime

MAX_TURNS = 10


class SessionMemory:
    def __init__(self, session_id: str, max_turns: int = MAX_TURNS):
        self.session_id = session_id
        self.max_turns = max_turns
        self.history: list[dict] = []
        self.user_profile: dict = {}

    def add(self, user_msg: str, assistant_msg: str):
        self.history.append(
            {
                "role": "user",
                "content": user_msg,
                "ts": datetime.utcnow().isoformat(),
            }
        )
        self.history.append(
            {
                "role": "assistant",
                "content": assistant_msg,
                "ts": datetime.utcnow().isoformat(),
            }
        )
        if len(self.history) > self.max_turns * 2:
            self.history = self.history[-(self.max_turns * 2) :]

    def get_history_str(self, max_chars: int = 3000) -> str:
        lines = []
        for msg in self.history:
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content']}")
        text = "\n".join(lines)
        if len(text) > max_chars:
            text = "...[earlier context truncated]...\n" + text[-max_chars:]
        return text

    def get_messages_for_llm(self) -> list[dict]:
        return [{"role": m["role"], "content": m["content"]} for m in self.history]

    def update_profile(self, key: str, value):
        self.user_profile[key] = value

    def get_profile_str(self) -> str:
        if not self.user_profile:
            return "No user profile information collected yet."
        lines = [f"- {k}: {v}" for k, v in self.user_profile.items()]
        return "Known about user:\n" + "\n".join(lines)

    def profile_missing_fields(self, required: list[str]) -> list[str]:
        return [f for f in required if f not in self.user_profile or not self.user_profile[f]]

    def clear(self):
        self.history = []
        self.user_profile = {}


_sessions: dict[str, SessionMemory] = {}


def get_session(session_id: str) -> SessionMemory:
    if session_id not in _sessions:
        _sessions[session_id] = SessionMemory(session_id)
    return _sessions[session_id]


def clear_session(session_id: str):
    if session_id in _sessions:
        _sessions[session_id].clear()
