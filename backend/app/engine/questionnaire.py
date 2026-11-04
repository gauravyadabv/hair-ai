from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import json

QUESTIONNAIRE_VERSION = "1.0.0"

# Schema definition of all questionnaire questions with metadata
QUESTION_SPECIFICATION = {
    # Personal Information
    "age_range": {
        "category": "personal",
        "label": "Age Range",
        "required": True,
        "type": "select",
        "options": ["under_18", "18_25", "26_35", "36_45", "46_55", "56_plus"],
        "description": "Helps evaluate typical hair life cycle factors."
    },
    "sex": {
        "category": "personal",
        "label": "Sex / Biological Factors",
        "required": False,
        "type": "select",
        "options": ["female", "male", "other", "prefer_not_to_say"],
        "description": "Optional: Only used when relevant to pattern categorization."
    },
    "country_region": {
        "category": "personal",
        "label": "Country / Region",
        "required": False,
        "type": "text",
        "description": "Optional: Environmental and climatic context."
    },

    # Hair Information
    "hair_type": {
        "category": "hair",
        "label": "Hair Type",
        "required": True,
        "type": "select",
        "options": ["straight", "wavy", "curly", "coily", "unsure"],
        "description": "Hair pattern affects light reflection and visible scalp appearance."
    },
    "hair_length": {
        "category": "hair",
        "label": "Hair Length",
        "required": True,
        "type": "select",
        "options": ["very_short", "short", "medium", "long"],
        "description": "Short or long hair influences parting and coverage visualization."
    },
    "hair_texture": {
        "category": "hair",
        "label": "Hair Texture",
        "required": True,
        "type": "select",
        "options": ["fine", "medium", "coarse"],
        "description": "Diameter of individual hair fibers."
    },
    "duration_of_concern": {
        "category": "hair",
        "label": "Duration of Concern",
        "required": True,
        "type": "select",
        "options": ["less_than_3_months", "3_to_6_months", "6_to_12_months", "over_1_year"],
        "description": "Chronicity of the observed changes."
    },
    "shedding_changed": {
        "category": "hair",
        "label": "Noticeable Increase in Daily Shedding",
        "required": True,
        "type": "select",
        "options": ["yes_significant", "yes_slight", "no", "unsure"],
        "description": "Whether shedding has increased in shower, pillow, or brushing."
    },
    "hairline_changed": {
        "category": "hair",
        "label": "Hairline Recession or Change",
        "required": True,
        "type": "select",
        "options": ["receding_temples", "overall_hairline_moving_back", "no_change", "unsure"],
        "description": "Perceived change in frontal and temporal hair boundary."
    },
    "crown_thinner": {
        "category": "hair",
        "label": "Crown / Vertex Looking Thinner",
        "required": True,
        "type": "select",
        "options": ["yes_noticeably", "yes_slightly", "no", "unsure"],
        "description": "Perceived thinning at the crown or swirl area."
    },
    "scalp_visible": {
        "category": "hair",
        "label": "Scalp Visible Through Hair Under Normal Light",
        "required": True,
        "type": "select",
        "options": ["yes_front", "yes_crown", "yes_throughout", "no", "unsure"],
        "description": "Whether scalp skin is readily visible without parting."
    },
    "patchy_loss": {
        "category": "hair",
        "label": "Patchy or Circular Spots of Sudden Hair Loss",
        "required": True,
        "type": "select",
        "options": ["yes", "no", "unsure"],
        "description": "Distinct coin-shaped or discrete bald spots."
    },

    # Scalp Information
    "itching": {
        "category": "scalp",
        "label": "Scalp Itching",
        "required": True,
        "type": "select",
        "options": ["none", "mild", "moderate", "severe"],
        "description": "Frequency or severity of itchy sensations."
    },
    "dandruff_flaking": {
        "category": "scalp",
        "label": "Dandruff or Visible Flaking",
        "required": True,
        "type": "select",
        "options": ["none", "dry_white_flakes", "oily_yellow_flakes", "crusting"],
        "description": "Visible shedding of epidermal flakes."
    },
    "redness": {
        "category": "scalp",
        "label": "Scalp Redness or Irritation",
        "required": True,
        "type": "select",
        "options": ["none", "mild", "moderate_to_severe", "unsure"],
        "description": "Inflammatory signs on scalp skin."
    },
    "pain_tenderness": {
        "category": "scalp",
        "label": "Scalp Tenderness, Burning, or Pain (Trichodynia)",
        "required": True,
        "type": "select",
        "options": ["none", "mild_sensitivity", "burning_pain", "tender_to_touch"],
        "description": "Pain or sensory discomfort around hair follicles."
    },
    "oiliness": {
        "category": "scalp",
        "label": "Scalp Sebum / Oiliness",
        "required": True,
        "type": "select",
        "options": ["dry", "normal", "oily", "very_oily"],
        "description": "Rate at which scalp becomes oily after washing."
    },
    "dryness": {
        "category": "scalp",
        "label": "Scalp Dryness or Tightness",
        "required": True,
        "type": "select",
        "options": ["yes", "no"],
        "description": "Feeling of dry, tight scalp."
    },
    "other_scalp_concerns": {
        "category": "scalp",
        "label": "Other Scalp Concerns",
        "required": False,
        "type": "text",
        "description": "Any additional user-reported observations."
    },

    # Lifestyle Information
    "sleep_pattern": {
        "category": "lifestyle",
        "label": "Sleep Pattern",
        "required": True,
        "type": "select",
        "options": ["regular_7_8_hours", "irregular", "poor_less_than_6_hours"],
        "description": "Sleep quality impacts cellular repair cycles."
    },
    "stress_level": {
        "category": "lifestyle",
        "label": "Perceived Stress Level",
        "required": True,
        "type": "select",
        "options": ["low", "moderate", "high", "extreme"],
        "description": "Physiological stress can trigger telogen shedding."
    },
    "diet_pattern": {
        "category": "lifestyle",
        "label": "Dietary Pattern",
        "required": True,
        "type": "select",
        "options": ["balanced_omnivore", "vegetarian_vegan", "low_calorie_restrictive", "keto_low_carb", "unsure"],
        "description": "Protein and micronutrient intake context."
    },
    "recent_major_illness": {
        "category": "lifestyle",
        "label": "Recent High Fever, Surgery, Major Stress, or Weight Loss (last 6 months)",
        "required": False,
        "type": "select",
        "options": ["yes_high_fever_illness", "yes_surgery_stress", "yes_rapid_weight_loss", "none", "prefer_not_to_say"],
        "description": "Optional: Common trigger for acute telogen effluvium."
    },
    "chemical_treatments": {
        "category": "lifestyle",
        "label": "Chemical Hair Treatments (last 6 months)",
        "required": True,
        "type": "select",
        "options": ["none", "dye_coloring", "bleaching", "perm_straightening", "multiple"],
        "description": "Chemical stress on hair shaft integrity."
    },
    "hair_products": {
        "category": "lifestyle",
        "label": "Current Hair Products",
        "required": False,
        "type": "text",
        "description": "Products currently applied (e.g., Minoxidil, oils, anti-dandruff shampoo)."
    }
}

