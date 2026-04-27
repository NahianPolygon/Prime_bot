from __future__ import annotations

from functools import lru_cache

import yaml


_DEFAULT_COLLECTIONS = {
    "all_products": "all_products",
    "conventional_i_need_a_credit_card": "conventional_credit_i_need_a_credit_card",
    "conventional_existing_cardholder": "conventional_credit_existing_cardholder",
    "islami_i_need_a_credit_card": "islami_credit_i_need_a_credit_card",
    "islami_existing_cardholder": "islami_credit_existing_cardholder",
}

_SUPPORTED_BANKING_TYPES = {"conventional", "islami"}
_SUPPORTED_SUFFIXES = {"i_need_a_credit_card", "existing_cardholder"}


@lru_cache(maxsize=1)
def load_config() -> dict:
    with open("config.yaml") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def get_collection_map() -> dict[str, str]:
    cfg = load_config()
    configured = ((cfg.get("knowledge_base") or {}).get("collections") or {})
    merged = dict(_DEFAULT_COLLECTIONS)
    for key, value in configured.items():
        if value:
            merged[str(key)] = str(value)
    return merged


def get_collection(name: str) -> str:
    return get_collection_map().get(name, name)


def get_all_products_collection() -> str:
    return get_collection("all_products")


def get_credit_card_collection(banking_type: str, suffix: str) -> str:
    if banking_type not in _SUPPORTED_BANKING_TYPES:
        raise ValueError(f"Unsupported banking type: {banking_type}")
    if suffix not in _SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported collection suffix: {suffix}")
    return get_collection(f"{banking_type}_{suffix}")


def get_credit_card_collections(banking_type: str, suffix: str) -> list[str]:
    if banking_type == "both":
        return [
            get_credit_card_collection("conventional", suffix),
            get_credit_card_collection("islami", suffix),
        ]
    return [get_credit_card_collection(banking_type, suffix)]
