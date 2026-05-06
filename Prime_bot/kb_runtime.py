from __future__ import annotations

import json
import re
from pathlib import Path

import yaml


RUNTIME_CONFIG_PATH = Path("runtime_kb_config.json")
DEFAULT_BANK = "prime_bank"
DOCUMENT_TYPES = ("i_need_a_credit_card", "existing_cardholder")
BANKING_TYPES = ("conventional", "islami", "both")

_COLLECTION_SUFFIXES = {
    "all_products": "all_products",
    "conventional_i_need_a_credit_card": "conventional_credit_i_need_a_credit_card",
    "conventional_existing_cardholder": "conventional_credit_existing_cardholder",
    "islami_i_need_a_credit_card": "islami_credit_i_need_a_credit_card",
    "islami_existing_cardholder": "islami_credit_existing_cardholder",
}


def slugify_bank(value: str, fallback: str = DEFAULT_BANK) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")
    return cleaned or fallback


def build_collection_map(bank_slug: str) -> dict[str, str]:
    slug = slugify_bank(bank_slug)
    return {key: f"{slug}_{suffix}" for key, suffix in _COLLECTION_SUFFIXES.items()}


def _load_yaml_defaults() -> dict:
    try:
        with open("config.yaml") as f:
            cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        cfg = {}
    kb_cfg = cfg.get("knowledge_base") or {}
    bank = slugify_bank(str(kb_cfg.get("active_company") or DEFAULT_BANK))
    collections = build_collection_map(bank)
    for key, value in (kb_cfg.get("collections") or {}).items():
        if key in collections and value:
            collections[str(key)] = str(value)
    return {
        "active_bank": bank,
        "collections": collections,
    }


def normalize_state(state: dict | None = None) -> dict:
    defaults = _load_yaml_defaults()
    incoming = state or {}
    active_bank = slugify_bank(str(incoming.get("active_bank") or defaults["active_bank"]))

    collections = build_collection_map(active_bank)
    for key, value in (incoming.get("collections") or {}).items():
        if key in collections and value:
            collections[str(key)] = str(value)

    return {
        "active_bank": active_bank,
        "collections": collections,
    }


def load_runtime_state() -> dict:
    if not RUNTIME_CONFIG_PATH.exists():
        return normalize_state()
    try:
        return normalize_state(json.loads(RUNTIME_CONFIG_PATH.read_text(encoding="utf-8")))
    except Exception:
        return normalize_state()


def save_runtime_state(state: dict) -> dict:
    normalized = normalize_state(state)
    RUNTIME_CONFIG_PATH.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    return normalized


def get_active_bank() -> str:
    return load_runtime_state()["active_bank"]


def get_runtime_collection_map() -> dict[str, str]:
    return load_runtime_state()["collections"]
