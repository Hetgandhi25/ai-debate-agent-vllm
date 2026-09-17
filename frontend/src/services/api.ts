import axios from 'axios';
import type { Session } from '../types/debate';

const API_BASE = 'http://localhost:8000/api';

export const getHistory = async (): Promise<Session[]> => {
  const res = await axios.get(`${API_BASE}/history`);
  return res.data.sessions;
};

export const getHistoryItem = async (idx: number): Promise<Session> => {
  const res = await axios.get(`${API_BASE}/history/${idx}`);
  return res.data.session;
};

export const clearHistory = async (): Promise<void> => {
  await axios.delete(`${API_BASE}/history`);
};

export const deleteHistoryItem = async (idx: number): Promise<void> => {
  await axios.delete(`${API_BASE}/history/${idx}`);
};
