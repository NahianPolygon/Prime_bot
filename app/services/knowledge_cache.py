import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class KnowledgeBaseCache:
    _instance = None
    _cache = {}
    _products_index = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._load_all_products()
            self._initialized = True

    def _load_all_products(self):
        kb_path = Path("/app/app/knowledge/structured")
        
        conventional_cards = self._load_json(
            kb_path / "conventional" / "credit_cards.json",
            "credit_cards_conventional"
        )
        logger.info(f"📚 Loaded {len(conventional_cards)} conventional credit cards")
        self._cache['conventional_credit_cards'] = conventional_cards
        
        islami_cards = self._load_json(
            kb_path / "islami" / "credit_cards.json",
            "credit_cards"
        )
        logger.info(f"📚 Loaded {len(islami_cards)} islami credit cards")
        self._cache['islami_credit_cards'] = islami_cards

    def _load_json(self, file_path: Path, key: str) -> List[Dict]:
        try:
            logger.info(f"📂 Loading from: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            result = data.get(key, [])
            logger.info(f"✓ Got {len(result)} items from key '{key}'")
            return result
        except Exception as e:
            logger.error(f"✗ Error loading {file_path}: {e}")
            return []

    def get_credit_cards(self, banking_type: Optional[str] = None) -> List[Dict]:
        if banking_type == "islami":
            return self._cache.get('islami_credit_cards', [])
        elif banking_type == "conventional":
            return self._cache.get('conventional_credit_cards', [])
        else:
            return (
                self._cache.get('conventional_credit_cards', []) +
                self._cache.get('islami_credit_cards', [])
            )

    def get_all_products(self) -> Dict[str, List[Dict]]:
        return self._cache.copy()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
