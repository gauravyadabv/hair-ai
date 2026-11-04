import os
import io
import pytest
import numpy as np
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import Base, engine
from app.engine.questionnaire import questionnaire_engine
from app.engine.image_quality import image_quality_engine
from app.engine.feature_extraction import feature_extraction_engine
from app.engine.assessment import assessment_engine
from app.engine.report import report_engine
from app.core.config import settings

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield

def create_synthetic_scalp_image(width=600, height=600, is_blurry=False, is_dark=False):
    """Generates synthetic scalp/hair image in memory for testing."""
    img = Image.new("RGB", (width, height), color=(220, 200, 185) if not is_dark else (10, 10, 10))
    draw = ImageDraw.Draw(img)

    if not is_dark:
        # Draw dark hair strands to simulate hair contrast
        for x in range(30, width - 30, 8):
            draw.line([(x, 40), (x + 15, height - 40)], fill=(30, 20, 15), width=3)
        for y in range(50, height - 50, 14):
            draw.line([(40, y), (width - 40, y + 10)], fill=(20, 15, 10), width=2)

    if is_blurry:
        from PIL import ImageFilter
        img = img.filter(ImageFilter.GaussianBlur(radius=8))

    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf, img

# ----------------- 1. Questionnaire Engine Tests -----------------
def test_questionnaire_specification():
    spec = questionnaire_engine.get_specification()
    assert spec["version"] == settings.QUESTIONNAIRE_VERSION
    assert "hair_type" in spec["questions"]
    assert "itching" in spec["questions"]
    assert "sleep_pattern" in spec["questions"]

def test_questionnaire_validation_and_categorization():
    raw_answers = [
        {"question_key": "age_range", "answer_value": "26_35"},
        {"question_key": "hair_type", "answer_value": "wavy"},
        {"question_key": "hair_length", "answer_value": "medium"},
        {"question_key": "hair_texture", "answer_value": "medium"},
        {"question_key": "duration_of_concern", "answer_value": "3_to_6_months"},
        {"question_key": "shedding_changed", "answer_value": "yes_significant"},
        {"question_key": "hairline_changed", "answer_value": "receding_temples"},
        {"question_key": "crown_thinner", "answer_value": "yes_slightly"},
        {"question_key": "scalp_visible", "answer_value": "yes_front"},
        {"question_key": "patchy_loss", "answer_value": "no"},
        {"question_key": "itching", "answer_value": "mild"},
        {"question_key": "dandruff_flaking", "answer_value": "dry_white_flakes"},
        {"question_key": "redness", "answer_value": "none"},
        {"question_key": "pain_tenderness", "answer_value": "none"},
        {"question_key": "oiliness", "answer_value": "normal"},
        {"question_key": "dryness", "answer_value": "no"},
        {"question_key": "sleep_pattern", "answer_value": "regular_7_8_hours"},
        {"question_key": "stress_level", "answer_value": "moderate"},
        {"question_key": "diet_pattern", "answer_value": "balanced_omnivore"},
        {"question_key": "chemical_treatments", "answer_value": "none"},
    ]
    result = questionnaire_engine.validate_and_process(raw_answers)
    assert result["is_complete"] is True
    assert len(result["missing_required_fields"]) == 0
    assert "hair" in result["categorized"]
    assert "scalp" in result["categorized"]
    assert result["categorized"]["hair"]["shedding_changed"]["value"] == "yes_significant"

# ----------------- 2. Image Quality Engine Tests -----------------
def test_image_quality_sharp_image(tmp_path):
    buf, _ = create_synthetic_scalp_image(width=600, height=600, is_blurry=False)
    test_file = tmp_path / "sharp_test.jpg"
    test_file.write_bytes(buf.getvalue())

    eval_res = image_quality_engine.evaluate_quality(test_file, "IMG_TEST_1", "front_hairline")
    assert eval_res["quality_status"] in ["acceptable", "needs_improvement"]
    assert eval_res["blur_score"] > 50.0
    assert eval_res["resolution"]["width"] == 600

