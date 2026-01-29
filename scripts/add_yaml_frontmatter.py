import json
from pathlib import Path

KB_PATH = Path("/app/app/knowledge")
STRUCTURED_PATH = KB_PATH / "structured"
PRODUCTS_PATH = KB_PATH / "products"

def load_product_mapping():
    mapping = {}
    
    try:
        conv_credit = STRUCTURED_PATH / "conventional" / "credit_cards.json"
        with open(conv_credit, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for p in data.get("credit_cards_conventional", []):
                name_key = p.get('name', '').lower().replace(" ", "_").replace("-", "_")
                mapping[name_key] = (p, "conventional")
    except Exception as e:
        print(f"Error loading conventional: {e}")
    
    try:
        isl_credit = STRUCTURED_PATH / "islami" / "credit_cards.json"
        with open(isl_credit, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for p in data.get("credit_cards", []):
                name_key = p.get('name', '').lower().replace(" ", "_").replace("-", "_")
                mapping[name_key] = (p, "islami")
    except Exception as e:
        print(f"Error loading islami: {e}")
    
    return mapping

def add_yaml_to_file(md_file_path, product_data, banking_type):
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if content.startswith("---"):
        return False
    
    suitable_for = product_data.get('filtering_metadata', {}).get('suitable_for', [])
    min_age = product_data.get('filtering_metadata', {}).get('min_age')
    max_age = product_data.get('filtering_metadata', {}).get('max_age')
    min_income = product_data.get('filtering_metadata', {}).get('min_income')
    keywords = product_data.get('filtering_metadata', {}).get('keywords', [])
    use_cases = product_data.get('filtering_metadata', {}).get('use_cases', [])
    
    yaml_lines = [
        "---",
        f"product_id: {product_data.get('id', '')}",
        f"product_name: {product_data.get('name', '')}",
        f"banking_type: {banking_type}",
        f"category: credit_card",
        f"card_network: {product_data.get('card_network', '')}",
        f"tier: {str(product_data.get('tier', '')).lower()}",
        f"employment_suitable: {suitable_for}",
        f"age_min: {min_age}",
        f"age_max: {max_age}",
        f"income_min: {min_income}",
        f"keywords: {keywords}",
        f"use_cases: {use_cases}",
        "---",
        ""
    ]
    
    yaml_str = "\n".join(yaml_lines)
    new_content = yaml_str + content
    
    with open(md_file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

def main():
    mapping = load_product_mapping()
    print(f"Loaded {len(mapping)} products")
    
    count = 0
    for banking_type in ["conventional", "islami"]:
        credit_dir = PRODUCTS_PATH / banking_type / "credit" / "i_need_a_credit_card"
        
        if not credit_dir.exists():
            print(f"Directory not found: {credit_dir}")
            continue
        
        for md_file in sorted(credit_dir.glob("*.md")):
            file_key = md_file.stem.lower()
            
            if file_key in mapping:
                product_data, btype = mapping[file_key]
                if add_yaml_to_file(str(md_file), product_data, btype):
                    print(f"✅ {md_file.name}")
                    count += 1
                else:
                    print(f"⏭️  {md_file.name} (already has frontmatter)")
            else:
                print(f"⚠️  {md_file.name} (no mapping found)")
    
    print(f"\n✓ Added frontmatter to {count} files")

if __name__ == "__main__":
    main()