class QuestionnaireEngine:
    def __init__(self, version: str = QUESTIONNAIRE_VERSION):
        self.version = version

    def get_specification(self) -> Dict[str, Any]:
        """Returns the full specification and metadata of the questionnaire."""
        return {
            "version": self.version,
            "questions": QUESTION_SPECIFICATION
        }

    def validate_and_process(self, raw_answers: List[Dict[str, Any]], consent_status: bool = True) -> Dict[str, Any]:
        """
        Validates answers against the specification.
        Returns categorized, clean structured dictionary with metadata.
        """
        answers_dict = {item["question_key"]: item["answer_value"] for item in raw_answers}
        missing_required = []

        for key, spec in QUESTION_SPECIFICATION.items():
            if spec.get("required", False):
                if key not in answers_dict or answers_dict[key] is None or str(answers_dict[key]).strip() == "":
                    missing_required.append(key)

        categorized = {
            "personal": {},
            "hair": {},
            "scalp": {},
            "lifestyle": {}
        }

        for key, val in answers_dict.items():
            spec = QUESTION_SPECIFICATION.get(key)
            if spec:
                cat = spec["category"]
                categorized[cat][key] = {
                    "label": spec["label"],
                    "value": val,
                    "description": spec["description"]
                }
            else:
                # Custom or extra answer
                categorized.setdefault("other", {})[key] = {
                    "label": key,
                    "value": val,
                    "description": "Additional user answer"
                }

        processed = {
            "questionnaire_version": self.version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "consent_status": consent_status,
            "is_complete": len(missing_required) == 0,
            "missing_required_fields": missing_required,
            "raw_answers": answers_dict,
            "categorized": categorized
        }

        return processed

questionnaire_engine = QuestionnaireEngine()

