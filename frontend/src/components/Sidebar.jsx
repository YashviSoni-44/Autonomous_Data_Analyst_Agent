import React, { useState, useRef, useEffect } from 'react';
import { FileSpreadsheet, FileUp, CheckCircle2, AlertCircle, Database, Loader2, RefreshCw, Compass, Sparkles, X, FileText } from 'lucide-react';
import { BACKEND_URL } from '../config';

export default function Sidebar({
  datasetInfo,
  setDatasetInfo,
  profile,
  setProfile,
  setConversationHistory,
  setSessionId,
  setFollowUpQuestions,
  setAutonomousReport,
  onNavigateTab
}) {
  const [file, setFile] = useState(null);
  const [useSample, setUseSample] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const tableScrollRef = useRef(null);

  useEffect(() => {
    const el = tableScrollRef.current;
    if (!el) return;

    const handleWheel = (e) => {
      if (el.scrollWidth > el.clientWidth && e.deltaY !== 0) {
        e.preventDefault();
        el.scrollLeft += e.deltaY;
      }
    };

    el.addEventListener('wheel', handleWheel, { passive: false });
    return () => {
      el.removeEventListener('wheel', handleWheel);
    };
  }, [datasetInfo?.tables]);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setUseSample(false);
      setErrorMsg('');
    }
  };

  const handleLoadDataset = async () => {
    setLoading(true);
    setErrorMsg('');
    setSuccessMsg('');

    try {
      let formData = new FormData();
      if (useSample) {
        // Fetch sample file from backend or public sample
        const sampleRes = await fetch('/data/sample_dataset.csv');
        let sampleBlob;
        if (sampleRes.ok) {
          sampleBlob = await sampleRes.blob();
        } else {
          // Fallback content if file fetch isn't direct
          const csvText = `Category,Product,Sales_Amount,Quantity,Region\nElectronics,Laptop,1200,2,North\nElectronics,Phone,800,5,South\nFurniture,Chair,150,10,East\nFurniture,Desk,450,3,West\nOffice,Pen,20,50,North\nElectronics,Tablet,600,4,East`;
          sampleBlob = new Blob([csvText], { type: 'text/csv' });
        }
        formData.append('file', sampleBlob, 'sample_dataset.csv');
      } else if (file) {
        formData.append('file', file);
      } else {
        setErrorMsg('Please select a file or check sample dataset.');
        setLoading(false);
        return;
      }

      const res = await fetch(`${BACKEND_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Upload failed');
      }

      const data = await res.json();
      setDatasetInfo({
        dataset_id: data.dataset_id,
        tables: data.tables,
      });
      setSuccessMsg(`Loaded dataset! ID: ${data.dataset_id}`);

      // Reset conversation and autonomous report when a new dataset is loaded
      if (setConversationHistory) setConversationHistory([]);
      if (setSessionId) setSessionId(null);
      if (setFollowUpQuestions) setFollowUpQuestions([]);
      if (setAutonomousReport) setAutonomousReport(null);

      // Automatically fetch profiling data
      try {
        const profRes = await fetch(`${BACKEND_URL}/profile/${data.dataset_id}`);
        if (profRes.ok) {
          const profData = await profRes.json();
          setProfile(profData);
        }
      } catch (profErr) {
        console.warn('Profiling error:', profErr);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to connect to backend.');
    } finally {
      setLoading(false);
    }
  };

  const getQualityBadge = (score) => {
    if (score >= 85) return <span className="badge-tag badge-green">🟢 High ({score}/100)</span>;
    if (score >= 65) return <span className="badge-tag badge-yellow">🟡 Moderate ({score}/100)</span>;
    return <span className="badge-tag badge-red">🔴 Warning ({score}/100)</span>;
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-badge">⚡</div>
        <div>
          <h1 className="brand-name">Data Analyst</h1>
          <div className="brand-subtitle">Autonomous AI Engine</div>
        </div>
      </div>

      <div style={{ marginBottom: '1rem' }}>
        <h3 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem', fontWeight: 600 }}>
          📂 DATA SOURCE
        </h3>

        <label
          htmlFor="file-upload"
          className="upload-card"
          onDragOver={(e) => e.preventDefault()}
        >
          {file ? (
            <div className="selected-file-box" onClick={(e) => e.stopPropagation()}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', overflow: 'hidden' }}>
                <FileSpreadsheet size={22} color="var(--accent-emerald)" style={{ flexShrink: 0 }} />
                <div style={{ textAlign: 'left', overflow: 'hidden' }}>
                  <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-main)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', maxWidth: '140px' }}>
                    {file.name}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--accent-emerald)' }}>
                    ✓ {(file.size / 1024).toFixed(1)} KB ready
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setFile(null);
                }}
                style={{
                  background: 'rgba(255, 255, 255, 0.1)',
                  border: 'none',
                  borderRadius: '50%',
                  width: '22px',
                  height: '22px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  color: 'var(--text-muted)'
                }}
                title="Remove file"
              >
                <X size={13} />
              </button>
            </div>
          ) : (
            <>
              <div className="upload-icon-wrapper">
                <FileSpreadsheet size={22} />
              </div>
              <div className="upload-title">Import CSV or Excel</div>
              <div className="upload-subtitle">Click to browse or drag & drop</div>
              <div className="format-pills">
                <span className="format-pill">CSV</span>
                <span className="format-pill">XLSX</span>
                <span className="format-pill">XLS</span>
              </div>
            </>
          )}
          <input
            id="file-upload"
            type="file"
            accept=".csv, .xlsx, .xls"
            className="file-input"
            onChange={handleFileChange}
          />
        </label>

        <div className="sample-toggle-container">
          <input
            type="checkbox"
            id="sample-checkbox"
            className="custom-checkbox"
            checked={useSample}
            onChange={(e) => {
              setUseSample(e.target.checked);
              if (e.target.checked) setFile(null);
            }}
          />
          <label htmlFor="sample-checkbox" style={{ cursor: 'pointer', flex: 1 }}>
            Use sample sales dataset
          </label>
        </div>

        <button
          className="btn-primary"
          onClick={handleLoadDataset}
          disabled={loading || (!file && !useSample)}
        >
          {loading ? <Loader2 size={16} className="spin-icon" style={{ animation: 'spin 1s linear infinite' }} /> : <Database size={16} />}
          <span>{loading ? 'Ingesting Data...' : '🚀 Load Dataset'}</span>
        </button>

        {errorMsg && (
          <div style={{ marginTop: '0.75rem', color: 'var(--accent-rose)', fontSize: '0.8rem', display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
            <AlertCircle size={14} />
            <span>{errorMsg}</span>
          </div>
        )}

        {successMsg && (
          <div style={{ marginTop: '0.75rem', color: 'var(--accent-emerald)', fontSize: '0.8rem', display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
            <CheckCircle2 size={14} />
            <span>{successMsg}</span>
          </div>
        )}
      </div>

      {datasetInfo && (
        <div className="dataset-status-box">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Active Dataset:</span>
            <span className="dataset-id-tag">{datasetInfo.dataset_id}</span>
          </div>

          <div style={{ fontSize: '0.8rem', color: 'var(--text-subtle)', marginBottom: '0.4rem' }}>
            Tables loaded:
          </div>
          <div ref={tableScrollRef} className="table-tags-scroll-container">
            {datasetInfo.tables && datasetInfo.tables.map((t, idx) => (
              <span key={idx} className="table-tag" title={t}>
                {t}
              </span>
            ))}
          </div>

          {profile && (
            <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Quality Score:</span>
              {getQualityBadge(profile.overall_quality_score)}
            </div>
          )}

          <button
            className="btn-primary"
            style={{
              marginTop: '0.85rem',
              background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.2) 0%, rgba(232, 255, 138, 0.2) 100%)',
              border: '1px solid var(--accent-cyan)',
              color: 'var(--text-main)',
              fontSize: '0.82rem'
            }}
            onClick={() => {
              if (onNavigateTab) onNavigateTab('autonomous');
            }}
          >
            <Compass size={15} color="var(--accent-cyan)" />
            <span>⚡ Autonomous Deep Dive</span>
          </button>
        </div>
      )}
    </aside>
  );
}
