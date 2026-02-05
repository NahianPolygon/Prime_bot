"""Product comparison prompts."""

EXTRACT_PRODUCT_MENTIONS_PROMPT = """Extract EXACT product mentions from this user comparison request.

User message: "{user_message}"

RULES:
1. PRIORITIZE specific product names (e.g., "Prime Hasanah Term Deposit", "Prime FD Plus", "JCB Platinum")
2. Extract EXACT names as mentioned by user - do NOT generalize
3. If user mentions "savings accounts" but also mentions specific products, extract the specific products
4. If user ONLY mentions generic types like "savings accounts", extract that as fallback

Return a JSON object with:
- mentioned_products: list of EXACT product names/types user wants to compare
- comparison_intent: boolean - is this clearly a comparison request?
- confidence: 0.0-1.0 how confident you are
- reasoning: brief explanation

Examples:
- "compare Prime Hasanah Term Deposit and Prime Hasanah Savings Account" → mentioned_products: ["Prime Hasanah Term Deposit", "Prime Hasanah Savings Account"]
- "which is better - teacher account or youth account?" → mentioned_products: ["teacher account", "youth account"]
- "show me two deposit products" → mentioned_products: ["deposit"], comparison_intent: true
- "FD vs savings" → mentioned_products: ["FD", "savings account"]

Return ONLY valid JSON, no markdown or extra text."""

CLARIFY_PRODUCTS_PROMPT = """The user wants to compare banking products but their request is unclear.

User message: "{user_message}"
User context:
- Age: {age}
- Occupation: {occupation}
- Banking preference: {banking_type}

Suggest 2-3 specific Prime Bank products that might interest them based on:
1. What they explicitly mentioned (even if vague)
2. Their profile (age, occupation, banking type)

Ask them to clarify which products they want to compare.

Be conversational and helpful, not just listing products."""

PERSONALIZED_COMPARISON_PROMPT = """You are a banking expert. Compare these {num_products} products in detail.

User's Comparison Request: "{user_message}"

User Profile:
- Age: {age}
- Occupation: {occupation}
- Banking Preference: {banking_type}
- Income: {income}
- Original Goal: {goal}

Comparison Preferences:
- Deposit Type: {deposit_frequency}
- Timeline: {tenure_range}
- Purpose: {purpose}
- Interest Priority: {interest_priority}
- Flexibility Need: {flexibility_priority}

Products to Compare:
{products_text}

Generate a comprehensive comparison that:
1. Shows 5-7 key differences between products in a clear table format
2. Highlights which features benefit THIS user most based on their profile and preferences
3. Provides a clear recommendation with reasoning
4. Uses markdown with tables for clarity

Be specific, data-driven, and personalized to their needs."""

COLLECT_BANKING_TYPE_PROMPT = """Determine which banking type to ask for.

User message: "{user_message}"
User profile: banking_type={banking_type}

If user already indicated a banking preference (Islamic or Conventional), note it.
Otherwise, ask: "Do you prefer Islamic or Conventional banking, or are you flexible?"

Be brief and conversational."""

COLLECT_DEPOSIT_FREQUENCY_PROMPT = """Determine deposit frequency preference.

User message: "{user_message}"

Ask: "Do you prefer lump-sum deposits (Fixed Deposits) or monthly deposits (DPS schemes)?"

Be concise and conversational."""

COLLECT_TENURE_PROMPT = """Determine timeline preference.

User message: "{user_message}"

Ask: "What's your timeline? (1-3 months, 6-12 months, 2-5 years, or 5+ years)"

Be concise and conversational."""

COLLECT_PURPOSE_PROMPT = """Determine savings purpose.

User message: "{user_message}"
User profile: age={age}, occupation={occupation}

Ask: "What's the main purpose? (general savings, child's education, wealth-building, retirement, or monthly income)"

Be concise and conversational."""

FILTER_PRODUCTS_EXPLANATION_PROMPT = """Based on user preferences, explain product recommendations.

User Preferences:
- Banking Type: {banking_type}
- Deposit Frequency: {deposit_frequency}
- Timeline: {tenure_range}
- Purpose: {purpose}

Recommended Products: {product_names}

Explain in 1-2 sentences why these products match their criteria."""
