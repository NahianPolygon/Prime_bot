EXTRACT_SLOT_PROMPT = """Extract and validate user response for {slot_name} from message.

Message: {user_message}
Expected type: {slot_type}

Valid values:
- age: numeric 18-100
- income: numeric amount in BDT
- deposit: numeric amount in BDT
- employment_type: salaried, self-employed, business
- banking_type: conventional, islami
- product_category: deposit, credit, investment

Return JSON with extracted_value, confidence, and is_valid."""
