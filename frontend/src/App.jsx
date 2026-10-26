import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import AgentChatStudio from './components/AgentChatStudio';
import DataProfiling from './components/DataProfiling';
import ObservabilityDashboard from './components/ObservabilityDashboard';
import AutonomousReportView from './components/AutonomousReportView';
import { MessageSquare, FileSearch, BarChart2, Compass } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [profile, setProfile] = useState(null);
  const [conversationHistory, setConversationHistory] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [followUpQuestions, setFollowUpQuestions] = useState([]);
  const [pendingQuestion, setPendingQuestion] = useState(null);
  const [autonomousReport, setAutonomousReport] = useState(null);
  const [autonomousLoading, setAutonomousLoading] = useState(false);

  const handleSelectAutonomousQuestion = (question) => {
    setPendingQuestion(question);
    setActiveTab('chat');
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <Sidebar
        datasetInfo={datasetInfo}
        setDatasetInfo={setDatasetInfo}
        profile={profile}
        setProfile={setProfile}
        setConversationHistory={setConversationHistory}
        setSessionId={setSessionId}
        setFollowUpQuestions={setFollowUpQuestions}
        setAutonomousReport={setAutonomousReport}
        onNavigateTab={setActiveTab}
      />

      {/* Main Content */}
      <main className="main-content">
        {/* Top Navbar */}
        <header className="top-navbar">
          <nav className="nav-tabs">
            <button
              className={`nav-tab ${activeTab === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveTab('chat')}
            >
              <MessageSquare size={16} />
              <span>💬 Agent Chat Studio</span>
            </button>

            <button
              className={`nav-tab ${activeTab === 'autonomous' ? 'active' : ''}`}
              onClick={() => setActiveTab('autonomous')}
            >
              <Compass size={16} />
              <span>⚡ Autonomous Deep Dive</span>
            </button>

            <button
              className={`nav-tab ${activeTab === 'profiling' ? 'active' : ''}`}
              onClick={() => setActiveTab('profiling')}
            >
              <FileSearch size={16} />
              <span>🔍 Data Quality & Profiling</span>
            </button>

            <button
              className={`nav-tab ${activeTab === 'metrics' ? 'active' : ''}`}
              onClick={() => setActiveTab('metrics')}
            >
              <BarChart2 size={16} />
              <span>📊 Observability & Metrics</span>
            </button>
          </nav>

          <div className="status-indicator">
            <div className="status-dot"></div>
            <span>System Active</span>
          </div>
        </header>

        {/* Tab Content Views (Preserved across tab switches to avoid reloads) */}
        <div style={{ display: activeTab === 'chat' ? 'flex' : 'none', flex: 1, flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
          <AgentChatStudio
            datasetInfo={datasetInfo}
            conversationHistory={conversationHistory}
            setConversationHistory={setConversationHistory}
            sessionId={sessionId}
            setSessionId={setSessionId}
            followUpQuestions={followUpQuestions}
            setFollowUpQuestions={setFollowUpQuestions}
            pendingQuestion={pendingQuestion}
            setPendingQuestion={setPendingQuestion}
          />
        </div>

        <div style={{ display: activeTab === 'autonomous' ? 'flex' : 'none', flex: 1, flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
          <AutonomousReportView
            datasetInfo={datasetInfo}
            onSelectQuestion={handleSelectAutonomousQuestion}
            report={autonomousReport}
            setReport={setAutonomousReport}
            loading={autonomousLoading}
            setLoading={setAutonomousLoading}
          />
        </div>

        <div style={{ display: activeTab === 'profiling' ? 'flex' : 'none', flex: 1, flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
          <DataProfiling
            datasetInfo={datasetInfo}
            profile={profile}
            setProfile={setProfile}
          />
        </div>

        <div style={{ display: activeTab === 'metrics' ? 'flex' : 'none', flex: 1, flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
          <ObservabilityDashboard />
        </div>
      </main>
    </div>
  );
}