def test_image_quality_low_resolution(tmp_path):
    buf, _ = create_synthetic_scalp_image(width=300, height=300)
    test_file = tmp_path / "lowres_test.jpg"
    test_file.write_bytes(buf.getvalue())

    eval_res = image_quality_engine.evaluate_quality(test_file, "IMG_TEST_2", "crown")
    assert eval_res["quality_status"] == "rejected"
    assert any("below the minimum required" in w for w in eval_res["warnings"])

# ----------------- 3. Feature Extraction Tests -----------------
def test_feature_extraction(tmp_path):
    buf, _ = create_synthetic_scalp_image(width=600, height=600)
    test_file = tmp_path / "feat_test.jpg"
    test_file.write_bytes(buf.getvalue())

    feat = feature_extraction_engine.analyze_photo_features(test_file, "top_scalp")
    assert feat["status"] == "completed"
    assert "hair_pixel_ratio" in feat["feature_data"]
    assert "scalp_pixel_ratio" in feat["feature_data"]
    assert 0.0 <= feat["feature_data"]["hair_pixel_ratio"] <= 1.0

# ----------------- 4. Assessment & Report Tests -----------------
def test_assessment_and_report_generation():
    q_data = {
        "assessment_id": "HA-TEST-001",
        "questionnaire_version": "1.0.0",
        "raw_answers": {
            "shedding_changed": "yes_significant",
            "hairline_changed": "receding_temples",
            "crown_thinner": "yes_slightly",
            "duration_of_concern": "3_to_6_months",
            "itching": "mild",
            "dandruff_flaking": "dry_white_flakes"
        },
        "categorized": {}
    }
    photo_q = {
        "front_hairline": {"quality_status": "acceptable", "blur_score": 150.0, "brightness_score": 120.0},
        "crown": {"quality_status": "acceptable", "blur_score": 140.0, "brightness_score": 115.0}
    }
    image_feat = {
        "front_hairline": {
            "feature_data": {"hair_pixel_ratio": 0.65, "scalp_pixel_ratio": 0.35, "lighting_uniformity": 0.88}
        },
        "crown": {
            "feature_data": {"hair_pixel_ratio": 0.50, "scalp_pixel_ratio": 0.50, "lighting_uniformity": 0.82}
        }
    }

    eval_result = assessment_engine.evaluate(q_data, photo_q, image_feat)
    assert len(eval_result["evidence_categories"]["user_reported_concerns"]) >= 2
    assert eval_result["prohibition_compliance"]["no_unsupported_alopecia_diagnosis"] is True

    # Report synthesis
    from datetime import datetime, timezone
    report_data = report_engine.generate_report(
        assessment_id="HA-TEST-001",
        assessment_created_at=datetime.now(timezone.utc),
        questionnaire_data=q_data,
        photo_quality_data=photo_q,
        image_feature_data=image_feat,
        assessment_result=eval_result
    )

    # Verify all 12 sections from PRD
    for i in range(1, 13):
        prefix = f"{i}_"
        matching_keys = [k for k in report_data.keys() if k.startswith(prefix)]
        assert len(matching_keys) == 1, f"Missing report section {prefix}"

