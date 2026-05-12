# PrimeBot QA Report

Date: 2026-05-11

Scope: representative full-pipeline tests against the current Prime Bank markdown and Chroma runtime. The report is grouped by what the bot can answer properly and what is currently unreliable.

## Summary

- Tested 20 representative cases across catalog, product details, comparison, application, cardholder services, calculators, recommendation form, and eligibility form.
- Clearly working: catalog, product details, comparison, deterministic calculators, preference form, eligibility form.
- Partially working: application/how-to-apply and existing-cardholder services.
- Needs fixing: greeting behavior and complete service/document answers.

## What Works Properly

### Catalog And Card Listing

Passed:

- "What credit cards does Prime Bank offer?"
- "Show me conventional credit cards"
- "Show Islamic / Halal cards"

The bot correctly lists the Prime Bank cards and separates conventional vs Islamic cards.

### Product Details

Passed:

- "Tell me the main benefits of Mastercard World Credit Card"

The bot returned correct key facts including 2 points per BDT 50, LoungeKey, BOGO dining, Balaka VIP, insurance, and airport welcome.

### Comparison

Passed:

- "Compare Mastercard World Credit Card and JCB Platinum Credit Card"

The bot produced a usable comparison table with both requested cards and important features.

### Fee Waiver

Passed:

- "What is the annual fee waiver condition for Mastercard World Credit Card?"

The bot returned: annual fee waiver on 15 purchases.

### Calculations

Passed:

- Mastercard World BDT 75,000/month reward points: 36,000 points/year.
- Mastercard World BDT 200,000/month to 48,000 points: 6 months.
- JCB Platinum BDT 500,000 over 36-month EMI: BDT 13,889.
- JCB Gold March 15 statement plus 50-day interest-free period: May 4.
- JCB Gold BDT 80,000 missed due date at 1.5% monthly interest: BDT 1,200.
- JCB Platinum BOGO 3 times/month at BDT 3,500: BDT 126,000/year.

These are strong because they now use deterministic calculation logic instead of trusting the LLM to do arithmetic.

### Recommendation Form

Passed:

- "I need a credit card for travel"

The bot correctly triggers the preference form.

### Eligibility Form

Passed:

- "Check eligibility for Mastercard World Credit Card"

The bot correctly triggers the eligibility form with Mastercard World as the target card.

## What Works Partially

### How To Apply

Tested:

- "How do I apply for JCB Gold Credit Card?"

Result:

- The bot gives a usable application flow.
- It missed some detailed requirements from the markdown, such as E-TIN and salaried/self-employed requirements.

Verdict: usable but not complete enough for document-requirement questions.

### Lost Card

Tested:

- "I lost my JCB Gold card. What should I do?"

Result:

- The bot correctly says to call 16218 immediately and block the card.
- The automated test marked it as failed only because the final response did not literally include the word "lost".

Verdict: semantically okay.

### Bill Payment

Tested:

- "How can I pay my credit card bill?"

Result:

- The bot mentions MyPrime, branch, and internet banking.
- It missed Auto Debit, even though that type of payment option exists in the card documents.

Verdict: partially reliable but incomplete.

### Dispute

Tested:

- "How do I dispute a card transaction?"

Result:

- The bot mentions dispute and 16218.
- It does not explain the full dispute mechanism or timeline.

Verdict: weak but not completely wrong.

## What Does Not Work Properly Yet

### Greeting / Conversational Opener

Tested:

- "Hi, can you help me with cards?"

Result:

- The message was routed toward the recommendation/form path.
- In the backend text test, this produced no normal assistant text because the response was a form signal.

Verdict: needs fixing. A greeting should respond conversationally first, not jump straight into a form.

### Complete Service And Document Answers

Problem area:

- Application document requirements.
- Dispute mechanism details.
- Bill payment options.
- Existing-cardholder service answers that require complete process/detail extraction.

Verdict: not dependable enough yet for complete service FAQ answers.

## Recommended Fix Priority

1. Fix greeting routing so casual openers do not trigger forms immediately.
2. Strengthen service/document retrieval for how-to-apply, dispute, bill payment, and documents-required style answers.
3. Add deterministic extractors for common service facts, similar to the calculation layer.
4. Add a persistent regression test suite so these 20 cases can be rerun after every change.
