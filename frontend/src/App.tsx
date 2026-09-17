import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { DebateConfig } from './components/DebateConfig';
import { DebateTranscript } from './components/DebateTranscript';
import { DebateResult } from './components/DebateResult';
import { getHistory, deleteHistoryItem } from './services/api';
import type { Session, DebateMessage, Verdict } from './types/debate';

function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeIdx, setActiveIdx] = useState<number>(-1);

  const [topic, setTopic] = useState('');
  const [rounds, setRounds] = useState<number>(3);
  
  const [transcript, setTranscript] = useState<DebateMessage[]>([]);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  
  const [isStreaming, setIsStreaming] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const data = await getHistory();
      setSessions(data);
    } catch (e) {
      console.error("Failed to load history", e);
    }
  };

    const handleTopicChange = (t: string) => {
    setTopic(t);
    if (activeIdx !== -1) {
      setActiveIdx(-1);
      setTranscript([]);
      setVerdict(null);
    }
  };

  const handleSelectSession = (idx: number) => {
    if (isStreaming) return;
    const s = sessions[idx];
    if (!s) return;
    setActiveIdx(idx);
    setTopic(s.topic);
    setRounds(s.rounds);
    setTranscript(s.transcript || []);
    setVerdict(s.verdict || null);
    setStatusMessage(null);
  };

  const handleNewDebate = () => {
    setActiveIdx(-1);
    setTopic('');
    setRounds(3);
    setTranscript([]);
    setVerdict(null);
    setStatusMessage(null);
  };

    const handleDeleteItem = async (idx: number) => {
    if (window.confirm("Are you sure you want to delete this debate?")) {
      await deleteHistoryItem(idx);
      setSessions(prev => prev.filter((_, i) => i !== idx));
      if (activeIdx === idx) {
        handleNewDebate();
      } else if (activeIdx > idx) {
        setActiveIdx(activeIdx - 1);
      }
    }
  };

  const handleClear = () => {
    handleNewDebate();
  };

  const handleStart = async () => {
    if (!topic.trim()) return;
    
    setTranscript([]);
    setVerdict(null);
    setStatusMessage("Connecting to agents...");
    setIsStreaming(true);

    try {
      const response = await fetch('http://localhost:8000/api/debate/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, rounds })
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || ''; // Keep the incomplete part

        for (const part of parts) {
          if (!part.trim()) continue;
          
          const lines = part.split('\n');
          const eventLine = lines.find(l => l.startsWith('event:'));
          const dataLine = lines.find(l => l.startsWith('data:'));

          if (eventLine && dataLine) {
            const eventType = eventLine.replace('event:', '').trim();
            const dataStr = dataLine.replace('data:', '').trim();
            const data = dataStr ? JSON.parse(dataStr) : null;

            if (eventType === 'status') {
              setStatusMessage(data.message);
            } 
            else if (eventType === 'chunk') {
              setTranscript(prev => {
                // If it's the same round and speaker as the last message, replace it
                const last = prev[prev.length - 1];
                if (last && last.round === data.round && last.speaker === data.speaker) {
                  const updated = [...prev];
                  updated[updated.length - 1] = data;
                  return updated;
                }
                return [...prev, data];
              });
              setStatusMessage(`Round ${data.round}: ${data.speaker} (${data.position}) is arguing…`);
            }
            else if (eventType === 'judge_chunk') {
              setStatusMessage(`⚖️ Judge is evaluating arguments…\n\n${data.content}`);
            }
            else if (eventType === 'state_full') {
              setTranscript(data.transcript || []);
              if (data.verdict && typeof data.verdict === "object" && Object.keys(data.verdict).length > 0) {
                setVerdict(data.verdict);
              }
            }
            else if (eventType === 'error') {
              setStatusMessage(`❌ Error: ${data.detail}`);
              setIsStreaming(false);
              return;
            }
            else if (eventType === 'done') {
              setIsStreaming(false);
              setStatusMessage(null);
              loadHistory();
              return;
            }
          }
        }
      }
    } catch (e: any) {
      setStatusMessage(`❌ Connection failed: ${e.message}`);
      setIsStreaming(false);
    }
  };

  return (
    <div className="flex w-full min-h-screen bg-background overflow-hidden">
      <Sidebar 
        sessions={sessions} 
        activeIdx={activeIdx} 
        onSelect={handleSelectSession} 
        onNew={handleNewDebate}
        onDelete={handleDeleteItem}
        isStreaming={isStreaming}
          readOnly={activeIdx !== -1}
      />

      <main className="flex-1 flex flex-col p-8 px-10 h-screen overflow-y-auto">
        <Header />
        
        <DebateConfig 
          topic={topic}
          setTopic={handleTopicChange}
          rounds={rounds}
          setRounds={setRounds}
          onStart={handleStart}
          isStreaming={isStreaming}
          readOnly={activeIdx !== -1}
        />

        <div className="grid grid-cols-[68fr_32fr] gap-6 w-full items-start">
          <DebateTranscript 
            transcript={transcript}
            statusMessage={statusMessage}
            isStreaming={isStreaming}
          readOnly={activeIdx !== -1}
            onClear={handleClear}
            topic={topic}
          />
          <DebateResult 
            verdict={verdict}
            isComplete={!!verdict && !isStreaming}
          />
        </div>
      </main>
    </div>
  );
}

export default App;
