#!/bin/bash

BASE_URL="http://localhost:8000/api/chat"

echo "=================================================="
echo "TESTING INQUIRY CLASSIFIER VIA API"
echo "=================================================="
echo ""

test_query() {
    local message="$1"
    local description="$2"
    local session_id="$3"
    
    echo "Testing: $description"
    echo "Message: $message"
    echo ""
    
    response=$(curl -s -X POST "$BASE_URL" \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$message\", \"session_id\": \"$session_id\"}")
    
    echo "Response:"
    echo "$response" | jq '.' 2>/dev/null || echo "$response"
    echo ""
    echo "-------------------------------------------"
    echo ""
}

echo "GREETING TESTS"
echo "=============="
echo ""
test_query "hello" "Simple greeting" "test_greeting_1"
test_query "hi there" "Hi greeting" "test_greeting_2"
test_query "good morning" "Good morning" "test_greeting_3"
test_query "how are you?" "How are you" "test_greeting_4"
test_query "hey" "Hey greeting" "test_greeting_5"

echo ""
echo "PRODUCT INFO QUERY TESTS"
echo "========================"
echo ""
test_query "show me credit cards" "Show credit cards" "test_product_1"
test_query "what credit cards do you have?" "What cards question" "test_product_2"
test_query "list your savings accounts" "List accounts" "test_product_3"
test_query "tell me about deposit schemes" "Tell about schemes" "test_product_4"
test_query "do you have islamic cards?" "Islamic cards" "test_product_5"
test_query "show me gold credit cards" "Gold cards" "test_product_6"
test_query "compare platinum cards" "Compare cards" "test_product_7"

echo ""
echo "ELIGIBILITY QUERY TESTS"
echo "======================="
echo ""
test_query "am I eligible for a credit card?" "Am I eligible" "test_eligibility_1"
test_query "can I apply for a savings account?" "Can I apply" "test_eligibility_2"
test_query "do I qualify for a deposit?" "Do I qualify" "test_eligibility_3"
test_query "will I be approved?" "Will be approved" "test_eligibility_4"
test_query "check if I can get a card" "Check if can get" "test_eligibility_5"

echo ""
echo "MIXED QUERY TESTS"
echo "================="
echo ""
test_query "I'm a freelancer, show me credit cards" "Freelancer + cards" "test_mixed_1"
test_query "I'm 28 years old, what cards can I get?" "Age + cards" "test_mixed_2"
test_query "I earn 50000 BDT, show me products" "Income + products" "test_mixed_3"
test_query "I'm a student and want savings account" "Student + account" "test_mixed_4"
test_query "I'm a business owner, am I eligible?" "Business + eligibility" "test_mixed_5"
test_query "Salaried, 35 years, show me platinum cards" "Salaried + age + tier" "test_mixed_6"

echo ""
echo "CONTEXT EXTRACTION TESTS"
echo "========================"
echo ""
test_query "I'm a 28-year-old freelancer earning 50000 BDT monthly, show me islamic credit cards" "Full context" "test_context_1"
test_query "Student from university, can I get a savings account?" "Student + eligibility" "test_context_2"
test_query "Business owner, 35 years, income 150000/month, what deposit schemes?" "Business + full data" "test_context_3"
test_query "Show me cards with international travel and lounge benefits" "Benefits focus" "test_context_4"
test_query "What accounts give monthly income scheme?" "Scheme search" "test_context_5"

echo ""
echo "EDGE CASES"
echo "=========="
echo ""
test_query "" "Empty message" "test_edge_1"
test_query "??!!!" "Punctuation only" "test_edge_2"
test_query "123456789" "Numbers only" "test_edge_3"
test_query "abcdefghijk" "Gibberish" "test_edge_4"

echo ""
echo "SEQUENTIAL CONVERSATION"
echo "======================="
echo ""
echo "Testing stateful conversation with same session..."
echo ""

session="test_conversation"

echo "Message 1: Hello"
test_query "hello" "Initial greeting" "$session"

echo "Message 2: Show me credit cards"
test_query "show me credit cards" "Product query after greeting" "$session"

echo "Message 3: I'm a freelancer"
test_query "I'm a freelancer" "Providing context" "$session"

echo ""
echo "=================================================="
echo "TEST COMPLETE"
echo "=================================================="
