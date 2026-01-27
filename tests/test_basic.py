import pytest
from pathlib import Path
import json


class TestKnowledgeBase:
    def test_credit_cards_json_valid(self):
        path = Path(__file__).parent.parent / "app" / "knowledge" / "structured" / "conventional" / "credit_cards.json"
        
        with open(path) as f:
            data = json.load(f)
        
        assert "credit_cards_conventional" in data
        assert len(data["credit_cards_conventional"]) == 6

    def test_islami_credit_cards_json_valid(self):
        path = Path(__file__).parent.parent / "app" / "knowledge" / "structured" / "islami" / "credit_cards.json"
        
        with open(path) as f:
            data = json.load(f)
        
        assert "credit_cards_islamic" in data
        assert len(data["credit_cards_islamic"]) == 2


class TestModels:
    def test_intent_result_validation(self):
        from app.models.intent import IntentResult, BankingType, VerticalType

        intent = IntentResult(
            domain=BankingType.CONVENTIONAL,
            vertical=VerticalType.CREDIT,
            confidence=0.92
        )
        
        assert intent.domain == BankingType.CONVENTIONAL
        assert intent.confidence == 0.92

    def test_chat_request_validation(self):
        from app.models.intent import ChatRequest

        request = ChatRequest(
            session_id="test_123",
            user_message="Show me credit cards",
            channel="web"
        )
        
        assert request.session_id == "test_123"
        assert request.channel == "web"
        assert request.language == "en"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
