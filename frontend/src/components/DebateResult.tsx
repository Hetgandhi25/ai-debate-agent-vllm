import React from 'react';
import { Trophy } from 'lucide-react';
import type { Verdict } from '../types/debate';

interface Props {
  verdict: Verdict | null;
  isComplete: boolean;
}

export const DebateResult: React.FC<Props> = ({ verdict, isComplete }) => {
  return (
    <div className="min-w-0 flex flex-col bg-white border border-border-light rounded-2xl shadow-[0_2px_12px_rgba(0,0,0,0.03)] p-6 min-h-[400px]">
      
      {/* Header */}
      <div className="flex justify-between items-center pb-4 mb-5 border-b border-border-light h-[52px] shrink-0">
        <div className="flex items-center gap-2.5 text-[17px] font-bold text-text-primary">
          <Trophy size={20} className="text-[#D97706]" /> Debate Result
          {isComplete && (
            <span className="bg-[#DCFCE7] text-[#15803D] text-[12px] px-3 py-1 rounded-full ml-2">
              ● Completed
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto pr-1">
        {!verdict ? (
          <div className="text-center text-text-secondary text-[15px] py-16">
            Awaiting the judge's verdict...
          </div>
        ) : (
          <>
            {/* Winner Card */}
            <div className={`rounded-xl p-5 mb-6 flex items-center gap-4 ${
              verdict.winner === 'Debater A' ? 'bg-[#EFF6FF] border border-[#BFDBFE]' :
              verdict.winner === 'Debater B' ? 'bg-[#FFF1F3] border border-[#FECDD3]' :
              'bg-[#F8FAFC] border border-border-light'
            }`}>
              <div className="text-[40px] drop-shadow-[0_4px_10px_rgba(0,0,0,0.08)]">🏆</div>
              <div>
                <div className="text-[12px] font-extrabold uppercase tracking-widest text-[#64748B] mb-1.5">
                  Winner
                </div>
                <div className={`text-[20px] font-extrabold leading-tight mb-1 ${
                  verdict.winner === 'Debater A' ? 'text-[#1D4ED8]' :
                  verdict.winner === 'Debater B' ? 'text-[#BE123C]' :
                  'text-[#475569]'
                }`}>
                  {verdict.winner === 'Tie' ? 'Tie' : `${verdict.winner} (${verdict.winner === 'Debater A' ? 'For' : 'Against'})`}
                </div>
                <div className="text-[13px] text-[#64748B]">
                  {verdict.winner === 'Debater A' ? 'Stronger logical foundation and reasoning' :
                   verdict.winner === 'Debater B' ? 'Stronger arguments and better evidence' :
                   'An equally matched and compelling debate'}
                </div>
              </div>
            </div>

            {/* Score Breakdown */}
            <div className="text-[15px] font-bold text-text-primary mb-4 flex items-center gap-2">
              📊 Score Breakdown
            </div>
            
            <table className="w-full text-[14px] mb-6 border-collapse">
              <thead>
                <tr>
                  <th className="text-left text-[#64748B] font-semibold text-[12px] pb-3 border-b-[1.5px] border-border-light">Criteria</th>
                  <th className="text-center text-[#64748B] font-semibold text-[12px] pb-3 border-b-[1.5px] border-border-light">Debater A</th>
                  <th className="text-center text-[#64748B] font-semibold text-[12px] pb-3 border-b-[1.5px] border-border-light">Debater B</th>
                </tr>
              </thead>
              <tbody>
                {['logic', 'evidence', 'persuasiveness'].map(crit => {
                  const sumScore = (debater: string) => 
                    (verdict.arguments || []).reduce((acc: number, arg: any) => 
                      arg.speaker === debater ? acc + (parseInt(arg[crit]) || 0) : acc, 0
                    );
                  const scoreA = sumScore('Debater A');
                  const scoreB = sumScore('Debater B');
                  return (
                    <tr key={crit}>
                      <td className="text-left py-3 border-b border-[#F1F4FA] text-[#475569] font-medium capitalize">{crit}</td>
                      <td className="text-center py-3 border-b border-[#F1F4FA] text-[#2563EB] font-bold">{scoreA}</td>
                      <td className="text-center py-3 border-b border-[#F1F4FA] text-[#E11D68] font-bold">{scoreB}</td>
                    </tr>
                  );
                })}
                <tr className="bg-[#F8FAFC]">
                  <td className="text-left py-3.5 border-t-2 border-border-light font-extrabold text-[15px]">Total Score</td>
                  <td className="text-center py-3.5 border-t-2 border-border-light text-[#2563EB] font-extrabold text-[15px]">{verdict.totals?.['Debater A'] || 0}</td>
                  <td className="text-center py-3.5 border-t-2 border-border-light text-[#E11D68] font-extrabold text-[15px]">{verdict.totals?.['Debater B'] || 0}</td>
                </tr>
              </tbody>
            </table>

            {/* Judge Summary */}
            <div className="text-[15px] font-bold text-text-primary mb-4 flex items-center gap-2">
              📝 Judge's Summary
            </div>
            <div className="text-[14px] text-[#475569] leading-[1.65] mb-5">
              {verdict.verdict}
            </div>

            <div className="bg-[#F8FAFC] border-l-4 border-[#6C4DFF] rounded-r-lg p-4 px-5 text-[13px] italic text-[#64748B] leading-relaxed">
              "A great debate doesn't just reveal who is right, but what we all can learn."
            </div>
          </>
        )}
      </div>
    </div>
  );
};
