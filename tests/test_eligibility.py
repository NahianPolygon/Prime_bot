import pytest
from app.core.eligibility import EligibilityChecker, UserProfile


@pytest.fixture
def checker():
    return EligibilityChecker()


@pytest.fixture
def young_student():
    return UserProfile(
        age=16,
        monthly_income=10000,
        tenure_months=0
    )


@pytest.fixture
def working_professional():
    return UserProfile(
        age=28,
        monthly_income=150000,
        tenure_months=12
    )


@pytest.fixture
def high_earner():
    return UserProfile(
        age=35,
        monthly_income=250000,
        tenure_months=36
    )


class TestEligibilityChecker:
    def test_prime_first_account_eligible(self, checker, young_student):
        result = checker.check("prime_first_account", young_student)
        assert result.eligible
        assert result.confidence > 0

    def test_credit_card_ineligible_age(self, checker, young_student):
        result = checker.check("visa_gold_credit_card", young_student)
        assert not result.eligible
        assert any("age" in r.lower() for r in result.reasons)

    def test_credit_card_eligible_professional(self, checker, working_professional):
        result = checker.check("visa_gold_credit_card", working_professional)
        assert result.eligible

    def test_platinum_ineligible_income(self, checker, working_professional):
        result = checker.check("visa_platinum_credit_card", working_professional)
        assert not result.eligible
        assert any("income" in r.lower() for r in result.reasons)

    def test_platinum_eligible_high_earner(self, checker, high_earner):
        result = checker.check("visa_platinum_credit_card", high_earner)
        assert result.eligible

    def test_islamic_products_eligible(self, checker, high_earner):
        result = checker.check("visa_hasanah_platinum_credit_card", high_earner)
        assert result.eligible

    def test_nonexistent_product(self, checker, working_professional):
        result = checker.check("fake_product", working_professional)
        assert not result.eligible
        assert "not found" in result.reasons[0].lower()

    def test_recommendations(self, checker, working_professional):
        recommendations = checker.recommend_products(working_professional, limit=3)
        assert len(recommendations) > 0
        assert all(isinstance(r, str) for r in recommendations)

    def test_multiple_products(self, checker, high_earner):
        products = ["visa_gold_credit_card", "visa_platinum_credit_card", "mastercard_world_credit_card"]
        results = checker.check_multiple(products, high_earner)
        assert all(key in results for key in products)

    def test_suggestions_for_ineligible(self, checker, young_student):
        result = checker.check("visa_platinum_credit_card", young_student)
        assert len(result.suggestions) > 0
        assert any("age" in s.lower() or "18" in s for s in result.suggestions)

    def test_salary_account_tenure_requirement(self, checker):
        new_hire = UserProfile(
            age=25,
            monthly_income=100000,
            tenure_months=2,
            employment_type="salaried"
        )
        result = checker.check("prime_salary_account", new_hire)
        assert not result.eligible
        assert any("tenure" in r.lower() for r in result.reasons)

    def test_confidence_score(self, checker, high_earner):
        result = checker.check("visa_platinum_credit_card", high_earner)
        assert 0 <= result.confidence <= 1.0
        assert result.confidence > 0.5
