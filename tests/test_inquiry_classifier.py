import pytest
from app.services.inquiry_classifier import InquiryClassifier


class TestGreetingDetection:
    
    def test_simple_hello(self):
        result = InquiryClassifier.classify("hello")
        assert result.inquiry_type == "GREETING"
        assert result.confidence >= 0.9
    
    def test_good_morning(self):
        result = InquiryClassifier.classify("good morning")
        assert result.inquiry_type == "GREETING"
    
    def test_how_are_you(self):
        result = InquiryClassifier.classify("how are you?")
        assert result.inquiry_type == "GREETING"
    
    def test_hey(self):
        result = InquiryClassifier.classify("hey there")
        assert result.inquiry_type == "GREETING"


class TestProductInfoQuery:
    
    def test_show_me_credit_cards(self):
        result = InquiryClassifier.classify("show me credit cards")
        assert result.inquiry_type == "PRODUCT_INFO_QUERY"
        assert result.confidence >= 0.7
        assert "credit card" in result.extracted_context.keywords
    
    def test_what_cards_do_you_have(self):
        result = InquiryClassifier.classify("what credit cards do you have?")
        assert result.inquiry_type == "PRODUCT_INFO_QUERY"
    
    def test_list_savings_accounts(self):
        result = InquiryClassifier.classify("list your savings accounts")
        assert result.inquiry_type == "PRODUCT_INFO_QUERY"
    
    def test_islamic_cards(self):
        result = InquiryClassifier.classify("show me islamic credit cards")
        assert result.inquiry_type == "PRODUCT_INFO_QUERY"
        assert result.extracted_context.banking_type == "islami"
    
    def test_gold_card(self):
        result = InquiryClassifier.classify("what gold credit cards do you have?")
        assert result.inquiry_type == "PRODUCT_INFO_QUERY"
        assert "gold" in result.extracted_context.keywords


class TestEligibilityQuery:
    
    def test_am_i_eligible(self):
        result = InquiryClassifier.classify("am I eligible for a credit card?")
        assert result.inquiry_type == "ELIGIBILITY_QUERY"
    
    def test_can_i_apply(self):
        result = InquiryClassifier.classify("can I apply for a savings account?")
        assert result.inquiry_type == "ELIGIBILITY_QUERY"
    
    def test_do_i_qualify(self):
        result = InquiryClassifier.classify("do I qualify?")
        assert result.inquiry_type == "ELIGIBILITY_QUERY"
    
    def test_will_i_be_approved(self):
        result = InquiryClassifier.classify("will I be approved?")
        assert result.inquiry_type == "ELIGIBILITY_QUERY"


class TestMixedQuery:
    
    def test_freelancer_wants_cards(self):
        result = InquiryClassifier.classify("I'm a freelancer, show me credit cards")
        assert result.inquiry_type == "MIXED_QUERY"
        assert result.extracted_context.employment == "freelancer"
        assert "credit card" in result.extracted_context.keywords
    
    def test_age_with_card_query(self):
        result = InquiryClassifier.classify("I'm 25 years old, what credit cards can I get?")
        assert result.inquiry_type == "MIXED_QUERY"
        assert result.extracted_context.age == 25
    
    def test_income_with_product_query(self):
        result = InquiryClassifier.classify("I earn 50000 BDT monthly, show me investment products")
        assert result.inquiry_type == "MIXED_QUERY"
        assert result.extracted_context.income == 50000


class TestContextExtraction:
    
    def test_extract_employment_salaried(self):
        result = InquiryClassifier.classify("I'm salaried, am I eligible?")
        assert result.extracted_context.employment == "salaried"
    
    def test_extract_employment_student(self):
        result = InquiryClassifier.classify("I'm a student, can I get a card?")
        assert result.extracted_context.employment == "student"
    
    def test_extract_employment_business_owner(self):
        result = InquiryClassifier.classify("I'm a business owner, what accounts do you have?")
        assert result.extracted_context.employment == "business_owner"
    
    def test_extract_banking_type_conventional(self):
        result = InquiryClassifier.classify("show me conventional credit cards")
        assert result.extracted_context.banking_type == "conventional"
    
    def test_extract_banking_type_islami(self):
        result = InquiryClassifier.classify("I want islami deposit accounts")
        assert result.extracted_context.banking_type == "islami"
    
    def test_extract_age(self):
        result = InquiryClassifier.classify("I'm 28 years old")
        assert result.extracted_context.age == 28
    
    def test_extract_income(self):
        result = InquiryClassifier.classify("I earn 75000 taka per month")
        assert result.extracted_context.income == 75000
    
    def test_extract_income_with_commas(self):
        result = InquiryClassifier.classify("monthly income is 1,50,000 tk")
        assert result.extracted_context.income == 150000


class TestEdgeCases:
    
    def test_empty_message(self):
        result = InquiryClassifier.classify("")
        assert result.inquiry_type in ["GREETING", "ELIGIBILITY_QUERY", "PRODUCT_INFO_QUERY"]
    
    def test_whitespace_only(self):
        result = InquiryClassifier.classify("   ")
        assert result.inquiry_type is not None
    
    def test_case_insensitive(self):
        result1 = InquiryClassifier.classify("HELLO")
        result2 = InquiryClassifier.classify("hello")
        assert result1.inquiry_type == result2.inquiry_type == "GREETING"
    
    def test_multiple_keywords(self):
        result = InquiryClassifier.classify("show me platinum credit cards with cashback")
        assert "platinum" in result.extracted_context.keywords
        assert "cashback" in result.extracted_context.keywords
