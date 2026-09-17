export interface DebateMessage {
  round: number;
  speaker: string;
  position: string;
  content: string;
  timestamp: string;
}

export interface Verdict {
  winner: string;
  totals: Record<string, number>;
  verdict: string;
  arguments: any[];
}

export interface Session {
  topic: string;
  rounds: number;
  timestamp: string;
  transcript: DebateMessage[];
  verdict: Verdict | null;
}
