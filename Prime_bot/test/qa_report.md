# PrimeBot QA Report

Date: 2026-05-12

Scope: unified full-pipeline QA against the current Prime Bank markdown and active Chroma-backed runtime. This report keeps all previously tested cases and adds a fresh Prime Bank-only pass with new prompts. Total reviewed coverage in the enumerated case inventory: 26 representative checks across catalog, product details, comparison, application, cardholder services, deterministic math, recommendation, eligibility, and premium-benefit FAQ.

## Executive Summary

- Reliable now: catalog listing, card detail lookup, comparison, fee-waiver lookup, deterministic calculations, recommendation form, eligibility form, direct document-requirement retrieval, damaged-card handling, and MyPrime-based limit/history guidance.
- Partially reliable: open-ended how-to-apply, lost-card phrasing, bill payment completeness, dispute handling detail, and some premium-benefit edge questions.
- Still unreliable: conversational greeting/openers and exact partner-specific benefit extraction for some card perks.

## Reliable

### Catalog And Card Discovery

Pass:

- "What credit cards does Prime Bank offer?"
- "Show me conventional credit cards"
- "Show Islamic / Halal cards"

Observed behavior:

- Correctly lists Prime Bank cards.
- Correctly separates conventional and Islamic collections.

### Product Details And Comparison

Pass:

- "Tell me the main benefits of Mastercard World Credit Card"
- "Compare Mastercard World Credit Card and JCB Platinum Credit Card"

Observed behavior:

- Correctly returns Mastercard World facts including 2 points per BDT 50, LoungeKey, BOGO dining, Balaka VIP, and insurance.
- Produces a usable comparison table with the requested cards and meaningful feature differences.

### Fee Conditions

Pass:

- "What is the annual fee waiver condition for Mastercard World Credit Card?"

Observed behavior:

- Correctly returns that fee waiver requires 15+ purchases in a year.

### Deterministic Calculations

Pass:

- Mastercard World BDT 75,000/month reward points: 36,000 points/year.
- Mastercard World BDT 200,000/month to 48,000 points: 6 months.
- JCB Platinum BDT 500,000 over 36-month EMI: BDT 13,889.
- JCB Gold March 15 statement plus 50-day interest-free period: May 4.
- JCB Gold BDT 80,000 missed due date at 1.5% monthly interest: BDT 1,200.
- JCB Platinum BOGO 3 times/month at BDT 3,500: BDT 126,000/year.
- "My Mastercard World outstanding is BDT 82,000. What minimum payment should I make this month?"
- "If I spend BDT 125,000 every month on Mastercard World for a full year, how many reward points should I earn?"

Observed behavior:

- Correctly applies formula-driven results instead of freeform LLM arithmetic.
- New Prime Bank pass correctly returned BDT 5,000 minimum payment and 60,000 annual reward points for the new cases.

### Recommendation And Eligibility Forms

Pass:

- "I need a credit card for travel"
- "Check eligibility for Mastercard World Credit Card"

Observed behavior:

- Correctly triggers the preference form for card recommendation.
- Correctly triggers the eligibility form with Mastercard World as the target card.

### Direct Application Document Retrieval

Pass:

- "For Mastercard World, list the salaried documents, self-employed documents, and say whether E-TIN is required."

Observed behavior:

- Correctly returns salaried proof, self-employed proof, and E-TIN requirement from the markdown.
- This is stronger than the older generic how-to-apply result because the query is document-specific and grounded.

### Core Existing-Cardholder Service Actions

Pass:

- "Without visiting a branch, how can I check my Prime Bank credit limit and transaction history?"
- "My Prime Bank credit card is damaged but not lost. What should I do right now?"

Observed behavior:

- Correctly routes to MyPrime for credit limit and transaction history, with internet banking as an alternative.
- Correctly instructs damaged-card users to visit the nearest Prime Bank branch for replacement.

## Partially Reliable

### Open-Ended How-To-Apply

Tested:

- "How do I apply for JCB Gold Credit Card?"

Observed behavior:

- Gives a usable application flow.
- Misses some detailed requirements such as E-TIN and the salaried/self-employed document split.

Verdict:

- Good for general process, not yet strong enough for exact document-checklist questions unless the prompt is very direct.

### Lost Card Handling

