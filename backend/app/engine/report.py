from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import json
from app.core.config import settings

EDUCATIONAL_DISCLAIMER = (
    "DISCLAIMER: This Hair Health AI report is generated for educational and informational purposes only. "
    "It does NOT provide a medical diagnosis, identify specific clinical conditions (such as alopecia areata, "
    "androgenetic alopecia, or scarring alopecias), or replace the professional judgment of a board-certified "
    "dermatologist or trichologist. Always consult a licensed healthcare professional for medical diagnosis and treatment."
)

class ReportEngine:
    def __init__(self, report_version: str = settings.REPORT_VERSION):
        self.report_version = report_version

    def generate_report(
        self,
        assessment_id: str,
        assessment_created_at: datetime,
        questionnaire_data: Dict[str, Any],
        photo_quality_data: Dict[str, Dict[str, Any]],
        image_feature_data: Dict[str, Dict[str, Any]],
        assessment_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synthesizes the complete 12-section structured report according to PRD specification.
        """
        now = datetime.now(timezone.utc)
        evidence = assessment_result.get("evidence_categories", {})

        # Photo Quality Summary
        photo_summary = {}
        for angle, q in photo_quality_data.items():
            photo_summary[angle] = {
                "status": q.get("quality_status", "unknown"),
                "blur_score": q.get("blur_score"),
                "brightness_score": q.get("brightness_score"),
                "warnings": q.get("warnings", [])
            }

        # Image analysis results summary (if validated or Phase 1-2 CV)
        image_analysis_summary = {
            "is_clinical_density_validated": False,
            "density_statement": "No validated clinical follicular density estimate available (requires calibrated trichoscopy).",
            "regional_pixel_coverage": {},
            "observations": []
        }
        for angle, feat in image_feature_data.items():
            f_data = feat.get("feature_data", {})
            hair_ratio = f_data.get("hair_pixel_ratio")
            scalp_ratio = f_data.get("scalp_pixel_ratio")
            if hair_ratio is not None:
                image_analysis_summary["regional_pixel_coverage"][angle] = {
                    "hair_pixel_ratio": hair_ratio,
                    "scalp_pixel_ratio": scalp_ratio,
                    "lighting_uniformity": f_data.get("lighting_uniformity")
                }
        for obs in evidence.get("image_observations", []):
            image_analysis_summary["observations"].append(obs.get("observation"))

        report_payload = {
            "report_id": f"REP-{assessment_id[:8].upper()}",
            "assessment_id": assessment_id,
            "report_version": self.report_version,
            "engine_version": settings.ENGINE_VERSION,
            "model_version": settings.DEFAULT_MODEL_VERSION,
            "assessment_date": assessment_created_at.isoformat() if isinstance(assessment_created_at, datetime) else str(assessment_created_at),
            "generated_at": now.isoformat(),

            # 1. Assessment Overview
            "1_assessment_overview": {
                "assessment_id": assessment_id,
                "status": "completed",
                "evaluated_angles_count": len(photo_quality_data),
                "summary": "Completed structured questionnaire and standardized five-angle photo quality & visual feature extraction."
            },

            # 2. User-Reported Hair Concerns
            "2_user_reported_concerns": evidence.get("user_reported_concerns", []),

            # 3. Questionnaire Summary
            "3_questionnaire_summary": {
                "personal_factors": questionnaire_data.get("categorized", {}).get("personal", {}),
                "hair_characteristics": questionnaire_data.get("categorized", {}).get("hair", {}),
                "scalp_symptoms": questionnaire_data.get("categorized", {}).get("scalp", {}),
                "lifestyle_factors": questionnaire_data.get("categorized", {}).get("lifestyle", {})
            },

            # 4. Photo Quality Summary
            "4_photo_quality_summary": photo_summary,

            # 5. Image Analysis Results
            "5_image_analysis_results": image_analysis_summary,

            # 6. Evidence Confidence & Limitations
            "6_evidence_confidence_and_limitations": {
                "confidence_level": "moderate_visual_screening",
                "distinction": "Assessment strictly distinguishes between user-reported information, surface photograph contrast, and clinical uncertainty.",
                "limitations": evidence.get("uncertain_evidence", []) + evidence.get("missing_or_insufficient_evidence", [])
            },

            # 7. Areas Worth Monitoring
            "7_areas_worth_monitoring": assessment_result.get("possible_patterns_worth_monitoring", []),

            # 8. Practical Hair-Care Recommendations
            "8_practical_recommendations": assessment_result.get("recommended_next_steps", []),

            # 9. Professional-Care Guidance
            "9_professional_care_guidance": assessment_result.get("reasons_to_seek_professional_care", []),

            # 10. Assessment Date
            "10_assessment_date": assessment_created_at.isoformat() if isinstance(assessment_created_at, datetime) else str(assessment_created_at),

            # 11. Engine & Model Versions
            "11_engine_versions": {
                "engine_version": settings.ENGINE_VERSION,
                "questionnaire_version": questionnaire_data.get("questionnaire_version", settings.QUESTIONNAIRE_VERSION),
                "assessment_rules_version": assessment_result.get("rules_version", "1.0.0"),
                "report_version": self.report_version
            },

            # 12. Educational Disclaimer
            "12_educational_disclaimer": EDUCATIONAL_DISCLAIMER
        }

        return report_payload

    def generate_pdf_report(self, report_data: Dict[str, Any], output_path: Path | str) -> str:
        """
        Renders the structured report into a clean, portable PDF document using ReportLab.
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

            pdf_path = Path(output_path)
            pdf_path.parent.mkdir(parents=True, exist_ok=True)

            doc = SimpleDocTemplate(
                str(pdf_path),
                pagesize=letter,
                rightMargin=40,
                leftMargin=40,
                topMargin=40,
                bottomMargin=40
            )
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                'ReportTitle',
                parent=styles['Heading1'],
                fontSize=20,
                leading=24,
                textColor=colors.HexColor("#1e293b"),
                spaceAfter=10
            )
            h2_style = ParagraphStyle(
                'SectionHeader',
                parent=styles['Heading2'],
                fontSize=13,
                leading=16,
                textColor=colors.HexColor("#0f766e"),
                spaceBefore=12,
                spaceAfter=6
            )
            body_style = ParagraphStyle(
                'Body',
                parent=styles['Normal'],
                fontSize=9,
                leading=13,
                textColor=colors.HexColor("#334155")
            )
            disclaimer_style = ParagraphStyle(
                'Disclaimer',
                parent=styles['Normal'],
                fontSize=8,
                leading=11,
                textColor=colors.HexColor("#b91c1c"),
                backColor=colors.HexColor("#fef2f2"),
                borderColor=colors.HexColor("#fecaca"),
                borderWidth=1,
                borderPadding=8,
                spaceBefore=10
            )

            story = []

            # Header
            story.append(Paragraph("HAIR HEALTH AI — ASSESSMENT REPORT", title_style))
            story.append(Paragraph(
                f"<b>Assessment ID:</b> {report_data.get('assessment_id')} &nbsp;|&nbsp; "
                f"<b>Date:</b> {report_data.get('assessment_date', '')[:10]} &nbsp;|&nbsp; "
                f"<b>Engine Version:</b> {report_data.get('engine_version')}",
                body_style
            ))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=10, spaceBefore=5))

            # 1. User Concerns
            story.append(Paragraph("1. User-Reported Observations", h2_style))
            concerns = report_data.get("2_user_reported_concerns", [])
            if concerns:
                for c in concerns:
                    story.append(Paragraph(f"• <b>{c.get('category', '').replace('_', ' ').title()}:</b> {c.get('finding')} <i>({c.get('detail', '')})</i>", body_style))
            else:
                story.append(Paragraph("No severe concerns reported in questionnaire.", body_style))

            # 2. Photo Quality
            story.append(Paragraph("2. Photo Quality Summary", h2_style))
            photos = report_data.get("4_photo_quality_summary", {})
            table_data = [["Angle", "Status", "Blur Score", "Brightness", "Feedback"]]
            for angle, q in photos.items():
                warnings = ", ".join(q.get("warnings", [])) or "None (Clean)"
                table_data.append([
                    angle.replace("_", " ").title(),
                    q.get("status", "").upper(),
                    str(q.get("blur_score", "N/A")),
                    str(q.get("brightness_score", "N/A")),
                    warnings[:60]
                ])
            if len(table_data) > 1:
                t = Table(table_data, colWidths=[90, 65, 60, 60, 240])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0"))
                ]))
                story.append(t)

            # 3. Image Analysis
            story.append(Paragraph("3. Image Analysis & Pixel Contrast", h2_style))
            img_res = report_data.get("5_image_analysis_results", {})
            story.append(Paragraph(f"<b>Density Validation:</b> {img_res.get('density_statement')}", body_style))
            for obs in img_res.get("observations", []):
                story.append(Paragraph(f"• {obs}", body_style))

            # 4. Areas Worth Monitoring
            story.append(Paragraph("4. Patterns Worth Monitoring", h2_style))
            patterns = report_data.get("7_areas_worth_monitoring", [])
            if patterns:
                for p in patterns:
                    story.append(Paragraph(f"• <b>{p.get('pattern_name')}:</b> {p.get('description')} <i>({p.get('notes')})</i>", body_style))
            else:
                story.append(Paragraph("No unusual asymmetry or focal thinning patterns detected.", body_style))

            # 5. Practical Hair Care Guidance
            story.append(Paragraph("5. Practical Hair & Scalp Guidance", h2_style))
            for rec in report_data.get("8_practical_recommendations", []):
                story.append(Paragraph(f"• {rec}", body_style))

            # 6. Medical & Professional Guidance
            story.append(Paragraph("6. Professional Care Guidance", h2_style))
            for reason in report_data.get("9_professional_care_guidance", []):
                story.append(Paragraph(f"• {reason}", body_style))

            # Educational Disclaimer
            story.append(Spacer(1, 10))
            story.append(Paragraph(report_data.get("12_educational_disclaimer", EDUCATIONAL_DISCLAIMER), disclaimer_style))

            doc.build(story)
            return str(pdf_path)
        except Exception as e:
            # If ReportLab fails or has font issue, return none and log
            return ""

report_engine = ReportEngine()

