// API 服务层 - 对接后端 Core API 和 TTS Server

import axios, { type AxiosInstance } from 'axios';
import type {
  ChatRequest,
  ChatResponse,
  SessionCreate,
  SessionResponse,
  EmotionUpdate,
  Live2DParametersUpdate,
  Live2DEmotionUpdate,
  ProviderConfig,
  ProviderTestResponse,
  CharacterConfig,
  InstalledPlugin,
  AppConfig,
  TTSRequest,
  ASRRequest,
  ASRResponse,
} from '@/types/api';

// API 基础URL配置
const CORE_API_URL = process.env.NEXT_PUBLIC_CORE_API_URL || 'http://localhost:8000';
const TTS_API_URL = process.env.NEXT_PUBLIC_TTS_API_URL || 'http://localhost:8001';

// 创建 axios 实例
const coreApi: AxiosInstance = axios.create({
  baseURL: CORE_API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

const ttsApi: AxiosInstance = axios.create({
  baseURL: TTS_API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 可以在这里添加认证token等
coreApi.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证逻辑
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器
coreApi.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// ============ Core API 服务 ============

export const chatApi = {
  // 健康检查
  async health(): Promise<{ status: string }> {
    const { data } = await coreApi.get('/health');
    return data;
  },

  // 创建会话
  async createSession(request: SessionCreate): Promise<SessionResponse> {
    const { data } = await coreApi.post('/sessions', request);
    return data;
  },

  // 获取会话信息
  async getSession(sessionId: string): Promise<SessionResponse> {
    const { data } = await coreApi.get(`/sessions/${sessionId}`);
    return data;
  },

  // 删除会话
  async deleteSession(sessionId: string): Promise<void> {
    await coreApi.delete(`/sessions/${sessionId}`);
  },

  // 发送聊天消息（非流式）
  async chat(request: ChatRequest): Promise<ChatResponse> {
    const { data } = await coreApi.post('/chat', request);
    return data;
  },

  // 获取当前情感
  async getEmotion(): Promise<EmotionUpdate> {
    const { data } = await coreApi.get('/emotion');
    return data;
  },

  // 手动设置情感
  async setEmotion(emotion: EmotionUpdate): Promise<void> {
    await coreApi.post('/emotion', emotion);
  },

  // 设置 Live2D 情感参数
  async setLive2DEmotion(update: Live2DEmotionUpdate): Promise<void> {
    await coreApi.post('/l2d/emotion', update);
  },

  // 设置 Live2D 参数
  async setLive2DParams(update: Live2DParametersUpdate): Promise<void> {
    await coreApi.post('/l2d/params', update);
  },
};

// Admin API 服务
export const adminApi = {
  // 获取应用配置
  async getConfig(): Promise<AppConfig> {
    const { data } = await coreApi.get('/admin/config');
    return data;
  },

  // 更新应用配置
  async updateConfig(config: Partial<AppConfig>): Promise<void> {
    await coreApi.put('/admin/config', config);
  },

  // Provider 管理
  async listProviders(): Promise<ProviderConfig[]> {
    const { data } = await coreApi.get('/admin/providers');
    return data;
  },

  async getProviderModels(providerId: string): Promise<string[]> {
    const { data } = await coreApi.get(`/admin/providers/${providerId}/models`);
    return data;
  },

  async addProvider(provider: ProviderConfig): Promise<void> {
    await coreApi.post('/admin/providers', provider);
  },

  async updateProvider(providerId: string, provider: Partial<ProviderConfig>): Promise<void> {
    await coreApi.put(`/admin/providers/${providerId}`, provider);
  },

  async deleteProvider(providerId: string): Promise<void> {
    await coreApi.delete(`/admin/providers/${providerId}`);
  },

  async testProvider(providerId: string): Promise<ProviderTestResponse> {
    const { data } = await coreApi.post(`/admin/providers/${providerId}/test`);
    return data;
  },

  async setDefaultProvider(providerId: string): Promise<void> {
    await coreApi.post(`/admin/providers/${providerId}/set-default`);
  },

  // 角色管理
  async listCharacters(): Promise<string[]> {
    const { data } = await coreApi.get('/admin/characters');
    return data;
  },

  async getCharacter(name: string): Promise<CharacterConfig> {
    const { data } = await coreApi.get(`/admin/characters/${name}`);
    return data;
  },

  async updateCharacter(name: string, character: Partial<CharacterConfig>): Promise<void> {
    await coreApi.put(`/admin/characters/${name}`, character);
  },

  // 插件管理
  async listPlugins(): Promise<InstalledPlugin[]> {
    const { data } = await coreApi.get('/admin/plugins');
    return data;
  },

  async installPluginFromGithub(url: string): Promise<void> {
    await coreApi.post('/admin/plugins/install/github', { url });
  },

  async installPluginFromFile(file: FormData): Promise<void> {
    await coreApi.post('/admin/plugins/install/upload', file, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  async uninstallPlugin(name: string): Promise<void> {
    await coreApi.delete(`/admin/plugins/${name}`);
  },

  async getPlugin(name: string): Promise<InstalledPlugin> {
    const { data } = await coreApi.get(`/admin/plugins/${name}`);
    return data;
  },

  async updatePlugin(name: string, config: Record<string, unknown>): Promise<void> {
    await coreApi.put(`/admin/plugins/${name}`, { config });
  },

  async enablePlugin(name: string): Promise<void> {
    await coreApi.post(`/admin/plugins/${name}/enable`);
  },

  async disablePlugin(name: string): Promise<void> {
    await coreApi.post(`/admin/plugins/${name}/disable`);
  },
};

// ============ TTS API 服务 ============

export const ttsApi_ = {
  // 健康检查
  async health(): Promise<{ status: string }> {
    const { data } = await ttsApi.get('/health');
    return data;
  },

  // 获取配置
  async getConfig(): Promise<unknown> {
    const { data } = await ttsApi.get('/config');
    return data;
  },

  // TTS 合成
  async synthesize(request: TTSRequest): Promise<Blob> {
    const { data } = await ttsApi.post('/api/v1/tts/synthesize/audio', request, {
      responseType: 'blob',
    });
    return data;
  },

  // 获取可用角色
  async getCharacters(): Promise<string[]> {
    const { data } = await ttsApi.get('/api/v1/tts/characters');
    return data;
  },

  // ASR 转录
  async transcribe(request: ASRRequest): Promise<ASRResponse> {
    const { data } = await ttsApi.post('/api/v1/asr/transcribe', request);
    return data;
  },
};

// WebSocket 连接辅助函数
export const createChatWebSocket = (sessionId?: string): WebSocket => {
  const wsUrl = CORE_API_URL.replace('http', 'ws');
  const url = sessionId ? `${wsUrl}/ws/chat?session_id=${sessionId}` : `${wsUrl}/ws/chat`;
  return new WebSocket(url);
};

export const createTTSWebSocket = (): WebSocket => {
  const wsUrl = TTS_API_URL.replace('http', 'ws');
  return new WebSocket(`${wsUrl}/ws/tts`);
};

export const createASRWebSocket = (): WebSocket => {
  const wsUrl = TTS_API_URL.replace('http', 'ws');
  return new WebSocket(`${wsUrl}/ws/asr`);
};

// 导出 API URLs
export { CORE_API_URL, TTS_API_URL };
