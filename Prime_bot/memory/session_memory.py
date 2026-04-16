from datetime import datetime

MAX_TURNS = 10
MAX_MSG_CHARS = 300
SUMMARIZE_AFTER_TURNS = 6  # summarize when older-half exceeds this many full exchanges

_SUMMARIZE_SYSTEM = (
    "Summarize this conversation excerpt in 2-3 sentences. "
    "Focus on what the user is looking for and what was already discussed. "
    "Be concise and factual."
)


class SessionMemory:
    def __init__(self, session_id: str, max_turns: int = MAX_TURNS):
        self.session_id = session_id
        self.max_turns = max_turns
        self.history: list[dict] = []
        self.user_profile: dict = {}
        self.last_intent: str | None = None
        self._summary: str | None = None

    def _maybe_summarize(self):
        """When history grows large, summarize the oldest half and drop it."""
        threshold_messages = SUMMARIZE_AFTER_TURNS * 2
        if len(self.history) < threshold_messages * 2:
            return

        cutoff = len(self.history) // 2
        to_summarize = self.history[:cutoff]
        self.history = self.history[cutoff:]

        lines = []
        if self._summary:
            lines.append(f"Previous summary: {self._summary}")
        for msg in to_summarize:
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content_short']}")
        excerpt = "\n".join(lines)

        try:
            from llm.ollama_client import chat as llm_chat
            result = llm_chat(
                messages=[{"role": "user", "content": excerpt}],
                system=_SUMMARIZE_SYSTEM,
                temperature=0.0,
                max_tokens=150,
                think=False,
            )
            self._summary = result.strip() if result else self._summary
        except Exception:
            pass

    def _truncate_for_history(self, text: str, max_chars: int = MAX_MSG_CHARS) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "... [truncated]"

    def add(self, user_msg: str, assistant_msg: str):
        self.history.append(
            {
                "role": "user",
                "content": user_msg,
                "content_short": self._truncate_for_history(user_msg),
                "ts": datetime.utcnow().isoformat(),
            }
        )
        self.history.append(
            {
                "role": "assistant",
                "content": assistant_msg,
                "content_short": self._truncate_for_history(assistant_msg),
                "ts": datetime.utcnow().isoformat(),
            }
        )
        if len(self.history) > self.max_turns * 2:
            self.history = self.history[-(self.max_turns * 2):]
        self._maybe_summarize()

    def set_last_intent(self, intent: str):
        self.last_intent = intent

    def get_last_intent(self) -> str | None:
        return self.last_intent

    def get_history_str(self, max_chars: int = 2000) -> str:
        lines = []
        if self._summary:
            lines.append(f"[Earlier summary: {self._summary}]")
        for msg in self.history:
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content_short']}")
        text = "\n".join(lines)
        if len(text) > max_chars:
            text = "...[earlier context truncated]...\n" + text[-max_chars:]
        return text

    def get_last_assistant_response(self) -> str:
        for msg in reversed(self.history):
            if msg["role"] == "assistant":
                return msg["content"]
        return ""

    def get_messages_for_llm(self) -> list[dict]:
        return [{"role": m["role"], "content": m["content_short"]} for m in self.history]

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
        self.last_intent = None
        self._summary = None


_sessions: dict[str, SessionMemory] = {}


def get_session(session_id: str) -> SessionMemory:
    if session_id not in _sessions:
        _sessions[session_id] = SessionMemory(session_id)
    return _sessions[session_id]


def clear_session(session_id: str):
    if session_id in _sessions:
        _sessions[session_id].clear()