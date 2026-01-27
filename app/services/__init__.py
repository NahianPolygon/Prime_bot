"""Services Package"""

from app.services.llm_service import (
    detect_intent,
    check_eligibility,
    compare_products,
    explain_product,
    generate_response,
)
from app.services.knowledge_service import (
    load_products,
    get_all_products,
    format_products_for_llm,
    get_product_markdown,
)
from app.services.conversation_manager import ConversationManager

__all__ = [
    "detect_intent",
    "check_eligibility",
    "compare_products",
    "explain_product",
    "generate_response",
    "load_products",
    "get_all_products",
    "format_products_for_llm",
    "get_product_markdown",
    "ConversationManager",
]
