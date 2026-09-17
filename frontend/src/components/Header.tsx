import React from 'react';
import { Sun, Zap } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <div className="flex justify-between items-center mb-8">
      <div>
        <h1 className="text-[38px] font-extrabold text-text-primary tracking-tight leading-tight">
          <span className="bg-gradient-to-r from-[#6C4DFF] to-[#4F7FFF] bg-clip-text text-transparent">AI</span> Debate Agent
        </h1>
        <p className="text-[15px] text-text-secondary mt-1.5">
          Two LLM agents argue. A judge scores. You learn.
        </p>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 bg-[#EDE9FE] text-[#5B21B6] text-[13px] font-semibold px-4 py-2 rounded-full">
          <Zap size={14} fill="currentColor" /> Powered by vLLM
        </div>
        <button className="w-[38px] h-[38px] bg-white border border-border-light rounded-full flex justify-center items-center text-text-secondary hover:text-text-primary transition-colors shadow-sm">
          <Sun size={18} />
        </button>
        <div className="flex items-center gap-2 bg-white border border-border-light rounded-full p-1 pr-4 shadow-sm cursor-pointer hover:bg-gray-50 transition-colors">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#8B5CF6] to-[#6C4DFF] text-white flex justify-center items-center text-[13px] font-bold">
            H
          </div>
          <span className="text-[14px] font-semibold text-text-primary">Het Gandhi</span>
        </div>
      </div>
    </div>
  );
};
