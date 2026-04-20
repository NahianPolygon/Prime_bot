ELIGIBILITY_SCHEMA = {
    "age": {
        "label": "Age",
        "type": "number",
        "placeholder": "e.g. 30",
        "min": 18,
        "max": 70,
        "required": True,
    },
    "employment_type": {
        "label": "Employment Status",
        "type": "select",
        "options": [
            {"value": "salaried", "label": "Salaried"},
            {"value": "self_employed", "label": "Self-Employed"},
            {"value": "business_owner", "label": "Business Owner"},
        ],
        "required": True,
    },
    "monthly_income": {
        "label": "Monthly Income (BDT)",
        "type": "number",
        "placeholder": "e.g. 50000",
        "min": 0,
        "required": True,
    },
    "employment_duration_years": {
        "label": "Employment Duration (Years)",
        "type": "select",
        "options": [{"value": i, "label": str(i)} for i in range(0, 41)],
        "required": True,
    },
    "employment_duration_months": {
        "label": "Employment Duration (Months)",
        "type": "select",
        "options": [{"value": i, "label": str(i)} for i in range(0, 12)],
        "required": False,
    },
    "has_etin": {
        "label": "Do you have a valid E-TIN?",
        "type": "checkbox",
        "required": False,
    },
}


PREFERENCE_FORM_SCHEMA = {
    "banking_type": {
        "label": "Banking Preference",
        "type": "button_group",
        "options": [
            {"value": "conventional", "label": "Conventional"},
            {"value": "islami", "label": "Islamic (Halal)"},
            {"value": "both", "label": "No Preference"},
        ],
        "required": True,
    },
    "use_case": {
        "label": "Primary Use",
        "type": "tile_grid",
        "options": [
            {"value": "shopping", "label": "Shopping & Daily Use"},
            {"value": "travel", "label": "Travel & Lounge"},
            {"value": "dining", "label": "Dining & Lifestyle"},
            {"value": "rewards_earning", "label": "Rewards & Cashback"},
            {"value": "business_spending", "label": "Business Spending"},
            {"value": "entry_level_premium", "label": "First Premium Card"},
        ],
        "required": True,
    },
    "income_band": {
        "label": "Monthly Income",
        "type": "button_group",
        "options": [
            {"value": "under_50k", "label": "Below BDT 50K"},
            {"value": "50k_100k", "label": "BDT 50K-100K"},
            {"value": "100k_200k", "label": "BDT 100K-200K"},
            {"value": "200k_plus", "label": "BDT 200K+"},
        ],
        "required": True,
    },
    "travel_frequency": {
        "label": "Travel Frequency",
        "type": "button_group",
        "options": [
            {"value": "rare", "label": "Rarely"},
            {"value": "occasional", "label": "Sometimes"},
            {"value": "frequent", "label": "Frequently"},
        ],
        "required": True,
    },
    "tier_preference": {
        "label": "Card Tier Preference",
        "type": "button_group",
        "options": [
            {"value": "gold", "label": "Accessible / Gold"},
            {"value": "premium", "label": "Premium"},
            {"value": "no_preference", "label": "No Preference"},
        ],
        "required": True,
    },
}


def get_preference_form_schema() -> dict:
    return {"fields": PREFERENCE_FORM_SCHEMA}