# ----------------- 5. Full End-to-End API Pipeline Test -----------------
def test_full_pipeline_e2e():
    with TestClient(app) as client:
        # 1. Health check
        res = client.get("/")
        assert res.status_code == 200
        assert "pipeline" in res.json()

        # 2. Register user
        email = "testuser@example.com"
        pwd = "SecurePassword123!"
        reg_res = client.post("/api/v1/auth/register", json={
            "name": "Jane Doe",
            "email": email,
            "password": pwd,
            "consent_processing": True,
            "consent_research": True
        })
        if reg_res.status_code == 400:  # already exists from prior test run
            login_res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
            token = login_res.json()["access_token"]
        else:
            assert reg_res.status_code == 201
            token = reg_res.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # 3. Create assessment
        ass_res = client.post("/api/v1/assessments", headers=headers)
        assert ass_res.status_code == 201
        assessment_id = ass_res.json()["id"]

        # 4. Hair Test (Questionnaire answers submission)
        answers_payload = {
            "consent_confirmed": True,
            "answers": [
                {"question_key": "age_range", "answer_value": "26_35"},
                {"question_key": "hair_type", "answer_value": "straight"},
                {"question_key": "hair_length", "answer_value": "medium"},
                {"question_key": "hair_texture", "answer_value": "fine"},
                {"question_key": "duration_of_concern", "answer_value": "3_to_6_months"},
                {"question_key": "shedding_changed", "answer_value": "yes_significant"},
                {"question_key": "hairline_changed", "answer_value": "receding_temples"},
                {"question_key": "crown_thinner", "answer_value": "yes_noticeably"},
                {"question_key": "scalp_visible", "answer_value": "yes_crown"},
                {"question_key": "patchy_loss", "answer_value": "no"},
                {"question_key": "itching", "answer_value": "mild"},
                {"question_key": "dandruff_flaking", "answer_value": "none"},
                {"question_key": "redness", "answer_value": "none"},
                {"question_key": "pain_tenderness", "answer_value": "none"},
                {"question_key": "oiliness", "answer_value": "normal"},
                {"question_key": "dryness", "answer_value": "no"},
                {"question_key": "sleep_pattern", "answer_value": "regular_7_8_hours"},
                {"question_key": "stress_level", "answer_value": "moderate"},
                {"question_key": "diet_pattern", "answer_value": "balanced_omnivore"},
                {"question_key": "chemical_treatments", "answer_value": "none"}
            ]
        }
        ans_res = client.post(f"/api/v1/assessments/{assessment_id}/answers", json=answers_payload, headers=headers)
        assert ans_res.status_code == 200
        assert ans_res.json()["is_complete"] is True

        # 5. Photo Upload: upload all 5 required angles
        angles = ["front_hairline", "top_scalp", "crown", "left_temple", "right_temple"]
        for angle in angles:
            buf, _ = create_synthetic_scalp_image(width=600, height=600)
            files = {"file": (f"{angle}.jpg", buf.getvalue(), "image/jpeg")}
            data = {"angle": angle}
            up_res = client.post(f"/api/v1/assessments/{assessment_id}/photos", files=files, data=data, headers=headers)
            assert up_res.status_code == 201
            assert up_res.json()["quality_status"] in ["acceptable", "needs_improvement"]

        # 6. Image Processing & Feature Extraction
        analyze_res = client.post(f"/api/v1/assessments/{assessment_id}/analyze", headers=headers)
        assert analyze_res.status_code == 200
        assert analyze_res.json()["status"] == "completed"
        assert analyze_res.json()["photos_analyzed_count"] == 5

        # 7. Assessment Engine & Report Generation
        rep_res = client.post(f"/api/v1/assessments/{assessment_id}/report", headers=headers)
        assert rep_res.status_code == 201
        report = rep_res.json()["report_data"]

        # 8. Verify structured report integrity
        assert "1_assessment_overview" in report
        assert "2_user_reported_concerns" in report
        assert "4_photo_quality_summary" in report
        assert "5_image_analysis_results" in report
        assert "8_practical_recommendations" in report
        assert "12_educational_disclaimer" in report
        assert len(report["4_photo_quality_summary"]) == 5

        # 9. Test PDF download endpoint
        pdf_res = client.get(f"/api/v1/assessments/{assessment_id}/report/pdf", headers=headers)
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"

        # 10. Test User Data Export
        data_res = client.get("/api/v1/users/me/data", headers=headers)
        assert data_res.status_code == 200
        assert len(data_res.json()["assessments"]) >= 1
