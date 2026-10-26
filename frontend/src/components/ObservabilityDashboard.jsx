import React, { useState, useEffect } from 'react';
import { Activity, RefreshCw, CheckCircle, CheckCircle2, XCircle, AlertOctagon, Clock, RotateCcw, Cpu, Terminal, Copy, Check } from 'lucide-react';
import { BACKEND_URL } from '../config';

export default function ObservabilityDashboard() {
  const [stats, setStats] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState(null);

  const handleCopySql = (sql, id) => {
    if (!sql) return;
    navigator.clipboard.writeText(sql);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statsRes, healthRes] = await Promise.all([
        fetch(`${BACKEND_URL}/stats`),
        fetch(`${BACKEND_URL}/health`)
      ]);

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }

      if (healthRes.ok) {
        const healthData = await healthRes.json();
        setHealth(healthData);
      }
    } catch (err) {
      console.error('Observability fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="tab-view">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>📊 Real-Time Observability & Performance Metrics</h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-subtle)' }}>
            Monitor agent run stats, success rate, query execution latency, LLM retries, and error logs.
          </p>
        </div>

        <button className="btn-copy" onClick={fetchData} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin-icon' : ''} />
          <span>{loading ? 'Refreshing...' : 'Refresh Metrics'}</span>
        </button>
      </div>

      {/* Backend Health Status */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '10px' }}>
        <Cpu size={18} color="var(--accent-cyan)" />
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Backend Engine Status:</span>
        {health ? (
          <span className="badge-tag badge-green" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <CheckCircle size={12} /> {health.message || 'Active'}
          </span>
        ) : (
          <span className="badge-tag badge-red" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <AlertOctagon size={12} /> Unreachable
          </span>
        )}
      </div>

      {stats ? (
        <>
          {/* KPI Cards */}
          <div className="metrics-grid">
            <div className="metric-card-react">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="metric-title">Total Runs</span>
                <Activity size={16} color="var(--accent-lime)" />
              </div>
              <div className="metric-value">{stats.total_runs ?? 0}</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-subtle)' }}>Queries logged in SQLite</div>
            </div>

            <div className="metric-card-react">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="metric-title">Success Rate</span>
                <CheckCircle size={16} color="var(--accent-emerald)" />
              </div>
              <div className="metric-value">{stats.success_rate ?? 0}%</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-subtle)' }}>
                {stats.success_rate >= 90 ? '🟢 Excellent Reliability' : '🟡 Review failures'}
              </div>
            </div>

            <div className="metric-card-react">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="metric-title">Avg Latency</span>
                <Clock size={16} color="var(--accent-cyan)" />
              </div>
              <div className="metric-value">{stats.avg_latency_seconds ?? 0} s</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-subtle)' }}>Per analytical question</div>
            </div>

            <div className="metric-card-react">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="metric-title">Avg Retries</span>
                <RotateCcw size={16} color="var(--accent-purple)" />
              </div>
              <div className="metric-value">{stats.avg_retries ?? 0}</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-subtle)' }}>Self-correcting SQL retries</div>
            </div>
          </div>

          {/* Recent Query Execution Logs */}
          <div style={{ flex: 1, minHeight: '260px', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <h3 style={{ fontSize: '0.98rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.45rem', margin: 0 }}>
                <Terminal size={17} color="var(--accent-cyan)" />
                <span>Recent Query Execution Logs ({stats.recent_runs?.length || 0})</span>
              </h3>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-subtle)' }}>
                Auto-synced with chat queries & SQL executions
              </span>
            </div>

            {stats.recent_runs && stats.recent_runs.length > 0 ? (
              <div className="table-wrapper" style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
                <table className="custom-table">
                  <thead>
                    <tr>
                      <th style={{ width: '85px' }}>Status</th>
                      <th style={{ width: '130px' }}>Timestamp</th>
                      <th style={{ width: '80px' }}>Dataset</th>
                      <th style={{ minWidth: '220px' }}>Question Asked</th>
                      <th style={{ minWidth: '240px' }}>Executed SQL</th>
                      <th style={{ width: '85px' }}>Latency</th>
                      <th style={{ width: '70px' }}>Retries</th>
                      <th style={{ minWidth: '220px' }}>Reasoning</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.recent_runs.map((run, idx) => (
                      <tr key={run.id || idx}>
                        <td>
                          {run.success ? (
                            <span className="badge-tag badge-green" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.72rem' }}>
                              <CheckCircle2 size={11} /> Success
                            </span>
                          ) : (
                            <span className="badge-tag badge-red" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.72rem' }}>
                              <XCircle size={11} /> Failed
                            </span>
                          )}
                        </td>
                        <td style={{ fontSize: '0.75rem', color: 'var(--text-subtle)', fontFamily: 'var(--font-mono)' }}>
                          {run.timestamp ? run.timestamp.replace('T', ' ').slice(0, 19) : 'N/A'}
                        </td>
                        <td>
                          <span className="dataset-id-tag" style={{ fontSize: '0.72rem', padding: '0.15rem 0.4rem' }}>
                            {run.dataset_id ? run.dataset_id.slice(0, 8) : '—'}
                          </span>
                        </td>
                        <td style={{ color: 'var(--text-main)', fontWeight: 500, fontSize: '0.82rem' }}>
                          {run.question}
                        </td>
                        <td>
                          {run.sql ? (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', maxWidth: '340px' }}>
                              <code style={{
                                flex: 1,
                                minWidth: 0,
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                                fontSize: '0.72rem',
                                fontFamily: 'var(--font-mono)',
                                background: 'rgba(0,0,0,0.25)',
                                padding: '0.25rem 0.5rem',
                                borderRadius: '4px',
                                color: 'var(--accent-lime)'
                              }} title={run.sql}>
                                {run.sql}
                              </code>
                              <button
                                onClick={() => handleCopySql(run.sql, run.id || idx)}
                                title={copiedId === (run.id || idx) ? "Copied!" : "Copy SQL query"}
                                style={{
                                  background: copiedId === (run.id || idx) ? 'rgba(52, 211, 153, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                                  border: `1px solid ${copiedId === (run.id || idx) ? 'var(--accent-emerald)' : 'var(--border-color)'}`,
                                  borderRadius: '4px',
                                  padding: '0.25rem 0.35rem',
                                  cursor: 'pointer',
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  color: copiedId === (run.id || idx) ? 'var(--accent-emerald)' : 'var(--text-muted)',
                                  transition: 'all 0.2s ease',
                                  flexShrink: 0
                                }}
                              >
                                {copiedId === (run.id || idx) ? <Check size={12} /> : <Copy size={12} />}
                              </button>
                            </div>
                          ) : (
                            <span style={{ color: 'var(--text-subtle)', fontSize: '0.75rem' }}>No SQL</span>
                          )}
                        </td>
                        <td style={{ fontSize: '0.78rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
                          {run.latency_seconds != null ? `${run.latency_seconds}s` : '—'}
                        </td>
                        <td style={{ fontSize: '0.78rem', color: run.retries > 0 ? 'var(--accent-rose)' : 'var(--text-subtle)' }}>
                          {run.retries ?? 0}
                        </td>
                        <td style={{ fontSize: '0.78rem', maxWidth: '300px', color: run.success ? 'var(--text-subtle)' : 'var(--accent-rose)', fontFamily: run.success ? 'inherit' : 'var(--font-mono)' }}>
                          {run.success ? 'Executed successfully' : (run.error || 'Unknown error')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ padding: '1.25rem', background: 'rgba(255,255,255,0.02)', border: '1px dashed var(--border-color)', borderRadius: '8px', textAlign: 'center', color: 'var(--text-subtle)', fontSize: '0.85rem' }}>
                No chat queries logged yet. Ask a question in <strong>Agent Chat Studio</strong> to see live execution telemetry appear here!
              </div>
            )}
          </div>

        </>
      ) : (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-subtle)' }}>
          Loading observability metrics...
        </div>
      )}
    </div>
  );
}
