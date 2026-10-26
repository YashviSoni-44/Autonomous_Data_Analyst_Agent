import React, { useState, useEffect, useRef } from 'react';
import { Send, Sparkles, ChevronDown, ChevronUp, BarChart3, Terminal, Activity, Trash2, HelpCircle, Layers, TrendingUp, Link2, AlertTriangle, ShieldCheck } from 'lucide-react';
import CodeBlock from './CodeBlock';
import ChartModal from './ChartModal';
import { BACKEND_URL } from '../config';

// Safety net: remove any markdown symbols so answers read as plain English
const cleanSummary = (text) => (text || '')
  .replace(/^\s{0,3}#{1,6}\s*/gm, '')
  .replace(/\*\*(.+?)\*\*/g, '$1')
  .replace(/__(.+?)__/g, '$1')
  .replace(/`([^`]+)`/g, '$1')
  .replace(/^\s*[-*]\s+/gm, '• ')
  .trim();

export default function AgentChatStudio({
  datasetInfo,
  conversationHistory,
  setConversationHistory,
  sessionId,
  setSessionId,
  followUpQuestions,
  setFollowUpQuestions,
  pendingQuestion,
  setPendingQuestion
}) {
  const [questionInput, setQuestionInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [expandedPlan, setExpandedPlan] = useState({});
  const [expandedTrace, setExpandedTrace] = useState({});
  const [expandedJoin, setExpandedJoin] = useState({});
  const [selectedChartBase64, setSelectedChartBase64] = useState(null);
  const [pendingTurnQuestion, setPendingTurnQuestion] = useState(null);
  const [progress, setProgress] = useState({ percent: 0, stage: 'Starting' });
  const [elapsed, setElapsed] = useState(0);

  const feedRef = useRef(null);

  const toggleExpand = (setter, key) => {
    setter(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // Keep the newest message in view
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTo({ top: feedRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [conversationHistory.length, pendingTurnQuestion]);

  useEffect(() => {
    if (pendingQuestion && !loading) {
      handleAskQuestion(pendingQuestion);
      if (setPendingQuestion) setPendingQuestion(null);
    }
  }, [pendingQuestion]);

  const handleAskQuestion = async (queryToAsk) => {
    const question = queryToAsk || questionInput;
    if (!question || !question.trim()) return;

    if (!datasetInfo?.dataset_id) {
      alert('Please load a dataset from the sidebar first.');
      return;
    }

    setLoading(true);
    setQuestionInput('');

    // Construct multi-turn context
    let convContext = '';
    conversationHistory.slice(-4).forEach(turn => {
      convContext += `Q: ${turn.question}\nSQL: ${turn.sql || ''}\nAnswer: ${turn.summary || ''}\n\n`;
    });

    const requestId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const payload = {
      dataset_id: datasetInfo.dataset_id,
      question: question,
      session_id: sessionId,
      conversation_context: convContext,
      request_id: requestId,
    };

    // Show the question immediately + start progress tracking
    setPendingTurnQuestion(question);
    setProgress({ percent: 0, stage: 'Starting' });
    setElapsed(0);
    const startedAt = Date.now();
    const tickTimer = setInterval(() => setElapsed((Date.now() - startedAt) / 1000), 100);
    const pollTimer = setInterval(async () => {
      try {
        const r = await fetch(`${BACKEND_URL}/progress/${requestId}`);
        if (r.ok) {
          const p = await r.json();
          setProgress(prev => ({ percent: Math.max(prev.percent, p.percent), stage: p.stage }));
        }
      } catch (_) { /* ignore transient polling errors */ }
    }, 500);

    try {
      const res = await fetch(`${BACKEND_URL}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Backend execution failed');
      }

      const data = await res.json();

      if (data.session_id) {
        setSessionId(data.session_id);
      }

      if (data.follow_up_questions) {
        setFollowUpQuestions(data.follow_up_questions);
      }

      setConversationHistory(prev => [
        ...prev,
        {
          question,
          summary: data.summary,
          sql: data.sql,
          chart_base64: data.chart_base64,
          plan: data.plan,
          join_hints: data.join_hints,
          analysis_type: data.analysis_type,
          analytics_result: data.analytics_result,
          trace: data.trace,
          retries: data.retries,
          session_id: data.session_id,
          critic_result: data.critic_result,
        }
      ]);
    } catch (err) {
      alert(`Error asking question: ${err.message}`);
    } finally {
      clearInterval(pollTimer);
      clearInterval(tickTimer);
      setLoading(false);
      setPendingTurnQuestion(null);
    }
  };

  const starterQuestions = [
    "What is the total sales amount by product category?",
    "Forecast sales for the next 3 months",
    "What is the correlation between sales_amount and quantity?",
    "Detect outliers in sales_amount"
  ];

  if (!datasetInfo?.dataset_id) {
    return (
      <div className="tab-view">
        <div className="empty-state">
          <div className="empty-state-icon">
            <Sparkles size={32} />
          </div>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Agent Chat Studio</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
            Please upload a CSV or Excel dataset, or select the sample sales dataset from the sidebar to start asking questions in natural language.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="tab-view" style={{ overflow: 'hidden' }}>
      <ChartModal imageBase64={selectedChartBase64} onClose={() => setSelectedChartBase64(null)} />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexShrink: 0 }}>
        <div>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>💬 Agent Chat Studio</h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-subtle)' }}>
            Ask plain-English questions — powered by LangGraph, DuckDB SQL execution, and auto-visualization.
          </p>
        </div>

        {conversationHistory.length > 0 && (
          <button
            className="btn-copy"
            onClick={() => {
              setConversationHistory([]);
              setSessionId(null);
              setFollowUpQuestions([]);
            }}
            title="Reset conversation"
          >
            <Trash2 size={14} /> Clear History
          </button>
        )}
      </div>

      {/* Conversation Feed */}
      <div className="chat-feed" ref={feedRef} style={{ overflowY: 'auto', minHeight: 0, paddingRight: '0.5rem' }}>
        {conversationHistory.map((turn, idx) => (
          <React.Fragment key={idx}>
            {/* User Question */}
            <div className="user-message">
              🧑 {turn.question}
            </div>

            {/* Agent Response Card */}
            <div className="agent-response-card">
              {/* Specialized Analytics Card (Phase 4) */}
              {turn.analytics_result && !turn.analytics_result.error && (
                <div style={{
                  background: 'rgba(15, 23, 42, 0.6)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  padding: '0.85rem',
                  marginBottom: '1rem'
                }}>
                  {turn.analysis_type === 'forecast' && (
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                        <TrendingUp size={16} color="var(--accent-emerald)" />
                        <span style={{ fontWeight: 600, color: 'var(--accent-emerald)', fontSize: '0.9rem' }}>
                          Predictive Time-Series Forecast (Holt's Exponential Smoothing)
                        </span>
                      </div>
                      <div className="plan-grid">
                        <div className="plan-item">
                          <div className="plan-item-label">Trend Direction</div>
                          <div className="plan-item-val" style={{ color: turn.analytics_result.metrics?.trend_direction === 'Growth' ? 'var(--accent-emerald)' : 'var(--accent-cyan)' }}>
                            {turn.analytics_result.metrics?.trend_direction || 'Stable'}
                          </div>
                        </div>
                        <div className="plan-item">
                          <div className="plan-item-label">Next Expected Value</div>
                          <div className="plan-item-val" style={{ fontWeight: 'bold' }}>
                            ${Number(turn.analytics_result.metrics?.next_predicted_value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}
                          </div>
                        </div>
                        <div className="plan-item">
                          <div className="plan-item-label">Model MAE</div>
                          <div className="plan-item-val">
                            {turn.analytics_result.metrics?.mae !== undefined ? turn.analytics_result.metrics.mae.toFixed(2) : '0.00'}
                          </div>
                        </div>
                        <div className="plan-item">
                          <div className="plan-item-label">Horizon</div>
                          <div className="plan-item-val">
                            {turn.analytics_result.horizon || 5} Periods
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {turn.analysis_type === 'correlation' && (
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                        <Link2 size={16} color="var(--accent-cyan)" />
                        <span style={{ fontWeight: 600, color: 'var(--accent-cyan)', fontSize: '0.9rem' }}>
                          Correlation Testing & Primary Associations
                        </span>
                      </div>
                      {turn.analytics_result.top_pairs?.length > 0 && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', marginTop: '0.4rem' }}>
                          {turn.analytics_result.top_pairs.slice(0, 3).map((p, pIdx) => (
                            <div key={pIdx} style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              padding: '0.35rem 0.6rem',
                              background: 'rgba(255,255,255,0.03)',
                              borderRadius: '4px',
                              fontSize: '0.85rem'
                            }}>
                              <span style={{ color: 'var(--text-muted)' }}>
                                <strong>{p.var1}</strong> ↔ <strong>{p.var2}</strong>
                              </span>
                              <span style={{
                                fontWeight: 600,
                                color: p.abs_pearson >= 0.7 ? 'var(--accent-emerald)' : (p.abs_pearson >= 0.4 ? 'var(--accent-cyan)' : 'var(--text-subtle)')
                              }}>
                                r = {p.pearson > 0 ? `+${p.pearson.toFixed(2)}` : p.pearson.toFixed(2)} ({p.strength} {p.direction})
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {turn.analysis_type === 'outliers' && (
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                        <AlertTriangle size={16} color="var(--accent-amber)" />
                        <span style={{ fontWeight: 600, color: 'var(--accent-amber)', fontSize: '0.9rem' }}>
                          Outlier & Anomaly Detection ({turn.analytics_result.method || 'IQR'})
                        </span>
                      </div>
                      <div className="plan-grid">
                        <div className="plan-item">
                          <div className="plan-item-label">Metric Tested</div>
                          <div className="plan-item-val">{turn.analytics_result.column}</div>
                        </div>
                        <div className="plan-item">
                          <div className="plan-item-label">Outliers Found</div>
                          <div className="plan-item-val" style={{ color: turn.analytics_result.outlier_count > 0 ? 'var(--accent-amber)' : 'var(--accent-emerald)', fontWeight: 'bold' }}>
                            {turn.analytics_result.outlier_count} ({turn.analytics_result.outlier_percentage}%)
                          </div>
                        </div>
                        <div className="plan-item">
                          <div className="plan-item-label">Normal Bounds</div>
                          <div className="plan-item-val">
                            [{turn.analytics_result.bounds?.lower_bound} to {turn.analytics_result.bounds?.upper_bound}]
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Executive Business Summary */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div className="section-header" style={{ marginBottom: '0.4rem' }}>
                    <Sparkles size={16} color="var(--accent-emerald)" />
                    <span>Key Findings & Answer</span>
                  </div>

                  {/* Critic Verification Badge (Phase 5.1) */}
                  {turn.critic_result && (
                    <div style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.35rem',
                      padding: '0.2rem 0.55rem',
                      borderRadius: '5px',
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      background: turn.critic_result.hallucination_detected 
                        ? 'rgba(251, 191, 36, 0.1)' 
                        : 'rgba(52, 211, 153, 0.1)',
                      border: `1px solid ${turn.critic_result.hallucination_detected ? 'var(--accent-amber)' : 'var(--accent-emerald)'}`,
                      color: turn.critic_result.hallucination_detected ? 'var(--accent-amber)' : 'var(--accent-emerald)',
                    }}>
                      <ShieldCheck size={13} />
                      <span>
                        {turn.critic_result.hallucination_detected
                          ? `Critic Auto-Adjusted (${(turn.critic_result.score * 100).toFixed(0)}% grounded)`
                          : `Critic Verified (100% Grounded)`}
                      </span>
                    </div>
                  )}
                </div>
                <div className="summary-box">
                  {cleanSummary(turn.summary) || 'No summary available.'}
                </div>
              </div>

              {/* Multi-table Join Hints */}
              {turn.join_hints && (
                <div className="accordion">
                  <div
                    className="accordion-summary"
                    onClick={() => toggleExpand(setExpandedJoin, idx)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--accent-cyan)' }}>
                      <Layers size={15} />
                      <span>Detected Multi-Table Relationships</span>
                    </div>
                    {expandedJoin[idx] ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </div>
                  {expandedJoin[idx] && (
                    <div className="accordion-content" style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                      {turn.join_hints}
                    </div>
                  )}
                </div>
              )}

              {/* Decomposed Analysis Plan */}
              {turn.plan && (
                <div className="accordion">
                  <div
                    className="accordion-summary"
                    onClick={() => toggleExpand(setExpandedPlan, idx)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <HelpCircle size={15} color="var(--accent-lime)" />
                      <span>🎯 Agent Strategy & Decomposed Plan</span>
                    </div>
                    {expandedPlan[idx] ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </div>
                  {expandedPlan[idx] && (
                    <div className="accordion-content">
                      <div style={{ marginBottom: '0.5rem' }}>
                        <strong>Intent:</strong> {turn.plan.intent || 'N/A'}
                      </div>
                      <div className="plan-grid">
                        <div className="plan-item">
                          <div className="plan-item-label">Metrics</div>
                          <div className="plan-item-val">{turn.plan.metrics?.join(', ') || 'None'}</div>
                        </div>
                        <div className="plan-item">
                          <div className="plan-item-label">Dimensions</div>
                          <div className="plan-item-val">{turn.plan.dimensions?.join(', ') || 'None'}</div>
                        </div>
                        <div className="plan-item">
                          <div className="plan-item-label">Operations</div>
                          <div className="plan-item-val">{turn.plan.operations?.join(', ') || 'None'}</div>
                        </div>
                      </div>
                      {turn.plan.chart_type_suggestion && (
                        <div style={{ marginTop: '0.4rem' }}>
                          <strong>Recommended Visual:</strong> <code>{turn.plan.chart_type_suggestion}</code>
                        </div>
                      )}
                      {turn.plan.steps && (
                        <div style={{ marginTop: '0.6rem' }}>
                          <strong>Execution Steps:</strong>
                          <ul style={{ paddingLeft: '1.2rem', marginTop: '0.2rem' }}>
                            {turn.plan.steps.map((step, sIdx) => (
                              <li key={sIdx}>{step}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Chart Visualization */}
              {turn.chart_base64 && (
                <div>
                  <div className="section-header">
                    <BarChart3 size={16} color="var(--accent-cyan)" />
                    <span>Generated Visualization</span>
                  </div>
                  <div className="chart-container">
                    <img
                      src={`data:image/png;base64,${turn.chart_base64}`}
                      alt="Generated Chart"
                      className="chart-img"
                      onClick={() => setSelectedChartBase64(turn.chart_base64)}
                    />
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-subtle)', marginTop: '0.4rem' }}>
                      Click chart to expand view
                    </div>
                  </div>
                </div>
              )}

              {/* Generated SQL */}
              <div>
                <div className="section-header">
                  <Terminal size={16} color="var(--accent-lime)" />
                  <span>Generated SQL Query</span>
                </div>
                <CodeBlock code={turn.sql} language="sql" />
              </div>

              {/* Observability Trace */}
              {turn.trace && (
                <div className="accordion">
                  <div
                    className="accordion-summary"
                    onClick={() => toggleExpand(setExpandedTrace, idx)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <Activity size={15} color="var(--accent-purple)" />
                      <span>🕵️ Agent Execution Trace & Metadata</span>
                    </div>
                    {expandedTrace[idx] ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </div>
                  {expandedTrace[idx] && (
                    <div className="accordion-content">
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-subtle)', marginBottom: '0.6rem' }}>
                        Session ID: <code>{turn.session_id || 'N/A'}</code> | Retries: {turn.retries || 0}
                      </div>
                      {turn.trace.map((step, tIdx) => (
                        <div key={tIdx} className="trace-node-item">
                          <span className="trace-node-name">[{step.node}]</span>
                          <span style={{ color: 'var(--text-muted)' }}>{step.detail}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </React.Fragment>
        ))}

        {loading && pendingTurnQuestion && (
          <>
            <div className="user-message">🧑 {pendingTurnQuestion}</div>
            <div className="agent-response-card" style={{ padding: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.6rem', color: 'var(--accent-lime)', marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <Sparkles className="spin-icon" size={18} style={{ animation: 'spin 1.5s linear infinite' }} />
                  <span style={{ fontWeight: 600 }}>{progress.stage}…</span>
                </div>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {progress.percent}% · {elapsed.toFixed(1)}s elapsed
                </span>
              </div>
              <div style={{ height: '8px', borderRadius: '999px', background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
                <div style={{
                  height: '100%',
                  width: `${Math.max(progress.percent, 4)}%`,
                  borderRadius: '999px',
                  background: 'linear-gradient(90deg, var(--accent-cyan), var(--accent-lime))',
                  transition: 'width 0.5s ease',
                }} />
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-subtle)', marginTop: '0.5rem' }}>
                Planner → SQL → Analytics → Chart → Summary → Verification → Follow-ups
              </div>
            </div>
          </>
        )}
      </div>

      {/* Starter & Follow-up Chips */}
      <div className="suggestion-section" style={{ flexShrink: 0 }}>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-subtle)', fontWeight: 600 }}>
          {followUpQuestions.length > 0 ? '💡 SUGGESTED FOLLOW-UP QUESTIONS:' : '💡 TRY ASKING:'}
        </div>
        <div className="suggestion-chips">
          {(followUpQuestions.length > 0 ? followUpQuestions : starterQuestions).map((q, qIdx) => (
            <button
              key={qIdx}
              className="chip-btn"
              onClick={() => handleAskQuestion(q)}
              disabled={loading}
            >
              <Sparkles size={12} color="var(--accent-lime)" />
              <span>{q}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Question Input Box */}
      <div className="input-bar-container" style={{ flexShrink: 0 }}>
        <input
          type="text"
          className="question-input"
          placeholder="Ask a question about your dataset (e.g. Total sales by category?)..."
          value={questionInput}
          onChange={(e) => setQuestionInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !loading) handleAskQuestion();
          }}
          disabled={loading}
        />
        <button
          className="btn-primary"
          style={{ width: 'auto', padding: '0.6rem 1.25rem' }}
          onClick={() => handleAskQuestion()}
          disabled={loading || !questionInput.trim()}
        >
          <span>Ask</span>
          <Send size={15} />
        </button>
      </div>
    </div>
  );
}
