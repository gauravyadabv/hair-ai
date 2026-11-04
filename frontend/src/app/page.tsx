'use client';

import React, { useState, useEffect, useRef } from 'react';
import { 
  Camera, CheckCircle2, AlertTriangle, FileText, 
  Download, ArrowRight, RefreshCw, Shield, Sparkles, Check
} from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000';

const REQUIRED_ANGLES = [
  { key: 'front_hairline', label: '1. Front Hairline', desc: 'Pull bangs/hair back to show the frontal hairline boundary' },
  { key: 'top_scalp', label: '2. Top Scalp', desc: 'Center top part line or mid-scalp hair density' },
  { key: 'crown', label: '3. Crown / Vertex', desc: 'Rear whorl/swirl area where thinning often begins' },
  { key: 'left_temple', label: '4. Left Temple', desc: 'Turn head right to reveal left temporal corner' },
  { key: 'right_temple', label: '5. Right Temple', desc: 'Turn head left to reveal right temporal corner' },
];

export default function HairHealthTestingApp() {
  const [currentStep, setCurrentStep] = useState<number>(2); // Start on photos or test
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');

  // Questionnaire Defaults
  const [answers, setAnswers] = useState<Record<string, any>>({
    age_range: '26_35',
    hair_type: 'straight',
    hair_length: 'medium',
    hair_texture: 'medium',
    duration_of_concern: '3_to_6_months',
    shedding_changed: 'yes_significant',
    hairline_changed: 'receding_temples',
    crown_thinner: 'yes_noticeably',
    scalp_visible: 'yes_crown',
    patchy_loss: 'no',
    itching: 'mild',
    dandruff_flaking: 'dry_white_flakes',
    redness: 'none',
    pain_tenderness: 'none',
    oiliness: 'normal',
    dryness: 'no',
    sleep_pattern: 'regular_7_8_hours',
    stress_level: 'moderate',
    diet_pattern: 'balanced_omnivore',
    chemical_treatments: 'none',
    hair_products: 'Standard gentle shampoo'
  });

  // Photos State
  const [uploadedPhotos, setUploadedPhotos] = useState<Record<string, any>>({});
  const [uploadingAngle, setUploadingAngle] = useState<string | null>(null);
  const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  // Analysis & Report
  const [analysisData, setAnalysisData] = useState<any>(null);
  const [reportData, setReportData] = useState<any>(null);

  // Helper fetch that handles both proxy and direct backend URL
  const apiFetch = async (path: string, options: RequestInit = {}) => {
    try {
      // Try direct API first for maximum reliability
      const res = await fetch(`${API_BASE}${path}`, options);
      return res;
    } catch {
      // Fallback to relative proxy
      return await fetch(path, options);
    }
  };

  // Initialize or resume assessment on page load
  useEffect(() => {
    checkHealthAndInit();
  }, []);

  const checkHealthAndInit = async () => {
    setBackendStatus('checking');
    try {
      const res = await apiFetch('/');
      if (res.ok) {
        setBackendStatus('online');
        initTestAssessment();
      } else {
        setBackendStatus('offline');
      }
    } catch {
      setBackendStatus('offline');
    }
  };

  const initTestAssessment = async () => {
    try {
      // Check existing assessments
      const listRes = await apiFetch('/api/v1/assessments');
      if (listRes.ok) {
        const list = await listRes.json();
        if (list.length > 0) {
          const latest = list[0];
          setAssessmentId(latest.id);
          fetchPhotos(latest.id);
          if (latest.assessment_status === 'completed') {
            fetchReport(latest.id);
          } else if (latest.assessment_status === 'analyzed') {
            fetchAnalysis(latest.id);
          }
          return;
        }
      }
      // Create fresh one
      createNewAssessment();
    } catch (e) {
      console.error(e);
    }
  };

  const createNewAssessment = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await apiFetch('/api/v1/assessments', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setAssessmentId(data.id);
        setUploadedPhotos({});
        setAnalysisData(null);
        setReportData(null);
        setCurrentStep(1);
      } else {
        setErrorMsg('Could not initialize test session.');
      }
    } catch {
      setErrorMsg('Cannot reach backend on http://127.0.0.1:8000. Is the backend running?');
      setBackendStatus('offline');
    } finally {
      setLoading(false);
    }
  };

  // 1. Submit Hair Test (Questionnaire)
  const submitQuestionnaire = async () => {
    if (!assessmentId) return;
    setLoading(true);
    setErrorMsg('');
    const answersList = Object.entries(answers).map(([k, v]) => ({ question_key: k, answer_value: v }));
    try {
      const res = await apiFetch(`/api/v1/assessments/${assessmentId}/answers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answers: answersList, consent_confirmed: true })
      });
      if (res.ok) {
        setCurrentStep(2);
      } else {
        const err = await res.json();
        setErrorMsg(err.detail || 'Failed to submit answers.');
      }
    } catch {
      setErrorMsg('Error communicating with backend.');
    } finally {
      setLoading(false);
    }
  };

  // 2. Upload Photo (Photo Quality Engine)
  const handlePhotoUpload = async (angle: string, file: File) => {
    if (!assessmentId) {
      await createNewAssessment();
    }
    setUploadingAngle(angle);
    setErrorMsg('');

    const formData = new FormData();
    formData.append('angle', angle);
    formData.append('file', file);

    try {
      const res = await apiFetch(`/api/v1/assessments/${assessmentId}/photos`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        setUploadedPhotos(prev => ({
          ...prev,
          [angle]: {
            ...data,
            localUrl: URL.createObjectURL(file)
          }
        }));
      } else {
        setErrorMsg(data.detail || 'Photo rejected by quality engine.');
      }
    } catch {
      setErrorMsg('Failed to upload photo. Ensure backend is running.');
    } finally {
      setUploadingAngle(null);
    }
  };

  const fetchPhotos = async (assId: string) => {
    try {
      const res = await apiFetch(`/api/v1/assessments/${assId}/photos`);
      if (res.ok) {
        const photos = await res.json();
        const map: Record<string, any> = {};
        photos.forEach((p: any) => { map[p.angle] = p; });
        setUploadedPhotos(map);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // 3. Computer Vision Analysis
  const runAnalysis = async () => {
    if (!assessmentId) return;
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await apiFetch(`/api/v1/assessments/${assessmentId}/analyze`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setAnalysisData(data);
        setCurrentStep(3);
      } else {
        setErrorMsg(data.detail || 'Analysis could not be completed.');
      }
    } catch {
      setErrorMsg('Error running image analysis.');
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalysis = async (assId: string) => {
    try {
      const res = await apiFetch(`/api/v1/assessments/${assId}/analysis`);
      if (res.ok) {
        const data = await res.json();
        setAnalysisData(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // 4. Generate Report
  const generateReport = async () => {
    if (!assessmentId) return;
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await apiFetch(`/api/v1/assessments/${assessmentId}/report`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setReportData(data.report_data);
        setCurrentStep(4);
      } else {
        setErrorMsg(data.detail || 'Could not generate report.');
      }
    } catch {
      setErrorMsg('Error generating assessment report.');
    } finally {
      setLoading(false);
    }
  };

  const fetchReport = async (assId: string) => {
    try {
      const res = await apiFetch(`/api/v1/assessments/${assId}/report`);
      if (res.ok) {
        const data = await res.json();
        setReportData(data.report_data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const downloadPDF = () => {
    if (!assessmentId) return;
    window.open(`${API_BASE}/api/v1/assessments/${assessmentId}/report/pdf`, '_blank');
  };

  const uploadedCount = Object.keys(uploadedPhotos).length;

  return (
    <>
      {/* Top Navbar */}
      <nav className="navbar">
        <div className="brand">
          <span>Hair Health AI</span>
          <span className="brand-badge">Fast Testing Mode</span>
        </div>
        <div className="user-info">
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ 
              width: 8, height: 8, borderRadius: '50%', 
              background: backendStatus === 'online' ? '#10b981' : '#ef4444',
              display: 'inline-block' 
            }} />
            <span style={{ fontSize: 13, color: backendStatus === 'online' ? '#10b981' : '#f87171' }}>
              Backend: {backendStatus === 'online' ? 'Online (127.0.0.1:8000)' : 'Offline'}
            </span>
          </div>

          <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: 12 }} onClick={createNewAssessment}>
            <RefreshCw size={14} /> Reset Test
          </button>
        </div>
      </nav>

      <div className="container">
        {/* Backend offline warning banner */}
        {backendStatus === 'offline' && (
          <div className="warning-box" style={{ borderColor: 'var(--red)', background: 'rgba(239, 68, 68, 0.1)', color: '#fca5a5', marginBottom: 20 }}>
            <b>Backend is not responding.</b> Please ensure the backend is started by running <code>run_backend.bat</code> in the project directory.
            <button className="btn btn-secondary" style={{ marginLeft: 16, padding: '4px 10px', fontSize: 11 }} onClick={checkHealthAndInit}>
              Retry Connection
            </button>
          </div>
        )}

        {/* Pipeline Navigation Bar */}
        <div className="pipeline-bar">
          <div 
            className={`step-item ${currentStep === 1 ? 'active' : ''} ${currentStep > 1 ? 'completed' : ''}`}
            onClick={() => setCurrentStep(1)}
          >
            <div className="step-num">{currentStep > 1 ? <Check size={16} /> : 1}</div>
            <div>
              <div className="step-text">Hair Test</div>
              <div className="step-desc">Questionnaire</div>
            </div>
          </div>

          <div 
            className={`step-item ${currentStep === 2 ? 'active' : ''} ${currentStep > 2 ? 'completed' : ''}`}
            onClick={() => setCurrentStep(2)}
          >
            <div className="step-num">{currentStep > 2 ? <Check size={16} /> : 2}</div>
            <div>
              <div className="step-text">Photo Upload & Quality</div>
              <div className="step-desc">5-Angle OpenCV Check</div>
            </div>
          </div>

          <div 
            className={`step-item ${currentStep === 3 ? 'active' : ''} ${currentStep > 3 ? 'completed' : ''}`}
            onClick={() => setCurrentStep(3)}
          >
            <div className="step-num">{currentStep > 3 ? <Check size={16} /> : 3}</div>
            <div>
              <div className="step-text">Feature Extraction</div>
              <div className="step-desc">Pixel Segmentation</div>
            </div>
          </div>

          <div 
            className={`step-item ${currentStep === 4 ? 'active' : ''}`}
            onClick={() => setCurrentStep(4)}
          >
            <div className="step-num">4</div>
            <div>
              <div className="step-text">Assessment Report</div>
              <div className="step-desc">12-Section PDF</div>
            </div>
          </div>
        </div>

        {errorMsg && (
          <div className="warning-box" style={{ borderColor: 'var(--red)', color: '#fca5a5', marginBottom: 20 }}>
            {errorMsg}
          </div>
        )}

        {/* ----------------- STEP 1: HAIR TEST QUESTIONNAIRE ----------------- */}
        {currentStep === 1 && (
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
              <div>
                <h2 className="card-title">Module A — Hair Test Questionnaire</h2>
                <p className="card-subtitle">Values are pre-filled for quick testing. Change any field or proceed directly.</p>
              </div>
              <button className="btn btn-primary" onClick={submitQuestionnaire} disabled={loading}>
                {loading ? 'Saving...' : 'Save & Continue to Photos'} <ArrowRight size={16} />
              </button>
            </div>

            <div className="form-grid">
              <div className="form-group">
                <label className="form-label">Duration of Concern</label>
                <select className="select" value={answers.duration_of_concern} onChange={e => setAnswers({...answers, duration_of_concern: e.target.value})}>
                  <option value="less_than_3_months">&lt; 3 Months (Recent)</option>
                  <option value="3_to_6_months">3 to 6 Months</option>
                  <option value="6_to_12_months">6 to 12 Months</option>
                  <option value="over_1_year">Over 1 Year (Chronic)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Daily Shedding</label>
                <select className="select" value={answers.shedding_changed} onChange={e => setAnswers({...answers, shedding_changed: e.target.value})}>
                  <option value="yes_significant">Yes, significant daily increase</option>
                  <option value="yes_slight">Yes, slight increase</option>
                  <option value="no">Normal / No increase</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Hairline Change</label>
                <select className="select" value={answers.hairline_changed} onChange={e => setAnswers({...answers, hairline_changed: e.target.value})}>
                  <option value="receding_temples">Temples receding</option>
                  <option value="overall_hairline_moving_back">Hairline shifting back</option>
                  <option value="no_change">No change</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Crown / Vertex Thinning</label>
                <select className="select" value={answers.crown_thinner} onChange={e => setAnswers({...answers, crown_thinner: e.target.value})}>
                  <option value="yes_noticeably">Yes, noticeably thinner</option>
                  <option value="yes_slightly">Yes, slightly</option>
                  <option value="no">No</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Scalp Visible</label>
                <select className="select" value={answers.scalp_visible} onChange={e => setAnswers({...answers, scalp_visible: e.target.value})}>
                  <option value="yes_crown">Yes, visible at crown</option>
                  <option value="yes_front">Yes, near hairline</option>
                  <option value="yes_throughout">Yes, diffuse throughout</option>
                  <option value="no">No, scalp well covered</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Scalp Discomfort / Flaking</label>
                <select className="select" value={answers.dandruff_flaking} onChange={e => setAnswers({...answers, dandruff_flaking: e.target.value})}>
                  <option value="dry_white_flakes">Dry white flakes</option>
                  <option value="oily_yellow_flakes">Oily yellowish flakes</option>
                  <option value="none">None</option>
                </select>
              </div>
            </div>

            <div style={{ marginTop: 24, display: 'flex', justifyContent: 'flex-end' }}>
              <button className="btn btn-primary" onClick={submitQuestionnaire} disabled={loading}>
                {loading ? 'Saving...' : 'Save & Proceed to Photos'} <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* ----------------- STEP 2: PHOTO UPLOAD & QUALITY ENGINE ----------------- */}
        {currentStep === 2 && (
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
              <div>
                <h2 className="card-title">Module B & C — Photo Collection & Quality Engine</h2>
                <p className="card-subtitle">
                  Upload photos for the 5 standard angles. OpenCV will immediately evaluate blur, lighting brightness, and contrast.
                </p>
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <button 
                  className="btn btn-primary" 
                  onClick={runAnalysis}
                  disabled={uploadedCount === 0 || loading}
                >
                  <Sparkles size={16} /> {loading ? 'Analyzing...' : `Analyze (${uploadedCount} uploaded)`}
                </button>
              </div>
            </div>

            <div className="angles-grid">
              {REQUIRED_ANGLES.map(ang => {
                const photo = uploadedPhotos[ang.key];
                const q = photo?.quality_details;
                const status = photo?.quality_status || 'pending';
                const isUploading = uploadingAngle === ang.key;

                return (
                  <div key={ang.key} className={`angle-card ${photo ? 'has-photo' : ''}`}>
                    <div className="angle-header">
                      <span className="angle-name">{ang.label}</span>
                      <span className={`quality-badge badge-${status}`}>
                        {status.replace('_', ' ')}
                      </span>
                    </div>

                    <input 
                      type="file" 
                      accept="image/jpeg,image/png,image/jpg" 
                      style={{ display: 'none' }}
                      ref={el => { fileInputRefs.current[ang.key] = el; }}
                      onChange={e => {
                        const file = e.target.files?.[0];
                        if (file) handlePhotoUpload(ang.key, file);
                      }}
                    />

                    <div 
                      className="angle-preview-box"
                      onClick={() => fileInputRefs.current[ang.key]?.click()}
                    >
                      {photo?.localUrl ? (
                        <img src={photo.localUrl} alt={ang.label} />
                      ) : (
                        <div style={{ textAlign: 'center', padding: 12 }}>
                          {isUploading ? (
                            <RefreshCw className="animate-spin" size={24} style={{ color: 'var(--teal-light)' }} />
                          ) : (
                            <>
                              <Camera size={26} style={{ color: 'var(--border-light)', marginBottom: 8 }} />
                              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Click to Upload</div>
                            </>
                          )}
                        </div>
                      )}
                    </div>

                    <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>{ang.desc}</p>

                    {q && (
                      <div className="quality-metrics">
                        <div><b>Blur score:</b> {q.blur_score} {q.is_blurry ? '⚠️ Blur' : '✓ Sharp'}</div>
                        <div><b>Brightness:</b> {q.brightness_score}/255</div>
                        <div><b>Resolution:</b> {q.resolution?.width}×{q.resolution?.height}</div>
                        {q.warnings?.length > 0 && (
                          <div style={{ color: 'var(--amber)', marginTop: 4 }}>
                            {q.warnings.join(' • ')}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <div style={{ marginTop: 28, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <button className="btn btn-secondary" onClick={() => setCurrentStep(1)}>
                Edit Questionnaire
              </button>

              <button 
                className="btn btn-primary" 
                onClick={runAnalysis}
                disabled={uploadedCount === 0 || loading}
              >
                {loading ? 'Running Computer Vision...' : 'Run Feature Extraction'} <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* ----------------- STEP 3: COMPUTER VISION FEATURE EXTRACTION ----------------- */}
        {currentStep === 3 && (
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
              <div>
                <h2 className="card-title">Module D & E — Computer Vision Feature Extraction</h2>
                <p className="card-subtitle">
                  Adaptive Otsu pixel segmentation, CLAHE illumination normalization, and regional comparison.
                </p>
              </div>
              <button className="btn btn-primary" onClick={generateReport} disabled={loading}>
                {loading ? 'Generating...' : 'Generate Health Report'} <ArrowRight size={16} />
              </button>
            </div>

            <div className="angles-grid" style={{ marginBottom: 20 }}>
              {analysisData?.analyses && Object.entries(analysisData.analyses).map(([angle, data]: any) => {
                const feat = data.feature_data || {};
                const conf = data.confidence_data || {};
                return (
                  <div key={angle} className="angle-card">
                    <div className="angle-header">
                      <span className="angle-name">{angle.replace('_', ' ').toUpperCase()}</span>
                      <span className="quality-badge badge-acceptable">
                        {conf.overall_feature_confidence ? `${Math.round(conf.overall_feature_confidence * 100)}% Conf` : 'Analyzed'}
                      </span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 10 }}>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                          <span>Hair Pixel Ratio</span>
                          <b>{feat.hair_pixel_ratio ? `${(feat.hair_pixel_ratio * 100).toFixed(1)}%` : 'N/A'}</b>
                        </div>
                        <div style={{ height: 6, background: '#374151', borderRadius: 4, overflow: 'hidden', marginTop: 4 }}>
                          <div style={{ height: '100%', width: `${(feat.hair_pixel_ratio || 0) * 100}%`, background: 'var(--teal-light)' }} />
                        </div>
                      </div>

                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                          <span>Scalp Contrast Ratio</span>
                          <b>{feat.scalp_pixel_ratio ? `${(feat.scalp_pixel_ratio * 100).toFixed(1)}%` : 'N/A'}</b>
                        </div>
                        <div style={{ height: 6, background: '#374151', borderRadius: 4, overflow: 'hidden', marginTop: 4 }}>
                          <div style={{ height: '100%', width: `${(feat.scalp_pixel_ratio || 0) * 100}%`, background: 'var(--amber)' }} />
                        </div>
                      </div>

                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                        Lighting uniformity: <b>{Math.round((feat.lighting_uniformity || 0) * 100)}%</b>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {analysisData?.regional_comparison?.observations?.length > 0 && (
              <div className="card" style={{ background: 'var(--bg-card)', marginBottom: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--teal-light)', marginBottom: 8 }}>
                  Cross-Regional Comparison Findings:
                </h3>
                <ul className="report-list">
                  {analysisData.regional_comparison.observations.map((obs: string, idx: number) => (
                    <li key={idx}>{obs}</li>
                  ))}
                </ul>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <button className="btn btn-secondary" onClick={() => setCurrentStep(2)}>Back to Photos</button>
              <button className="btn btn-primary" onClick={generateReport} disabled={loading}>
                {loading ? 'Synthesizing Report...' : 'Generate 12-Section Health Report'} <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* ----------------- STEP 4: 12-SECTION REPORT ----------------- */}
        {currentStep === 4 && reportData && (
          <div className="card">
            <div className="report-header">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <h2 style={{ fontSize: 22, fontWeight: 800, color: '#fff' }}>
                    Hair Health Intelligence Report
                  </h2>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
                    Assessment ID: <b>{reportData.assessment_id}</b> &nbsp;|&nbsp; 
                    Generated: {reportData.generated_at?.slice(0, 10)} &nbsp;|&nbsp; 
                    Engine: v{reportData.engine_version}
                  </div>
                </div>

                <button className="btn btn-primary" onClick={downloadPDF}>
                  <Download size={16} /> Download Official PDF
                </button>
              </div>
            </div>

            <div className="report-grid">
              <div className="report-section">
                <h3><CheckCircle2 size={16} /> 1. User-Reported Evidence</h3>
                <ul className="report-list">
                  {reportData['2_user_reported_concerns']?.map((c: any, i: number) => (
                    <li key={i}><b>{c.category.replace('_', ' ').toUpperCase()}:</b> {c.finding}</li>
                  ))}
                </ul>
              </div>

              <div className="report-section">
                <h3><Camera size={16} /> 2. Photo Quality Summary</h3>
                <ul className="report-list">
                  {reportData['4_photo_quality_summary'] && Object.entries(reportData['4_photo_quality_summary']).map(([ang, q]: any) => (
                    <li key={ang}><b>{ang.replace('_', ' ')}:</b> {q.status.toUpperCase()} (Blur: {q.blur_score}, Brightness: {q.brightness_score})</li>
                  ))}
                </ul>
              </div>

              <div className="report-section">
                <h3><Shield size={16} /> 3. Visual Image Findings</h3>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>
                  {reportData['5_image_analysis_results']?.density_statement}
                </div>
                <ul className="report-list">
                  {reportData['5_image_analysis_results']?.observations?.map((obs: string, i: number) => (
                    <li key={i}>{obs}</li>
                  ))}
                </ul>
              </div>

              <div className="report-section">
                <h3><AlertTriangle size={16} /> 4. Patterns Worth Monitoring</h3>
                <ul className="report-list">
                  {reportData['7_areas_worth_monitoring']?.map((p: any, i: number) => (
                    <li key={i}><b>{p.pattern_name}:</b> {p.description}</li>
                  ))}
                </ul>
              </div>

              <div className="report-section">
                <h3><Sparkles size={16} /> 5. Practical Hair Care Guidance</h3>
                <ul className="report-list">
                  {reportData['8_practical_recommendations']?.map((rec: string, i: number) => (
                    <li key={i}>{rec}</li>
                  ))}
                </ul>
              </div>

              <div className="report-section">
                <h3><FileText size={16} /> 6. Professional Care Guidance</h3>
                <ul className="report-list">
                  {reportData['9_professional_care_guidance']?.map((g: string, i: number) => (
                    <li key={i}>{g}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="disclaimer-banner">
              <b>EDUCATIONAL DISCLAIMER:</b> {reportData['12_educational_disclaimer']}
            </div>

            <div style={{ marginTop: 24, display: 'flex', justifyContent: 'space-between' }}>
              <button className="btn btn-secondary" onClick={() => setCurrentStep(2)}>Upload More Photos</button>
              <button className="btn btn-primary" onClick={downloadPDF}>
                <Download size={16} /> Download PDF
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
