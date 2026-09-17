import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import type { Session } from '../types/debate';

interface SidebarProps {
  isStreaming: boolean;
  sessions: Session[];
  activeIdx: number;
  onSelect: (idx: number) => void;
  onNew: () => void;
  onDelete: (idx: number) => void;
}

const AVATAR_COLORS = [
  '#4F7FFF', '#E11D68', '#059669', '#D97706',
  '#6C4DFF', '#0891B2', '#EA580C',
];

export const Sidebar: React.FC<SidebarProps> = ({ sessions, activeIdx, onSelect, onNew, onDelete, isStreaming }) => {
  const renderDate = (ts: string) => {
    try {
      const dt = new Date(ts);
      if (isNaN(dt.getTime())) return ts.substring(0, 16);
      return dt.toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return ts;
    }
  };

  return (
    <div className="w-[280px] min-w-[280px] bg-sidebar p-6 flex flex-col h-screen sticky top-0 overflow-y-auto">
      <div className="flex items-center gap-3 mb-7">
        <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-[#6C4DFF] to-[#4F7FFF] flex justify-center items-center text-xl shadow-[0_6px_20px_rgba(108,77,255,0.35)] shrink-0">
          🤖
        </div>
        <div>
          <h3 className="text-white text-[17px] font-bold leading-tight">AI Debate Agent</h3>
          <p className="text-[#7B8DB5] text-xs mt-1 leading-snug">Different perspectives.<br/>Better thinking.</p>
        </div>
      </div>

      <button 
        onClick={onNew}
        disabled={isStreaming}
        className={`w-full h-[50px] bg-gradient-to-br from-[#6C4DFF] to-[#4F7FFF] text-white rounded-xl text-[15px] font-bold shadow-[0_6px_20px_rgba(79,127,255,0.3)] flex justify-center items-center gap-2 mb-8 hover:-translate-y-[1px] transition-transform ${isStreaming ? "opacity-50 cursor-not-allowed" : ""}`}
      >
        <Plus size={18} strokeWidth={3} /> New Debate
      </button>

            <div className="flex justify-between items-center mb-4 pr-3">
        <div className="text-[#5A6E94] text-[11px] font-bold uppercase tracking-wider">
          Recent Debates
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 dark-scrollbar pr-1.5 mr-[-6px]">
        {sessions.length === 0 ? (
          <div className="text-[#5A6E94] text-sm">No debates yet.</div>
        ) : (
          sessions.map((s, idx) => {
            const topic = s.topic || 'Untitled';
            const initial = topic.charAt(0).toUpperCase();
            const color = AVATAR_COLORS[idx % AVATAR_COLORS.length];
            const isActive = idx === activeIdx;

            return (
              <div 
                key={idx} 
                onClick={() => !isStreaming && onSelect(idx)}
                className={`group flex items-center gap-3 p-[12px_14px] rounded-xl transition-colors border relative ${isStreaming ? "opacity-50 cursor-not-allowed" : "cursor-pointer"} ${
                  isActive 
                    ? 'bg-[#6C4DFF]/10 border-[#6C4DFF]/40' 
                    : 'bg-white/5 border-white/5 hover:bg-white/10'
                }`}
              >
                <div 
                  className="w-[38px] h-[38px] rounded-full flex justify-center items-center text-[15px] font-bold text-white shrink-0"
                  style={{ backgroundColor: color }}
                >
                  {initial}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[#E2E8F0] text-sm font-medium truncate mb-1">
                    {topic}
                  </div>
                  <div className="text-[#5A6E94] text-[11px] font-medium">
                    📅 {renderDate(s.timestamp)}
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(idx);
                  }}
                  disabled={isStreaming}
                  className={`opacity-0 group-hover:opacity-100 transition-opacity p-2 -mr-2 text-[#5A6E94] hover:text-red-400 ${isStreaming ? 'cursor-not-allowed' : 'cursor-pointer'}`}
                  title="Delete debate"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            );
          })
        )}
      </div>

      <div className="mt-8 bg-[#6C4DFF]/10 border-l-4 border-[#6C4DFF] rounded-r-lg p-4 text-[#7B8DB5] text-[13px] italic leading-relaxed">
        "Better questions lead to better thinking."
      </div>
    </div>
  );
};
