import ReactMarkdown from 'react-markdown';
import React from 'react';
import type { DebateMessage as IDebateMessage } from '../types/debate';

interface Props {
  msg: IDebateMessage;
}

export const DebateMessage: React.FC<Props> = ({ msg }) => {
  const isA = msg.speaker === 'Debater A';
  const role = isA ? 'For' : 'Against';

  return (
    <div className="flex gap-4 mb-5">
      <div 
        className={`w-11 h-11 rounded-full flex justify-center items-center text-[17px] font-bold text-white shrink-0 ${
          isA ? 'bg-[#4F7FFF]' : 'bg-[#E11D68]'
        }`}
      >
        {isA ? 'A' : 'B'}
      </div>
      
      <div 
        className={`flex-1 min-w-0 p-4 px-5 rounded-xl border ${
          isA ? 'bg-[#EFF6FF] border-[#DBEAFE]' : 'bg-[#FFF1F3] border-[#FFE4E9]'
        }`}
      >
        <div className="flex justify-between items-center mb-3 flex-wrap gap-2">
          <div className="flex items-center">
            <span className="text-[15px] font-bold text-text-primary">
              {msg.speaker} ({role})
            </span>
            <span 
              className={`text-[12px] font-semibold px-3 py-1 rounded-full ml-3 ${
                isA ? 'bg-[#DBEAFE] text-[#1D4ED8]' : 'bg-[#FFE4E9] text-[#BE123C]'
              }`}
            >
              Round {msg.round}
            </span>
          </div>
          <span className="text-[12px] text-[#94A3B8] font-medium">
            {msg.timestamp}
          </span>
        </div>
        
        <div 
          className="text-[15px] text-[#334155] leading-[1.65] whitespace-pre-wrap break-words"
          dangerouslySetInnerHTML={{ __html: msg.content.replace(/\n/g, '<br/>') }}
        />
      </div>
    </div>
  );
};
