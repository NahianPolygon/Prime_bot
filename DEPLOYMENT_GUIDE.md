# Integration Guide: Deploying Pattern-Based Optimization

## Pre-Deployment Verification

### 1. Code Structure Check
```bash
find app/services -name "inquiry_classifier.py"
find tests -name "test_inquiry_classifier.py"
find documentation -name "PATTERN_CLASSIFICATION_OPTIMIZATION.md"
```

### 2. Verify Deleted Files
```bash
ls app/prompts/conversation_manager/inquiry_type.py  # Should NOT exist
echo $?  # Should return 1 (file not found)
```

### 3. Verify Modified Files
```bash
grep -l "InquiryClassifier" app/core/graphs/conversation_manager.py
grep -l "from app.services.inquiry_classifier" app/core/graphs/conversation_manager.py
```

## Running Tests

### Unit Tests
```bash
pytest tests/test_inquiry_classifier.py -v
pytest tests/test_inquiry_classifier.py::TestGreetingDetection -v
pytest tests/test_inquiry_classifier.py::TestProductInfoQuery -v
pytest tests/test_inquiry_classifier.py::TestEligibilityQuery -v
pytest tests/test_inquiry_classifier.py::TestMixedQuery -v
pytest tests/test_inquiry_classifier.py::TestContextExtraction -v
pytest tests/test_inquiry_classifier.py::TestEdgeCases -v
```

### Coverage Report
```bash
pytest tests/test_inquiry_classifier.py --cov=app.services.inquiry_classifier --cov-report=html
```

### Integration Tests
```bash
pytest tests/ -v -k "conversation_manager or chat"
```

## Manual Testing

### Setup
```bash
cd /mnt/sda1/Polygon/Prime_bot
docker-compose up -d
sleep 10
curl http://localhost:8000/health
```

### Test Cases

#### 1. Simple Greeting
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "hello", "session_id": "test_greeting"}'

# Expected: Greeting response generated via LLM
# Check logs for: "⚡ [CLASSIFY_INQUIRY] Pattern-based classification"
```

#### 2. Product Query
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "show me credit cards", "session_id": "test_product"}'

# Expected: Product list
# Check logs for: "inquiry_type: PRODUCT_INFO_QUERY"
```

#### 3. Eligibility Query
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "am I eligible for a credit card?", "session_id": "test_eligibility"}'

# Expected: Eligibility assessment flow
# Check logs for: "inquiry_type: ELIGIBILITY_QUERY"
```

#### 4. Mixed Query
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I earn 50000 BDT, show me credit cards", "session_id": "test_mixed"}'

# Expected: Mixed query handling
# Check logs for: "inquiry_type: MIXED_QUERY"
```

#### 5. Complex Extraction
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I am 28 years old, freelancer, want islamic platinum credit cards", "session_id": "test_complex"}'

# Expected: All context extracted
# Check logs for:
#   - age: 28
#   - employment: freelancer
#   - banking_type: islami
#   - keywords: ["platinum", "credit card"]
```

## Performance Verification

### Before Optimization
Typical response time for product query: 174+ seconds

### After Optimization
Expected response times:
- Greeting: 500-800ms (LLM only)
- Product Query: 300-600ms (pattern match + filter + LLM format)
- Eligibility Query: 2-4 seconds (pattern match + slot collection)
- Mixed Query: 1-3 seconds (pattern match + routing)

### Measuring Performance
```bash
# Using time command
time curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "show me credit cards", "session_id": "perf_test"}'

# Using curl with time metrics
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "show me credit cards", "session_id": "perf_test"}' \
  -w "\nTime: %{time_total}s\n"

# Check Docker logs
docker logs prime_bot_app | grep "CLASSIFY_INQUIRY"
```

## Monitoring

### Log Lines to Check

Pattern match speed:
```
⚡ [CLASSIFY_INQUIRY] Pattern-based classification (fast)
✅ [CLASSIFY_INQUIRY] Type: PRODUCT_INFO_QUERY, Confidence: 0.85
```

Greeting generation:
```
[CLASSIFY_INQUIRY] Type: GREETING
```

Product filtering:
```
🎯 [PRODUCT_MATCHER] Starting product matching
✅ [PRODUCT_MATCHER] Matched X products after filtering
```

### Metrics to Track

1. **Classification Speed** (should be <20ms)
   - Before: 174,000ms
   - After: <20ms

2. **Total Response Time**
   - Before: 174s+ (including network)
   - After: <1s for fast path

3. **LLM Calls Per Request**
   - Before: 2+ calls (inquiry + response)
   - After: 0-1 calls (only response)

4. **API Cost Reduction**
   - Estimated: 40-50% reduction in API calls
   - Gemini tokens saved: 50-100 per request

## Rollback Plan

If issues occur:

### Option 1: Quick Revert
```bash
git checkout HEAD~1 app/core/graphs/conversation_manager.py
docker-compose down
docker-compose up -d
```

### Option 2: Hybrid Mode (Fallback)
Keep both classifiers, use LLM as fallback:
```python
classification = InquiryClassifier.classify(message)
if classification.confidence < 0.5:
    classification = self.product_matcher.classify_inquiry_type_llm(message)
```

## Post-Deployment

### Day 1
- Monitor error logs
- Check response times in LangFuse
- Verify accuracy of classification
- Monitor token usage

### Week 1
- Collect 1000+ sample classifications
- Analyze misclassifications
- Refine patterns if needed
- Compare costs with baseline

### Ongoing
- Monthly pattern review
- Update keywords based on user queries
- Monitor confidence scores
- Adjust thresholds if needed

## Troubleshooting

### Issue: Classifications seem wrong
Check logs for extracted context:
```bash
docker logs prime_bot_app | grep "Filter start"
```

### Issue: Response time not improved
Check if LLM is still being called:
```bash
docker logs prime_bot_app | grep "Pattern-based"
```

### Issue: Greetings not being detected
Test classifier directly:
```python
from app.services.inquiry_classifier import InquiryClassifier
result = InquiryClassifier.classify("hello")
print(result)
```

## Success Criteria

✅ All tests passing
✅ Classification time <20ms
✅ Total response time <2s for product queries
✅ Greeting responses generated correctly
✅ Eligibility flow works as before
✅ No increase in error rates
✅ Cost reduction visible in metrics

## Support

If issues arise:
1. Check IMPLEMENTATION_COMPLETE.md
2. Review PATTERN_CLASSIFICATION_OPTIMIZATION.md
3. Run test_inquiry_classifier.py
4. Check conversation_manager logs
5. Review extracted_context in state
