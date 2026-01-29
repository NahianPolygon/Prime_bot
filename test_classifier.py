from app.services.inquiry_classifier import InquiryClassifier

test_cases = [
    ("hello", "GREETING"),
    ("hi there", "GREETING"),
    ("good morning", "GREETING"),
    ("hey", "GREETING"),
    ("how are you?", "GREETING"),
    ("what's up", "GREETING"),
    
    ("show me credit cards", "PRODUCT_INFO_QUERY"),
    ("what credit cards do you have?", "PRODUCT_INFO_QUERY"),
    ("list your savings accounts", "PRODUCT_INFO_QUERY"),
    ("tell me about deposit schemes", "PRODUCT_INFO_QUERY"),
    ("do you have islamic cards?", "PRODUCT_INFO_QUERY"),
    ("what are your products?", "PRODUCT_INFO_QUERY"),
    ("show me gold credit cards", "PRODUCT_INFO_QUERY"),
    ("compare platinum cards", "PRODUCT_INFO_QUERY"),
    
    ("am I eligible for a credit card?", "ELIGIBILITY_QUERY"),
    ("can I apply for a savings account?", "ELIGIBILITY_QUERY"),
    ("do I qualify for a deposit?", "ELIGIBILITY_QUERY"),
    ("will I be approved?", "ELIGIBILITY_QUERY"),
    ("check if I can get a card", "ELIGIBILITY_QUERY"),
    
    ("I'm a freelancer, show me credit cards", "MIXED_QUERY"),
    ("I'm 28, what cards can I get?", "MIXED_QUERY"),
    ("I earn 50000 BDT, show me products", "MIXED_QUERY"),
    ("I'm a student and want savings account", "MIXED_QUERY"),
    ("I'm a business owner, am I eligible?", "MIXED_QUERY"),
]

print("\n" + "="*80)
print("INQUIRY CLASSIFIER TEST SUITE")
print("="*80 + "\n")

passed = 0
failed = 0
context_samples = []

for message, expected_type in test_cases:
    result = InquiryClassifier.classify(message)
    status = "✅ PASS" if result.inquiry_type == expected_type else "❌ FAIL"
    
    if result.inquiry_type == expected_type:
        passed += 1
    else:
        failed += 1
    
    print(f"{status} | Type: {result.inquiry_type:20} | Confidence: {result.confidence:.2f} | Message: {message}")
    
    if result.extracted_context.age or result.extracted_context.income or result.extracted_context.employment or result.extracted_context.banking_type:
        context_samples.append((message, result.extracted_context))

print(f"\n{'='*80}")
print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
print(f"{'='*80}\n")

if context_samples:
    print("CONTEXT EXTRACTION SAMPLES:\n")
    for msg, ctx in context_samples:
        print(f"Message: {msg}")
        print(f"  Banking Type: {ctx.banking_type}")
        print(f"  Employment: {ctx.employment}")
        print(f"  Age: {ctx.age}")
        print(f"  Income: {ctx.income}")
        print(f"  Keywords: {ctx.keywords}")
        print()

print("\nDETAILED TEST CASES WITH CONTEXT:\n")

detailed_tests = [
    "I'm a 28-year-old freelancer earning 50000 BDT monthly, show me islamic credit cards",
    "Student from university, can I get a savings account?",
    "Business owner, 35 years, income 150000/month, what deposit schemes?",
    "Retired person, want conventional account with good interest",
    "Self-employed, earning 75000 yearly, am I eligible for platinum card?",
    "I'm 22, salaried, show me gold and platinum cards with cashback",
    "Can a 18+ year old student get a credit card with you?",
    "What cards give international travel benefits?",
    "Suggest deposit schemes for 1 lakh investment",
    "I work in office, want dining and lounge benefits",
]

for message in detailed_tests:
    result = InquiryClassifier.classify(message)
    print(f"Message: {message}")
    print(f"Type: {result.inquiry_type} (confidence: {result.confidence:.2f})")
    print(f"Context:")
    print(f"  - Banking Type: {result.extracted_context.banking_type}")
    print(f"  - Employment: {result.extracted_context.employment}")
    print(f"  - Age: {result.extracted_context.age}")
    print(f"  - Income: {result.extracted_context.income}")
    print(f"  - Product Category: {result.extracted_context.product_category}")
    print(f"  - Keywords: {result.extracted_context.keywords}")
    print(f"  - Use Cases: {result.extracted_context.use_cases}")
    print()

print("\n" + "="*80)
print("EDGE CASES:")
print("="*80 + "\n")

edge_cases = [
    ("", "Empty message"),
    ("   ", "Whitespace only"),
    ("??!!!", "Punctuation only"),
    ("asdfghjkl", "Gibberish"),
    ("123456789", "Numbers only"),
]

for message, description in edge_cases:
    result = InquiryClassifier.classify(message)
    print(f"{description:25} | Type: {result.inquiry_type:20} | Confidence: {result.confidence:.2f}")

print("\n" + "="*80)
