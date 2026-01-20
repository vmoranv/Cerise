// 全局状态管理 - 使用 Zustand

import { create } from 'zustand';
import type { ChatResponse, SessionResponse, AppConfig } from '@/types/api';

// 导出 Emotion 类型
export { Emotion } from '@/types/api';

// 聊天消息类型
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  emotion?: import('@/types/api').Emotion;
  emotion_intensity?: number;
  timestamp: number;
}

// 聊天状态
interface ChatState {
  session: SessionResponse | null;
  messages: Message[];
  currentEmotion: import('@/types/api').Emotion;
  emotionIntensity: number;
  isLoading: boolean;
  error: string | null;

  // Actions
  setSession: (session: SessionResponse | null) => void;
  addMessage: (message: Message) => void;
  setEmotion: (emotion: import('@/types/api').Emotion, intensity: number) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearMessages: () => void;
  updateLastMessage: (content: string) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  session: null,
  messages: [],
  currentEmotion: 'neutral' as import('@/types/api').Emotion,
  emotionIntensity: 0.5,
  isLoading: false,
  error: null,

  setSession: (session) => set({ session }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  setEmotion: (emotion, intensity) =>
    set({
      currentEmotion: emotion,
      emotionIntensity: intensity,
    }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  clearMessages: () => set({ messages: [] }),

  updateLastMessage: (content) =>
    set((state) => {
      const messages = [...state.messages];
      if (messages.length > 0) {
        const lastMessage = messages[messages.length - 1];
        lastMessage.content = content;
      }
      return { messages };
    }),
}));

// 应用配置状态
interface ConfigState {
  config: AppConfig | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  setConfig: (config: AppConfig) => void;
  updateConfig: (updates: Partial<AppConfig>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useConfigStore = create<ConfigState>((set) => ({
  config: null,
  isLoading: false,
  error: null,

  setConfig: (config) => set({ config }),

  updateConfig: (updates) =>
    set((state) => ({
      config: state.config ? { ...state.config, ...updates } : null,
    })),

  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
}));

// UI 状态
interface UIState {
  sidebarOpen: boolean;
  settingsOpen: boolean;
  live2DVisible: boolean;
  voiceInputActive: boolean;

  // Actions
  toggleSidebar: () => void;
  toggleSettings: () => void;
  toggleLive2D: () => void;
  setVoiceInputActive: (active: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  settingsOpen: false,
  live2DVisible: true,
  voiceInputActive: false,

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  toggleSettings: () => set((state) => ({ settingsOpen: !state.settingsOpen })),
  toggleLive2D: () => set((state) => ({ live2DVisible: !state.live2DVisible })),
  setVoiceInputActive: (active) => set({ voiceInputActive: active }),
}));
