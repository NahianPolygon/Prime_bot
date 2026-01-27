import json
from pathlib import Path
from functools import lru_cache


class KnowledgeBase:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent / "knowledge" / "structured"
        self._load_all()

    def _load_all(self):
        self.conventional_credit = self._load_json(
            "conventional/credit_cards.json"
        )
        self.islami_credit = self._load_json(
            "islami/credit_cards.json"
        )
        self.conventional_accounts = self._load_json(
            "conventional/deposit_accounts.json"
        )
        self.conventional_schemes = self._load_json(
            "conventional/deposit_schemes.json"
        )
        self.islami_accounts = self._load_json(
            "islami/deposit_accounts.json"
        )
        self.islami_schemes = self._load_json(
            "islami/deposit_schemes.json"
        )

    def _load_json(self, path: str) -> dict:
        full_path = self.base_path / path
        if not full_path.exists():
            return {}
        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_credit_cards(self, banking_type: str) -> list:
        if banking_type == "conventional":
            return self.conventional_credit.get("credit_cards_conventional", [])
        elif banking_type == "islami":
            return self.islami_credit.get("credit_cards_islamic", [])
        return []

    def get_accounts(self, banking_type: str) -> list:
        if banking_type == "conventional":
            return self.conventional_accounts.get("accounts", [])
        elif banking_type == "islami":
            return self.islami_accounts.get("accounts", [])
        return []

    def get_schemes(self, banking_type: str) -> list:
        if banking_type == "conventional":
            return self.conventional_schemes.get("schemes", [])
        elif banking_type == "islami":
            return self.islami_schemes.get("schemes", [])
        return []

    def search_product(self, name: str, banking_type: str = None) -> dict:
        name_lower = name.lower()

        if not banking_type or banking_type == "conventional":
            for card in self.get_credit_cards("conventional"):
                if name_lower in card.get("name", "").lower():
                    return card

        if not banking_type or banking_type == "islami":
            for card in self.get_credit_cards("islami"):
                if name_lower in card.get("name", "").lower():
                    return card

        return {}


@lru_cache(maxsize=1)
def get_knowledge_base() -> KnowledgeBase:
    return KnowledgeBase()
