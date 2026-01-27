import json
from pathlib import Path
from typing import List, Dict, Optional

KNOWLEDGE_BASE = Path("/app/app/knowledge")


def load_products(banking_type: str = "conventional", category: str = None) -> List[Dict]:
    if category == "credit":
        json_file = KNOWLEDGE_BASE / "structured" / banking_type / "credit_cards.json"
        try:
            if json_file.exists():
                with open(json_file) as f:
                    data = json.load(f)
                    key = list(data.keys())[0]
                    return data[key]
        except Exception as e:
            print(f"Error loading credit products: {e}")
    
    elif category == "deposit":
        json_file = KNOWLEDGE_BASE / "structured" / banking_type / "deposit_accounts.json"
        try:
            if json_file.exists():
                with open(json_file) as f:
                    data = json.load(f)
                    products = []
                    for key, value in data.items():
                        if isinstance(value, dict):
                            products.append({
                                'name': value.get('product_name', key),
                                'category': value.get('category', 'Savings'),
                                'id': value.get('product_id', key),
                                **value
                            })
                    return products
        except Exception as e:
            print(f"Error loading deposit products: {e}")
    
    elif category == "schemes":
        json_file = KNOWLEDGE_BASE / "structured" / banking_type / "deposit_schemes.json"
        try:
            if json_file.exists():
                with open(json_file) as f:
                    data = json.load(f)
                    if "deposit_schemes" in data:
                        return data["deposit_schemes"]
                    return list(data.values()) if data else []
        except Exception as e:
            print(f"Error loading deposit schemes: {e}")
    
    return []


def get_all_products(banking_type: str = "conventional") -> Dict[str, List[Dict]]:
    return {
        "credit_cards": load_products(banking_type, "credit"),
        "deposit_accounts": load_products(banking_type, "deposit"),
        "deposit_schemes": load_products(banking_type, "schemes"),
    }


def format_products_for_llm(products: List[Dict], max_products: int = 5) -> str:
    formatted = []
    for product in products[:max_products]:
        summary = {
            "name": product.get("product_name") or product.get("name"),
            "type": product.get("category") or product.get("type"),
            "key_feature": product.get("tagline") or product.get("summary"),
            "interest_rate": product.get("interest_rate"),
            "monthly_charge": product.get("monthly_charge"),
        }
        formatted.append(summary)
    
    return json.dumps(formatted, indent=2)


def get_product_markdown(product_name: str, banking_type: str = "conventional") -> Optional[str]:
    search_name = product_name.lower().replace(" ", "_") + ".md"
    
    try:
        for root, dirs, files in __import__('os').walk(KNOWLEDGE_BASE / "products" / banking_type):
            for file in files:
                if file == search_name:
                    with open(Path(root) / file) as f:
                        return f.read()
    except Exception:
        pass
    
    return None
