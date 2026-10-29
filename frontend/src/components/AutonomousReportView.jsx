import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  TrendingUp,
  AlertTriangle,
  Link2,
  Compass,
  BarChart3,
  RefreshCw,
  Loader2,
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  Layers,
  Lightbulb,
  FileDown,
  FileText,
  Copy,
  Check,
  Download,
  Maximize2
} from 'lucide-react';
import ChartModal from './ChartModal';
import { BACKEND_URL } from '../config';
import {
  exportReportToMarkdown,
  exportReportToPDF,
  copyReportSummaryToClipboard
} from '../utils/exportUtils';

export default function AutonomousReportView({
  datasetInfo,
  onSelectQuestion,
  report: externalReport,
  setReport: setExternalReport,
  loading: externalLoading,
  setLoading: setExternalLoading,
}) {
  const [localReport, setLocalReport] = useState(null);
  const [localLoading, setLocalLoading] = useState(false);
  const report = externalReport !== undefined ? externalReport : localReport;
  const setReport = setExternalReport || setLocalReport;
  const loading = externalLoading !== undefined ? externalLoading : localLoading;
  const setLoading = setExternalLoading || setLocalLoading;
  
  const [errorMsg, setErrorMsg] = useState('');
  const [selectedChartBase64, setSelectedChartBase64] = useState(null);
  const [pdfExporting, setPdfExporting] = useState(false);
  const [copied, setCopied] = useState(false);

  const reportContainerRef = useRef(null);

  const fetchAutonomousReport = async (retryCount = 0, force = false) => {
    if (!datasetInfo?.dataset_id) return;
    setLoading(true);
    setErrorMsg('');

    try {
      const url = `${BACKEND_URL}/analyze/${datasetInfo.dataset_id}${force ? '?force=true' : ''}`;
      const res = await fetch(url, {
        method: 'POST',
      });
      if (!res.ok) {
        const errData = await res.json();
        if (retryCount === 0 && (errData.detail?.includes('No tables found') || res.status === 500)) {
          await new Promise((r) => setTimeout(r, 600));
          return fetchAutonomousReport(1, force);
        }
        throw new Error(errData.detail || 'Autonomous analysis failed.');
      }
      const data = await res.json();
      setReport(data);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to fetch autonomous investigation report.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (datasetInfo?.dataset_id) {
      if (!report && !loading) {
        fetchAutonomousReport(0, false);
      }
    } else {
      setReport(null);
      setErrorMsg('');
    }
  }, [datasetInfo?.dataset_id]);

  const handleExportPDF = async () => {
    if (!reportContainerRef.current || !report || pdfExporting) return;
    try {
      setPdfExporting(true);
      await exportReportToPDF(reportContainerRef.current, report, datasetInfo);
    } catch (err) {
      console.error('PDF generation error:', err);
      alert('Failed to generate PDF. Please try again.');
    } finally {
      setPdfExporting(false);
    }
  };

  const handleExportMarkdown = () => {
    if (!report) return;
    exportReportToMarkdown(report, datasetInfo);
  };

  const handleCopySummary = async () => {
    if (!report || copied) return;
    const ok = await copyReportSummaryToClipboard(report);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2400);
    }
  };

  const handleDownloadChartPNG = (chartBase64) => {
    if (!chartBase64) return;
    const link = document.createElement('a');
    link.href = `data:image/png;base64,${chartBase64}`;
    link.download = `Autonomous_Chart_${report?.table_name || 'analysis'}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!datasetInfo?.dataset_id) {
    return (
      <div className="tab-view">
        <div className="empty-state">
          <div className="empty-state-icon">
            <Compass size={32} color="var(--accent-lime)" />
          </div>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Autonomous Investigation Mode</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
            Upload a CSV or Excel dataset to trigger autonomous zero-prompt exploration, KPI discovery, outlier scans, and executive briefings.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="tab-view">
      <ChartModal imageBase64={selectedChartBase64} onClose={() => setSelectedChartBase64(null)} />

      {/* Top Header & Action Toolbar */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '1rem',
        marginBottom: '1.25rem',
        paddingBottom: '0.75rem',
        borderBottom: '1px solid var(--border-color)'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <h2 style={{ fontSize: '1.3rem', fontWeight: 800 }}>⚡ Autonomous Executive Briefing</h2>
            <span className="badge-tag badge-green" style={{ fontSize: '0.75rem' }}>Zero-Prompt Mode</span>
            {report?.table_name && (
              <span className="badge-tag badge-cyan" style={{ fontSize: '0.75rem' }}>
                Table: {report.table_name}
              </span>
            )}
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-subtle)', marginTop: '0.2rem' }}>
            Multi-agent exploratory synthesis • Generated {report?.generated_at || 'Just now'}
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          {report && (
            <>
              <button
                className="chip-btn"
                onClick={handleCopySummary}
                title="Copy Executive Summary to Clipboard"
                style={{ fontSize: '0.8rem', padding: '0.45rem 0.8rem' }}
              >
                {copied ? <Check size={14} color="var(--accent-lime)" /> : <Copy size={14} />}
                <span>{copied ? 'Copied!' : 'Copy Summary'}</span>
              </button>

              <button
                className="chip-btn"
                onClick={handleExportMarkdown}
                title="Download formatted Markdown dossier"
                style={{ fontSize: '0.8rem', padding: '0.45rem 0.8rem' }}
              >
                <FileText size={14} color="var(--accent-cyan)" />
                <span>Export MD</span>
              </button>

              <button
                className="chip-btn"
                onClick={handleExportPDF}
                disabled={pdfExporting}
                title="Export high-resolution Executive PDF Report"
                style={{
                  fontSize: '0.8rem',
                  padding: '0.45rem 0.85rem',
                  borderColor: 'rgba(232, 255, 138, 0.4)',
                  color: 'var(--accent-lime)'
                }}
              >
                {pdfExporting ? (
                  <Loader2 size={14} className="spin-icon" style={{ animation: 'spin 1s linear infinite' }} />
                ) : (
                  <FileDown size={14} />
                )}
                <span>{pdfExporting ? 'Generating PDF...' : 'Export Executive PDF'}</span>
              </button>
            </>
          )}

          <button
            className="btn-primary"
            style={{ width: 'auto', padding: '0.45rem 0.9rem', fontSize: '0.8rem' }}
            onClick={() => fetchAutonomousReport(0, true)}
            disabled={loading}
          >
            {loading ? (
              <Loader2 size={14} className="spin-icon" style={{ animation: 'spin 1s linear infinite' }} />
            ) : (
              <RefreshCw size={14} />
            )}
            <span>{loading ? 'Investigating...' : 'Re-Run Deep Dive'}</span>
          </button>
        </div>
      </div>

      {errorMsg && (
        <div style={{
          padding: '1rem',
          background: 'rgba(251, 113, 133, 0.1)',
          border: '1px solid var(--accent-rose)',
          borderRadius: '8px',
          color: 'var(--accent-rose)',
          marginBottom: '1rem',
          display: 'flex',
          gap: '0.5rem',
          alignItems: 'center'
        }}>
          <AlertTriangle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}

      {loading && !report && (
        <div className="agent-response-card" style={{ textAlign: 'center', padding: '3.5rem' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.8rem', color: 'var(--accent-lime)' }}>
            <Sparkles className="spin-icon" size={28} style={{ animation: 'spin 1.5s linear infinite' }} />
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Autonomous Analyst Formulating Hypotheses…</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', maxWidth: '480px' }}>
              Scanning columns • Computing dimensional Pareto breakdowns • Testing Pearson correlation matrix • Extracting IQR outliers
            </p>
          </div>
        </div>
      )}

      {/* Printable Report Container */}
      {report && (
        <div
          ref={reportContainerRef}
          className="printable-report-container"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '1.25rem',
            padding: '0.25rem'
          }}
        >
          {/* Executive Briefing Banner */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.95) 100%)',
            border: '1px solid rgba(232, 255, 138, 0.35)',
            borderRadius: '12px',
            padding: '1.4rem',
            boxShadow: '0 8px 30px rgba(0, 0, 0, 0.35)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldCheck size={20} color="var(--accent-lime)" />
                <span style={{ fontWeight: 800, color: 'var(--accent-lime)', fontSize: '1rem', letterSpacing: '0.02em' }}>
                  Executive Intelligence Briefing
                </span>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-subtle)', background: 'rgba(255,255,255,0.05)', padding: '0.2rem 0.6rem', borderRadius: '4px' }}>
                Verified by Multi-Agent Critic
              </span>
            </div>
            <p style={{ color: 'var(--text-main)', fontSize: '0.94rem', lineHeight: 1.65, margin: 0 }}>
              {report.executive_summary}
            </p>
          </div>

          {/* High-Level KPI Cards */}
          {report.kpi_metrics?.length > 0 && (
            <div>
              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.6rem', letterSpacing: '0.05em' }}>
                CORE BUSINESS METRICS & KPI ANCHORS
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
                {report.kpi_metrics.map((kpi, kIdx) => (
                  <div
                    key={kIdx}
                    className="metric-card"
                    style={{
                      padding: '1.1rem',
                      background: 'var(--bg-card)',
                      border: '1px solid var(--border-color)',
                      transition: 'transform 0.2s ease, border-color 0.2s ease'
                    }}
                  >
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-subtle)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                      {kpi.label}
                    </div>
                    <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--accent-lime)', margin: '0.3rem 0' }}>
                      {kpi.value}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {kpi.subtext}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Strategic Findings & Chart Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: report.chart_base64 ? '1.1fr 1fr' : '1fr',
            gap: '1rem',
            alignItems: 'stretch'
          }}>
            {/* Top Findings */}
            <div style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '10px',
              padding: '1.2rem',
              display: 'flex',
              flexDirection: 'column'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.9rem' }}>
                <Lightbulb size={18} color="var(--accent-amber)" />
                <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Key Discovered Findings</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', flex: 1 }}>
                {report.top_findings?.map((finding, fIdx) => (
                  <div key={fIdx} style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.65rem',
                    padding: '0.7rem 0.85rem',
                    background: 'rgba(255, 255, 255, 0.02)',
                    borderRadius: '6px',
                    fontSize: '0.86rem',
                    borderLeft: '3px solid var(--accent-cyan)'
                  }}>
                    <CheckCircle2 size={15} color="var(--accent-cyan)" style={{ marginTop: '0.15rem', flexShrink: 0 }} />
                    <span style={{ color: 'var(--text-main)', lineHeight: 1.5 }}>{finding}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Auto-Generated Chart */}
            {report.chart_base64 && (
              <div style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border-color)',
                borderRadius: '10px',
                padding: '1.2rem',
                display: 'flex',
                flexDirection: 'column'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <BarChart3 size={18} color="var(--accent-cyan)" />
                    <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Autonomous Overview Visualization</span>
                  </div>

                  <div style={{ display: 'flex', gap: '0.35rem' }}>
                    <button
                      className="icon-btn"
                      onClick={() => handleDownloadChartPNG(report.chart_base64)}
                      title="Download PNG chart image"
                      style={{ padding: '0.25rem 0.45rem', fontSize: '0.75rem' }}
                    >
                      <Download size={13} />
                    </button>
                    <button
                      className="icon-btn"
                      onClick={() => setSelectedChartBase64(report.chart_base64)}
                      title="Enlarge chart modal"
                      style={{ padding: '0.25rem 0.45rem', fontSize: '0.75rem' }}
                    >
                      <Maximize2 size={13} />
                    </button>
                  </div>
                </div>

                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '220px' }}>
                  <img
                    src={`data:image/png;base64,${report.chart_base64}`}
                    alt="Autonomous Chart"
                    style={{
                      maxWidth: '100%',
                      maxHeight: '260px',
                      objectFit: 'contain',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      boxShadow: '0 4px 15px rgba(0,0,0,0.3)'
                    }}
                    onClick={() => setSelectedChartBase64(report.chart_base64)}
                  />
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-subtle)', marginTop: '0.5rem' }}>
                    Click visual to enlarge or inspect full resolution
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Correlations & Outliers Diagnostic Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
            {/* Outlier Scans */}
            <div style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '10px',
              padding: '1.2rem'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.8rem' }}>
                <AlertTriangle size={17} color="var(--accent-rose)" />
                <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Anomalies & Extreme Outlier Scan</span>
              </div>
              {report.anomalies_detected?.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
                  {report.anomalies_detected.map((ano, aIdx) => (
                    <div key={aIdx} style={{
                      padding: '0.7rem 0.85rem',
                      background: 'rgba(251, 113, 133, 0.05)',
                      border: '1px solid rgba(251, 113, 133, 0.25)',
                      borderRadius: '6px',
                      fontSize: '0.84rem'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                        <span style={{ fontWeight: 700, color: 'var(--text-main)' }}>{ano.column}</span>
                        <span className={`badge-tag ${ano.severity === 'High' ? 'badge-red' : 'badge-yellow'}`} style={{ fontSize: '0.7rem' }}>
                          {ano.severity} Severity
                        </span>
                      </div>
                      <div style={{ color: 'var(--text-muted)', lineHeight: 1.45 }}>{ano.details}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: '0.85rem', color: 'var(--text-subtle)', padding: '0.5rem 0' }}>
                  No extreme anomalies detected within standard IQR statistical boundaries.
                </div>
              )}
            </div>

            {/* Correlations */}
            <div style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '10px',
              padding: '1.2rem'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.8rem' }}>
                <Link2 size={17} color="var(--accent-purple)" />
                <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Correlation Matrix Discoveries</span>
              </div>
              {report.correlations?.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {report.correlations.map((c, cIdx) => (
                    <div key={cIdx} style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '0.6rem 0.8rem',
                      background: 'rgba(255, 255, 255, 0.03)',
                      borderRadius: '6px',
                      fontSize: '0.84rem'
                    }}>
                      <span style={{ color: 'var(--text-muted)' }}>
                        <strong>{c.var1}</strong> ↔ <strong>{c.var2}</strong>
                      </span>
                      <span className="badge-tag badge-cyan" style={{ fontSize: '0.72rem' }}>
                        r = {c.pearson > 0 ? `+${c.pearson}` : c.pearson} ({c.strength} {c.direction})
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: '0.85rem', color: 'var(--text-subtle)', padding: '0.5rem 0' }}>
                  Single numerical dimension detected; multi-variable correlation requires at least 2 metrics.
                </div>
              )}
            </div>
          </div>

          {/* Recommended Deep Dive Actions */}
          {report.recommended_actions?.length > 0 && (
            <div style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '10px',
              padding: '1.2rem'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.8rem' }}>
                <Compass size={18} color="var(--accent-lime)" />
                <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>
                  Recommended Deep-Dive Inquiries (Click to Ask Agent)
                </span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem' }}>
                {report.recommended_actions.map((q, qIdx) => (
                  <button
                    key={qIdx}
                    className="chip-btn"
                    style={{ fontSize: '0.82rem', padding: '0.55rem 0.9rem', textAlign: 'left' }}
                    onClick={() => {
                      if (onSelectQuestion) onSelectQuestion(q);
                    }}
                  >
                    <ArrowRight size={13} color="var(--accent-lime)" style={{ flexShrink: 0 }} />
                    <span>{q}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Dossier Footer Stamp */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '0.6rem 0',
            borderTop: '1px solid rgba(255, 255, 255, 0.06)',
            fontSize: '0.75rem',
            color: 'var(--text-subtle)'
          }}>
            <span>Autonomous Data Analyst Agent • Multi-Agent Engine</span>
            <span>Generated: {report.generated_at || new Date().toISOString().slice(0, 19).replace('T', ' ')}</span>
          </div>
        </div>
      )}
    </div>
  );
}
