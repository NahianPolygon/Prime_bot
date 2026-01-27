from openai import AsyncOpenAI
from app.core.config import settings
from app.prompts import (
    INTENT_DETECTION_PROMPT,
    ELIGIBILITY_CHECK_PROMPT,
    PRODUCT_COMPARISON_PROMPT,
    PRODUCT_EXPLANATION_PROMPT,
    RESPONSE_GENERATION_PROMPT,
)
import json

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def detect_intent(message: str) -> dict:
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a banking intent classifier. Always respond with valid JSON only."
            },
            {
                "role": "user",
                "content": INTENT_DETECTION_PROMPT.format(message=message)
            }
        ],
        temperature=0.3,
    )
    
    content = response.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON response: {content}")


async def check_eligibility(age: int, employment: str, income: float, banking_type: str, products: list, message: str) -> dict:
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a banking eligibility expert. Always respond with valid JSON only."
            },
            {
                "role": "user",
                "content": ELIGIBILITY_CHECK_PROMPT.format(
                    age=age,
                    employment_type=employment,
                    monthly_income=income,
                    banking_type=banking_type,
                    message=message,
                    products=json.dumps(products[:5])
                )
            }
        ],
        temperature=0.2,
    )
    
    content = response.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON response: {content}")


async def compare_products(age: int, income: float, employment: str, banking_type: str, products: list, priority: str) -> dict:
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a product comparison expert. Always respond with valid JSON only."
            },
            {
                "role": "user",
                "content": PRODUCT_COMPARISON_PROMPT.format(
                    age=age,
                    monthly_income=income,
                    employment_type=employment,
                    banking_type=banking_type,
                    products_json=json.dumps(products[:5]),
                    priority=priority
                )
            }
        ],
        temperature=0.3,
    )
    
    content = response.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON response: {content}")


async def explain_product(product_data: dict, age: int, employment: str, banking_type: str) -> dict:
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a product expert. Always respond with valid JSON only."
            },
            {
                "role": "user",
                "content": PRODUCT_EXPLANATION_PROMPT.format(
                    product_data=json.dumps(product_data),
                    age=age,
                    employment_type=employment,
                    banking_type=banking_type
                )
            }
        ],
        temperature=0.3,
    )
    
    content = response.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON response: {content}")


async def generate_response(intent: str, domain: str, age: int, employment: str, message: str, knowledge_context: str, conversation_history: list) -> str:
    recent_context = "; ".join([f"{h['role']}: {h['content'][:50]}" for h in conversation_history[-3:]])
    
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are Prime Bank's helpful assistant. Generate conversational responses, not JSON."
            },
            {
                "role": "user",
                "content": RESPONSE_GENERATION_PROMPT.format(
                    intent=intent,
                    domain=domain,
                    age=age,
                    employment_type=employment,
                    context=recent_context,
                    user_message=message,
                    knowledge_context=knowledge_context
                )
            }
        ],
        temperature=0.7,
    )
    
    return response.choices[0].message.content.strip()
