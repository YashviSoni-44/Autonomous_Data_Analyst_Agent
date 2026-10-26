import React, { useState } from 'react';
import { ShieldCheck, AlertTriangle, RefreshCw, Table as TableIcon, Layers, FileSpreadsheet, Sparkles } from 'lucide-react';
import { BACKEND_URL } from '../config';

export default function DataProfiling({ datasetInfo, profile, setProfile }) {
  const [loading, setLoading] = useState(false);
  const [selectedTable, setSelectedTable] = useState(null);

  const fetchProfile = async () => {
    if (!datasetInfo?.dataset_id) return;
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/profile/${datasetInfo.dataset_id}`);
      if (res.ok) {
        const data = await res.json();
        setProfile(data);
      }
    } catch (err) {
      console.error('Failed to refresh profile:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!datasetInfo?.dataset_id) {
    return (
      <div className="tab-view">
        <div className="empty-state">
          <div className="empty-state-icon">
            <FileSpreadsheet size={32} />
          </div>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Data Quality & Automated Profiling</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Please load a dataset from the sidebar to view automated schema profiling, data health metrics, candidate keys, and quality warnings.
          </p>
        </div>
      </div>
    );
  }

  const score = profile?.overall_quality_score ?? 100;
  const getQualityBadge = (s) => {
    if (s >= 85) return <span className="badge-tag badge-green">🟢 High Quality</span>;
    if (s >= 65) return <span className="badge-tag badge-yellow">🟡 Moderate Warnings</span>;
    return <span className="badge-tag badge-red">🔴 Quality Issues</span>;
  };

  const tables = profile?.tables || [];
  const currentTable = selectedTable ? tables.find(t => t.table_name === selectedTable) || tables[0] : tables[0];

  return (
    <div className="tab-view">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>🔍 Automated Dataset Profiling & Health</h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-subtle)' }}>
            Deep schema inspection, null rates, candidate primary keys, and data health scores.
          </p>
        </div>

        <button className="btn-copy" onClick={fetchProfile} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin-icon' : ''} />
          <span>{loading ? 'Refreshing...' : 'Refresh Profile'}</span>
        </button>
      </div>

      {profile && (
        <>
          {/* KPI Metrics */}
          <div className="metrics-grid">
            <div className="metric-card-react">
              <div className="metric-title">Overall Quality Score</div>
              <div className="metric-value">{score} / 100</div>
              <div>{getQualityBadge(score)}</div>
            </div>
            <div className="metric-card-react">
              <div className="metric-title">Total Tables</div>
              <div className="metric-value">{profile.total_tables || profile.tables?.length || 0}</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-subtle)' }}>Loaded in DuckDB</div>
            </div>
            <div className="metric-card-react">
              <div className="metric-title">Total Rows</div>
              <div className="metric-value">{(profile.total_rows || 0).toLocaleString()}</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-subtle)' }}>Across all tables</div>
            </div>
            <div className="metric-card-react">
              <div className="metric-title">Total Columns</div>
              <div className="metric-value">{profile.total_columns || 0}</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-subtle)' }}>Schema attributes</div>
            </div>
          </div>

          {/* Health Warnings */}
          <div style={{ marginBottom: '2rem' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <AlertTriangle size={16} color="var(--accent-amber)" />
              <span>Data Health & Quality Alerts</span>
            </h3>

            {profile.warnings && profile.warnings.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {profile.warnings.map((w, idx) => (
                  <div key={idx} style={{ padding: '0.75rem 1rem', background: 'rgba(251, 191, 36, 0.08)', borderLeft: '4px solid var(--accent-amber)', borderRadius: '0 8px 8px 0', fontSize: '0.88rem', color: '#FDE68A' }}>
                    ⚠️ {w}
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '0.75rem 1rem', background: 'rgba(52, 211, 153, 0.08)', borderLeft: '4px solid var(--accent-emerald)', borderRadius: '0 8px 8px 0', fontSize: '0.88rem', color: '#A7F3D0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldCheck size={16} />
                <span>🎉 No data quality issues or warnings detected! Dataset is clean and ready for analysis.</span>
              </div>
            )}
          </div>

          {/* Table Selector & Schema Details */}
          <div>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <TableIcon size={16} color="var(--accent-cyan)" />
              <span>Table & Schema Deep-Dive</span>
            </h3>

            {/* Table Tabs */}
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
              {tables.map((t, idx) => (
                <button
                  key={idx}
                  className={`nav-tab ${currentTable?.table_name === t.table_name ? 'active' : ''}`}
                  onClick={() => setSelectedTable(t.table_name)}
                >
                  <Layers size={14} />
                  <span>{t.table_name}</span>
                  <span style={{ fontSize: '0.72rem', opacity: 0.7 }}>({t.row_count} rows)</span>
                </button>
              ))}
            </div>

            {/* Current Table Schema */}
            {currentTable && (
              <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div>
                    <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--accent-lime)' }}>
                      Table: <code>{currentTable.table_name}</code>
                    </h4>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-subtle)' }}>
                      {currentTable.row_count.toLocaleString()} rows × {currentTable.column_count} columns | Quality: {currentTable.quality_score}/100
                    </div>
                  </div>
                  {currentTable.duplicate_rows > 0 && (
                    <span className="badge-tag badge-yellow">
                      ⚠️ Duplicate Rows: {currentTable.duplicate_rows}
                    </span>
                  )}
                </div>

                {/* Columns Table */}
                <div className="table-wrapper">
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>Column</th>
                        <th>Type</th>
                        <th>Nulls</th>
                        <th>Unique</th>
                        <th>Sample Values</th>
                        <th>Min / Max</th>
                        <th>Mean</th>
                        <th>Flags</th>
                      </tr>
                    </thead>
                    <tbody>
                      {currentTable.columns?.map((c, colIdx) => {
                        const flags = [];
                        if (c.is_candidate_pk) flags.push('🔑 Key');
                        if (c.is_datetime) flags.push('📅 Date');
                        if (c.null_count > 0) flags.push(`⚠️ ${c.null_percentage}% Null`);

                        return (
                          <tr key={colIdx}>
                            <td style={{ fontWeight: 600, color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>
                              {c.name}
                            </td>
                            <td>
                              <code style={{ color: 'var(--accent-cyan)', fontSize: '0.8rem' }}>{c.data_type}</code>
                            </td>
                            <td>
                              {c.null_count} ({c.null_percentage}%)
                            </td>
                            <td>{c.distinct_count}</td>
                            <td style={{ maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>
                              {c.sample_values?.join(', ') || '-'}
                            </td>
                            <td style={{ fontSize: '0.8rem', color: 'var(--text-subtle)' }}>
                              {c.min_val !== null && c.max_val !== null ? `${c.min_val} / ${c.max_val}` : '-'}
                            </td>
                            <td>{c.mean_val !== null && c.mean_val !== undefined ? c.mean_val : '-'}</td>
                            <td>
                              {flags.length > 0 ? (
                                <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                                  {flags.map((f, fIdx) => (
                                    <span key={fIdx} style={{ fontSize: '0.72rem', background: 'rgba(255,255,255,0.05)', padding: '0.1rem 0.4rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
                                      {f}
                                    </span>
                                  ))}
                                </div>
                              ) : (
                                <span style={{ color: 'var(--accent-emerald)', fontSize: '0.78rem' }}>✅ Clean</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
