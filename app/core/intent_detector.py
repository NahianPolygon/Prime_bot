import json
from openai import AsyncOpenAI
from app.models.intent import IntentResult, BankingType, VerticalType, IntentType
from app.core.config import settings
from app.prompts import INTENT_DETECTION_PROMPT

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


class IntentDetector:
    async def detect(self, user_message: str) -> IntentResult:
        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a banking intent classifier. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": INTENT_DETECTION_PROMPT.format(message=user_message)
                    }
                ],
                temperature=0.3,
            )

            content = response.choices[0].message.content.strip()
            data = json.loads(content)

            return IntentResult(
                domain=data.get("domain"),
                vertical=data.get("vertical"),
                intent_type=data.get("intent_type"),
                confidence=float(data.get("confidence", 0.0)),
                extracted_entities=data.get("extracted_entities", {})
            )

        except Exception as e:
            return IntentResult(
                confidence=0.0,
                extracted_entities={}
            )
