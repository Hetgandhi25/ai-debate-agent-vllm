import React, { useRef, useEffect } from 'react';
import { Copy, Download, Trash2, Users, Check } from 'lucide-react';
import type { DebateMessage as IDebateMessage } from '../types/debate';
import { DebateMessage } from './DebateMessage';

interface Props {
  transcript: IDebateMessage[];
  statusMessage: string | null;
  isStreaming: boolean;
  onClear: () => void;
  topic: string;
}

export const DebateTranscript: React.FC<Props> = ({ transcript, statusMessage, isStreaming, onClear, topic }) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = React.useState(false);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcript, statusMessage]);

  const handleCopy = async () => {
    const text = transcript.map(m => `[Round ${m.round}] ${m.speaker} (${m.position})\n${m.content}\n`).join('\n');
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      alert("Copy failed");
    }
  };

  const handleDownload = () => {
    const text = transcript.map(m => `[Round ${m.round}] ${m.speaker} (${m.position})\n${m.content}\n`).join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(topic || 'debate').replace(/[^a-z0-9]/gi, '_').toLowerCase()}_transcript.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full min-w-0 flex flex-col bg-white border border-border-light rounded-2xl shadow-[0_2px_12px_rgba(0,0,0,0.03)] p-6 min-h-[400px]">
      
      {/* Header */}
      <div className="flex justify-between items-center pb-4 mb-5 border-b border-border-light h-[52px] shrink-0">
        <div className="flex items-center gap-2.5 text-[17px] font-bold text-text-primary">
          <Users size={20} /> Debate Transcript
          {isStreaming && (
            <span className="bg-[#DCFCE7] text-[#15803D] text-[12px] px-3 py-1 rounded-full ml-2 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-[#15803D] rounded-full animate-pulse" /> Live
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <button 
            onClick={handleCopy} 
            className={`h-9 px-3.5 border text-[13px] font-semibold rounded-lg flex items-center gap-1.5 transition-all active:scale-95 shadow-sm ${
              copied 
                ? 'bg-emerald-50 border-emerald-200 text-emerald-600' 
                : 'bg-white border-border-light text-text-secondary hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-600'
            }`}
          >
            {copied ? <Check size={14} /> : <Copy size={14} />} 
            {copied ? 'Copied!' : 'Copy'}
          </button>
          <button 
            onClick={handleDownload} 
            className="h-9 px-3.5 bg-white border border-border-light text-text-secondary text-[13px] font-semibold rounded-lg flex items-center gap-1.5 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-600 transition-all active:scale-95 shadow-sm"
          >
            <Download size={14} /> Download
          </button>
          <button 
            onClick={onClear} 
            className="h-9 px-3.5 bg-white border border-border-light text-text-secondary text-[13px] font-semibold rounded-lg flex items-center gap-1.5 hover:bg-red-50 hover:border-red-200 hover:text-red-600 transition-all active:scale-95 shadow-sm"
          >
            <Trash2 size={14} /> Clear
          </button>
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar" ref={scrollRef}>
        {transcript.length === 0 && !statusMessage && (
          <div className="text-center text-text-secondary text-[15px] py-16">
            The debate will appear here once you start…
          </div>
        )}

        {transcript.map((msg, idx) => (
          <DebateMessage key={idx} msg={msg} />
        ))}

        {statusMessage && (
          <div className="flex items-center gap-3 bg-[#EFF6FF] border border-[#DBEAFE] rounded-xl px-5 py-3.5 text-[14px] font-medium text-[#4F7FFF] mb-4">
            🤖 <span>{statusMessage}</span>
          </div>
        )}
      </div>
    </div>
  );
};
