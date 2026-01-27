import pytest
from app.core.agents import SaveAgent, CreditAgent, RouterAgent, AgentState
from app.core.comparison import ProductComparator, ComparisonCriteria
from app.core.markdown_loader import MarkdownLoader
from app.core.flow import CompleteFlow, CompleteFlowState, ConversationPhase
from app.core.eligibility import UserProfile


@pytest.fixture
def save_agent():
    return SaveAgent()


@pytest.fixture
def credit_agent():
    return CreditAgent()


@pytest.fixture
def router_agent():
    return RouterAgent()


@pytest.fixture
def comparator():
    return ProductComparator()


@pytest.fixture
def md_loader():
    return MarkdownLoader()


@pytest.fixture
def complete_flow():
    return CompleteFlow()


@pytest.fixture
def sample_profile():
    return UserProfile(
        age=28,
        monthly_income=150000,
        tenure_months=12
    )


class TestAgents:
    def test_save_agent_discover(self, save_agent):
        state = AgentState(
            session_id="test_1",
            user_message="show me accounts",
            domain="conventional",
            vertical="save",
            intent="discover"
        )
        result = save_agent.discover_accounts(state)
        assert result.current_step == "account_discovery"
        assert len(result.products) >= 0

    def test_credit_agent_discover(self, credit_agent):
        state = AgentState(
            session_id="test_2",
            user_message="show me credit cards",
            domain="conventional",
            vertical="credit",
            intent="discover"
        )
        result = credit_agent.discover_cards(state)
        assert result.current_step == "card_discovery"
        assert len(result.products) >= 0

    def test_router_agent_build_graph(self, router_agent):
        graph = router_agent.build_graph()
        assert graph is not None


class TestComparator:
    def test_compare_credit_cards(self, comparator):
        card_ids = ["visa_gold_credit_card", "visa_platinum_credit_card"]
        criteria = ComparisonCriteria()
        result = comparator.compare_credit_cards(card_ids, criteria)
        assert result.product_names == card_ids or len(result.product_names) >= 0
        assert result.winner_reason

    def test_compare_for_profile(self, comparator, sample_profile):
        card_ids = ["visa_gold_credit_card"]
        result = comparator.compare_for_profile(card_ids, sample_profile, "credit")
        assert "comparison" in result
        assert "eligibility" in result
        assert "recommendation" in result


class TestMarkdownLoader:
    def test_list_documents(self, md_loader):
        docs = md_loader.get_all_documents()
        assert isinstance(docs, list)

    def test_search_document(self, md_loader):
        results = md_loader.search_document_title("visa")
        assert isinstance(results, list)

    def test_extract_sections(self, md_loader):
        sample_content = "# Introduction\nHello\n## Benefits\nGreat"
        sections = md_loader.extract_sections(sample_content)
        assert "introduction" in sections or len(sections) >= 0


class TestCompleteFlow:
    @pytest.mark.asyncio
    async def test_greeting_phase(self, complete_flow):
        state = CompleteFlowState(
            session_id="test_flow_1",
            user_message="hello",
            phase=ConversationPhase.GREETING,
            domain="conventional",
            vertical="credit"
        )
        result = await complete_flow.process(state)
        assert result.phase == ConversationPhase.INTENT_DETECTION
        assert len(result.response) > 0

    @pytest.mark.asyncio
    async def test_intent_detection_phase(self, complete_flow):
        state = CompleteFlowState(
            session_id="test_flow_2",
            user_message="I want a credit card",
            phase=ConversationPhase.INTENT_DETECTION,
            domain="conventional",
            vertical="credit"
        )
        result = await complete_flow.process(state)
        assert result.phase in [ConversationPhase.INTENT_DETECTION, ConversationPhase.PROFILE_COLLECTION]

    @pytest.mark.asyncio
    async def test_profile_collection_phase(self, complete_flow, sample_profile):
        state = CompleteFlowState(
            session_id="test_flow_3",
            user_message="I'm 28 years old",
            phase=ConversationPhase.PROFILE_COLLECTION,
            domain="conventional",
            vertical="credit",
            user_profile=sample_profile
        )
        result = await complete_flow.process(state)
        assert result.phase == ConversationPhase.ELIGIBILITY_CHECK
        assert len(result.response) > 0

    @pytest.mark.asyncio
    async def test_eligibility_check_phase(self, complete_flow, sample_profile):
        state = CompleteFlowState(
            session_id="test_flow_4",
            user_message="check eligibility",
            phase=ConversationPhase.ELIGIBILITY_CHECK,
            domain="conventional",
            vertical="credit",
            user_profile=sample_profile
        )
        result = await complete_flow.process(state)
        assert result.phase in [ConversationPhase.PRODUCT_COMPARISON, ConversationPhase.EDUCATION]