Tested:

- "I lost my JCB Gold card. What should I do?"

Observed behavior:

- Correctly tells the user to call 16218 immediately and block the card.
- Response was semantically correct, but earlier automated wording checks were stricter than the answer wording.

Verdict:

- Operationally usable.

### Bill Payment

Tested:

- "How can I pay my credit card bill?"

Observed behavior:

- Mentions MyPrime, branch, and internet banking.
- Does not consistently include every possible payment path.

Verdict:

- Useful, but still incomplete for comprehensive bill-payment FAQ coverage.

### Dispute Handling

Tested:

- "How do I dispute a card transaction?"

Observed behavior:

- Mentions dispute handling and 16218.
- Does not consistently explain the full process or timeline.

Verdict:

- Directionally correct, but not detailed enough.

### Premium Benefit Edge Cases

Tested:

- "With Mastercard World Balaka VIP, can I bring a third companion for free?"

Observed behavior:

- Answer correctly says the card includes the holder and two companions, so a third companion is not included for free.
- The answer is correct, but still terse and not as explicit as it should be for a premium-benefit FAQ.

Verdict:

- Semantically correct, but could be clearer and more benefit-specific.

## Unreliable Or Failing

### Greeting / Conversational Opener

Tested:

- "Hi, can you help me with cards?"

Observed behavior:

- Earlier run routed the message toward form behavior instead of replying conversationally first.

Verdict:

- Still not dependable until revalidated with a conversationally clean response.

### Exact Partner-Specific Premium Benefit Extraction

Tested:

- "Can I use Visa Platinum BOGO at any restaurant, or only at specific partners?"

Observed behavior:

- Returns that BOGO is available at premium restaurants.
- Does not reliably surface the exact partner list from the markdown, even though the card file contains the specific hotels/restaurants.

Verdict:

- Not dependable yet for exact partner-name questions.

### Fully Detailed Service / Process FAQ

Problem area:

- Complete dispute mechanism.
- Full bill-payment option coverage.
- Precise partner lists or detailed process answers that require pulling exact service sub-details from the markdown.

Verdict:

- These still need stronger retrieval and answer assembly to be production-safe.

## Case Inventory

Reliable cases:

- "What credit cards does Prime Bank offer?"
- "Show me conventional credit cards"
- "Show Islamic / Halal cards"
- "Tell me the main benefits of Mastercard World Credit Card"
- "Compare Mastercard World Credit Card and JCB Platinum Credit Card"
- "What is the annual fee waiver condition for Mastercard World Credit Card?"
- Mastercard World BDT 75,000/month reward points
- Mastercard World BDT 200,000/month to 48,000 points
- JCB Platinum BDT 500,000 over 36-month EMI
- JCB Gold March 15 statement plus 50-day interest-free period
- JCB Gold BDT 80,000 missed due date at 1.5% monthly interest
- JCB Platinum BOGO 3 times/month at BDT 3,500
- "I need a credit card for travel"
- "Check eligibility for Mastercard World Credit Card"
- "For Mastercard World, list the salaried documents, self-employed documents, and say whether E-TIN is required."
- "My Mastercard World outstanding is BDT 82,000. What minimum payment should I make this month?"
- "If I spend BDT 125,000 every month on Mastercard World for a full year, how many reward points should I earn?"
- "Without visiting a branch, how can I check my Prime Bank credit limit and transaction history?"
- "My Prime Bank credit card is damaged but not lost. What should I do right now?"

Partially reliable cases:

- "How do I apply for JCB Gold Credit Card?"
- "I lost my JCB Gold card. What should I do?"
- "How can I pay my credit card bill?"
- "How do I dispute a card transaction?"
- "With Mastercard World Balaka VIP, can I bring a third companion for free?"

Unreliable or failing cases:

- "Hi, can you help me with cards?"
- "Can I use Visa Platinum BOGO at any restaurant, or only at specific partners?"

## Recommended Fix Priority

1. Fix conversational greeting handling so simple openers do not jump straight into form behavior.
2. Improve exact benefit retrieval for partner lists, companion rules, and premium entitlement details.
3. Strengthen service/process synthesis for dispute steps, bill payment completeness, and complete application-document answers.
4. Keep rerunning this unified case set after every retrieval or prompting change.
