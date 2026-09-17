import React from 'react';
import { FileText, Layers, Play } from 'lucide-react';

interface DebateConfigProps {
  topic: string;
  setTopic: (t: string) => void;
  rounds: number;
  setRounds: (r: number) => void;
  onStart: () => void;
  isStreaming: boolean;
  readOnly?: boolean;
}

export const DebateConfig: React.FC<DebateConfigProps> = ({
  topic, setTopic, rounds, setRounds, onStart, isStreaming, readOnly
}) => {
  return (
    <div className="bg-white border border-border-light rounded-2xl shadow-[0_2px_12px_rgba(0,0,0,0.03)] p-6 px-8 mb-6 grid grid-cols-[45fr_25fr_30fr] gap-8 items-end w-full">
      
      {/* Topic Input - 45% */}
      <div className="min-w-0">
        <label className="flex items-center gap-2 text-[14px] font-[650] text-text-primary mb-3">
          <FileText size={16} className="text-text-secondary" /> Debate Topic
        </label>
        <input
          type="text"
          placeholder="e.g. Android Vs Apple"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          disabled={isStreaming || readOnly}
          className="w-full h-[52px] px-4 bg-white border-[1.5px] border-border-light rounded-xl text-[15px] text-text-primary focus:border-[#6C4DFF] focus:ring-[3px] focus:ring-[#6C4DFF]/10 outline-none transition-all placeholder:text-[#94A3B8] disabled:bg-gray-50 disabled:cursor-not-allowed"
        />
        <div className="text-right text-[11px] text-[#94A3B8] mt-2 font-medium">
          {topic.length} / 200
        </div>
      </div>

      {/* Rounds - 25% */}
      <div className="min-w-0">
        <label className="flex items-center gap-2 text-[14px] font-[650] text-text-primary mb-3">
          <Layers size={16} className="text-text-secondary" /> Number of Rounds
        </label>
        <div className="flex gap-2 h-[52px] items-start">
          {[1, 2, 3, 4, 5].map((r) => (
            <button
              key={r}
              onClick={() => setRounds(r)}
              disabled={isStreaming || readOnly}
              className={`w-[46px] h-[46px] rounded-[10px] text-[15px] font-semibold border-[1.5px] flex justify-center items-center shrink-0 transition-all ${
                rounds === r
                  ? 'bg-gradient-to-br from-[#6C4DFF] to-[#4F7FFF] text-white border-transparent shadow-[0_4px_12px_rgba(108,77,255,0.3)]'
                  : 'bg-white border-border-light text-[#475569] hover:border-[#94A3B8] disabled:opacity-50'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Start Button - 30% */}
      <div className="min-w-0 flex flex-col justify-start">
        <button
          onClick={onStart}
          disabled={isStreaming || readOnly || !topic.trim()}
          className="w-full h-[52px] bg-gradient-to-br from-[#6C4DFF] to-[#4F7FFF] text-white text-[16px] font-bold rounded-xl shadow-[0_4px_16px_rgba(79,127,255,0.25)] flex justify-center items-center gap-2 hover:-translate-y-[1px] transition-transform disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:translate-y-0 mb-2"
        >
          <Play size={18} fill="currentColor" /> {readOnly ? "View Only" : "Start Debate"}
        </button>
        <div className="text-center text-[12px] text-[#94A3B8] font-medium">
          Let the AI agents begin!
        </div>
      </div>

    </div>
  );
};
