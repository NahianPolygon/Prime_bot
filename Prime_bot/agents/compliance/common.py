import re


def clean_context(context: str) -> str:
    context = re.sub(r"product_id:\s*\S+", "", context)
    context = re.sub(r"\b(?:CARD|ISLAMI_CARD)_\d+\b", "", context)
    context = re.sub(r"\n\s*\n\s*\n", "\n\n", context)
    return context.strip()


def safe_int(value, default=0):
    if value is None or str(value).strip() == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def get_collections(banking: str, suffix: str) -> list[str]:
    if banking == "both":
        return [
            f"conventional_credit_{suffix}",
            f"islami_credit_{suffix}",
        ]
    return [f"{banking}_credit_{suffix}"]


def meta_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = str(value).split(",")
    return [str(item).strip().lower() for item in items if str(item).strip()]

