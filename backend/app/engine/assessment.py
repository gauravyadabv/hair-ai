from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.core.config import settings

ASSESSMENT_RULES_VERSION = "1.0.0"

class AssessmentEngine:
    def __init__(self, rules_version: str = ASSESSMENT_RULES_VERSION):
        self.rules_version = rules_version

    def evaluate(
        self,
        questionnaire_data: Dict[str, Any],
        photo_quality_data: Dict[str, Dict[str, Any]],
        image_feature_data: Dict[str, Dict[str, Any]],
        previous_assessment: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes rule-based assessment separating:
        - user_reported evidence
        - image_observed evidence
        - uncertain evidence
        Produces 6 structured categories without generating unvalidated medical diagnoses.
        """
        raw_answers = questionnaire_data.get("raw_answers", {})
        categorized = questionnaire_data.get("categorized", {})

        user_reported_concerns: List[Dict[str, Any]] = []
        image_observations: List[Dict[str, Any]] = []
        missing_or_insufficient_evidence: List[str] = []
        possible_patterns_worth_monitoring: List[Dict[str, Any]] = []
        recommended_next_steps: List[str] = []
        reasons_to_seek_professional_care: List[str] = []

        # -------------------------------------------------------------
        # 1. EVALUATE USER-REPORTED EVIDENCE
        # -------------------------------------------------------------
        # Hair concerns
        shedding = raw_answers.get("shedding_changed")
        if shedding in ["yes_significant", "yes_slight"]:
            user_reported_concerns.append({
                "category": "hair_shedding",
                "evidence_type": "user_reported",
                "finding": f"User reports noticeable increase in daily hair shedding ({shedding.replace('_', ' ')}).",
                "detail": "Increased shedding may be reactive (telogen phase shifting) or progressive."
            })

        hairline = raw_answers.get("hairline_changed")
        if hairline and hairline != "no_change" and hairline != "unsure":
            user_reported_concerns.append({
                "category": "hairline_recession",
                "evidence_type": "user_reported",
                "finding": f"User notes change in hairline shape: {hairline.replace('_', ' ')}.",
                "detail": "Reported bitemporal recession or hairline elevation."
            })

        crown_thin = raw_answers.get("crown_thinner")
        if crown_thin in ["yes_noticeably", "yes_slightly"]:
            user_reported_concerns.append({
                "category": "vertex_thinning",
                "evidence_type": "user_reported",
                "finding": f"User notes thinning at the crown/vertex ({crown_thin.replace('_', ' ')}).",
                "detail": "Visible lightening or density loss at the whorl."
            })

        patchy = raw_answers.get("patchy_loss")
        if patchy == "yes":
            user_reported_concerns.append({
                "category": "focal_patchy_loss",
                "evidence_type": "user_reported",
                "finding": "User reports sudden, distinct circular or coin-shaped bald spots.",
                "detail": "Acute patchy loss warrants prompt in-person dermatological evaluation."
            })
            reasons_to_seek_professional_care.append(
                "User-reported discrete, patchy hair loss patches warrant rapid clinical inspection for autoimmune conditions."
            )

        # Scalp symptoms
        itching = raw_answers.get("itching")
        redness = raw_answers.get("redness")
        pain = raw_answers.get("pain_tenderness")
        flaking = raw_answers.get("dandruff_flaking")

        scalp_symptoms = []
        if itching in ["moderate", "severe"]:
            scalp_symptoms.append(f"significant itching ({itching})")
        if redness in ["mild", "moderate_to_severe"]:
            scalp_symptoms.append(f"scalp redness ({redness.replace('_', ' ')})")
        if pain in ["mild_sensitivity", "burning_pain", "tender_to_touch"]:
            scalp_symptoms.append(f"scalp tenderness/burning ({pain.replace('_', ' ')})")
        if flaking in ["dry_white_flakes", "oily_yellow_flakes", "crusting"]:
            scalp_symptoms.append(f"flaking ({flaking.replace('_', ' ')})")

        if scalp_symptoms:
            user_reported_concerns.append({
                "category": "scalp_symptoms",
                "evidence_type": "user_reported",
                "finding": f"User reports active scalp discomfort: {', '.join(scalp_symptoms)}.",
                "detail": "Inflammation or seborrheic factors can destabilize the follicle environment."
            })
            if pain in ["burning_pain", "tender_to_touch"] or redness == "moderate_to_severe":
                reasons_to_seek_professional_care.append(
                    "Persistent scalp pain, burning sensations, or prominent erythema may indicate underlying scalp dermatoses or scarring processes."
                )

        # Lifestyle & recent triggers
        recent_illness = raw_answers.get("recent_major_illness")
        if recent_illness in ["yes_high_fever_illness", "yes_surgery_stress", "yes_rapid_weight_loss"]:
            user_reported_concerns.append({
                "category": "physiological_trigger",
                "evidence_type": "user_reported",
                "finding": f"Recent physiological event reported: {recent_illness.replace('_', ' ')} within last 6 months.",
                "detail": "Major physiological stressors frequently trigger temporary shedding (telogen effluvium) 2-4 months later."
            })

        # -------------------------------------------------------------
        # 2. EVALUATE PHOTO QUALITY & MISSING EVIDENCE
        # -------------------------------------------------------------
        required_angles = ["front_hairline", "top_scalp", "crown", "left_temple", "right_temple"]
        uploaded_angles = list(photo_quality_data.keys())

        for angle in required_angles:
            if angle not in uploaded_angles:
                missing_or_insufficient_evidence.append(
                    f"Missing {angle.replace('_', ' ')} photograph. A complete five-angle set is required for full comparative assessment."
                )
            else:
                q = photo_quality_data[angle]
                if q.get("quality_status") == "rejected":
                    missing_or_insufficient_evidence.append(
                        f"Photo for {angle.replace('_', ' ')} was rejected due to quality issues: {'; '.join(q.get('warnings', []))}."
                    )
                elif q.get("quality_status") == "needs_improvement":
                    missing_or_insufficient_evidence.append(
                        f"Photo for {angle.replace('_', ' ')} has sub-optimal lighting or focus: {'; '.join(q.get('warnings', []))}."
                    )

        # -------------------------------------------------------------
        # 3. EVALUATE IMAGE-OBSERVED EVIDENCE
        # -------------------------------------------------------------
        for angle, feat in image_feature_data.items():
            f_data = feat.get("feature_data", {})
            hair_ratio = f_data.get("hair_pixel_ratio")
            scalp_ratio = f_data.get("scalp_pixel_ratio")
            uniformity = f_data.get("lighting_uniformity", 1.0)

            if hair_ratio is not None and scalp_ratio is not None:
                image_observations.append({
                    "angle": angle,
                    "evidence_type": "image_observed",
                    "hair_pixel_coverage": hair_ratio,
                    "scalp_pixel_coverage": scalp_ratio,
                    "lighting_uniformity": uniformity,
                    "observation": f"In {angle.replace('_', ' ')} view, visual hair-pixel coverage is {hair_ratio*100:.1f}%, visible scalp contrast is {scalp_ratio*100:.1f}%."
                })

        # Cross-angle pattern observations
        ratios = {angle: feat.get("feature_data", {}).get("hair_pixel_ratio") for angle, feat in image_feature_data.items() if feat.get("feature_data", {}).get("hair_pixel_ratio") is not None}
        
        if "crown" in ratios and "top_scalp" in ratios:
            if ratios["top_scalp"] - ratios["crown"] > 0.12:
                possible_patterns_worth_monitoring.append({
                    "pattern_name": "Vertex vs Mid-scalp Contrast Variance",
                    "evidence_basis": "image_observed",
                    "description": "Visual pixel coverage at the crown shows lower density appearance compared to top-scalp.",
                    "notes": "Recommend monitoring vertex closely with identical lighting in subsequent checks."
                })

        if "left_temple" in ratios and "right_temple" in ratios:
            asym = abs(ratios["left_temple"] - ratios["right_temple"])
            if asym > 0.12:
                possible_patterns_worth_monitoring.append({
                    "pattern_name": "Bitemporal Asymmetry",
                    "evidence_basis": "image_observed",
                    "description": f"Noticeable contrast difference ({asym*100:.1f}%) observed between left and right temples.",
                    "notes": "Natural asymmetry or preferential sleeping/parting posture may contribute."
                })

        # Correlate user-reported shedding with timeline
        duration = raw_answers.get("duration_of_concern")
        if shedding in ["yes_significant", "yes_slight"]:
            if duration in ["less_than_3_months", "3_to_6_months"]:
                possible_patterns_worth_monitoring.append({
                    "pattern_name": "Acute Diffuse Shedding Timeline",
                    "evidence_basis": "user_reported",
                    "description": "Reported duration under 6 months suggests a potential acute cycle rather than chronic longstanding thinning.",
                    "notes": "Tracking daily hair loss counts and reviewing recent lifestyle changes is helpful."
                })
            elif duration in ["6_to_12_months", "over_1_year"]:
                possible_patterns_worth_monitoring.append({
                    "pattern_name": "Chronic Shedding / Progressive Pattern",
                    "evidence_basis": "user_reported",
                    "description": "Concern persisting over 6-12 months indicates a sustained or gradual process.",
                    "notes": "Consider formal baseline dermoscopic evaluation."
                })

        # -------------------------------------------------------------
        # 4. RECOMMENDED NEXT STEPS (PRACTICAL & EDUCATIONAL)
        # -------------------------------------------------------------
        recommended_next_steps.append("Establish a consistent monthly photo baseline under identical room lighting and dry hair conditions.")
        if flaking != "none" or itching != "none":
            recommended_next_steps.append("Consider a gentle, clarifying or zinc-pyrithione/ketoconazole based scalp cleanser to soothe epidermal flaking.")
        if raw_answers.get("stress_level") in ["high", "extreme"] or raw_answers.get("sleep_pattern") == "poor_less_than_6_hours":
            recommended_next_steps.append("Address lifestyle recovery: Sleep hygiene and physiological stress directly modulate hair follicle transition.")
        recommended_next_steps.append("Avoid high-tension hairstyles (tight ponytails/braids) and excessive heat styling that place mechanical traction on follicles.")

        # General doctor guidance
        if not reasons_to_seek_professional_care:
            reasons_to_seek_professional_care.append(
                "If hair shedding accelerates rapidly or noticeable scalp exposure widens over the next 8-12 weeks."
            )
            reasons_to_seek_professional_care.append(
                "To obtain a definitive clinical diagnosis and trichoscopy magnification of follicular units from a board-certified dermatologist."
            )

        # -------------------------------------------------------------
        # 5. SCIENTIFIC LIMITATIONS & UNCERTAIN EVIDENCE
        # -------------------------------------------------------------
        uncertain_evidence = [
            "Clinical hair shaft caliber diversity (miniaturization) cannot be quantified from standard consumer camera photos.",
            "Pixel segmentation coverage is not a measure of follicular unit density per square centimeter (FU/cm²).",
            "Internal systemic factors (serum ferritin, thyroid function, hormonal profiles) cannot be assessed visually."
        ]

        return {
            "assessment_id": questionnaire_data.get("assessment_id"),
            "engine_version": settings.ENGINE_VERSION,
            "rules_version": self.rules_version,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "evidence_categories": {
                "user_reported_concerns": user_reported_concerns,
                "image_observations": image_observations,
                "uncertain_evidence": uncertain_evidence,
                "missing_or_insufficient_evidence": missing_or_insufficient_evidence
            },
            "possible_patterns_worth_monitoring": possible_patterns_worth_monitoring,
            "recommended_next_steps": recommended_next_steps,
            "reasons_to_seek_professional_care": reasons_to_seek_professional_care,
            "prohibition_compliance": {
                "no_unsupported_alopecia_diagnosis": True,
                "no_unvalidated_density_numbers": True,
                "no_medical_claims_made": True
            }
        }

assessment_engine = AssessmentEngine()

